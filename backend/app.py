"""
AgroChat Backend API
Integrates CNN (disease detection) + RAG (knowledge retrieval) + LLM (advice) + Weather API
"""

# =========================
# ENV & BASIC IMPORTS
# =========================
from dotenv import load_dotenv
import os
import io
import json
import subprocess
import traceback
from pathlib import Path
import time
import httpx
import chromadb
from chromadb.utils import embedding_functions
import torchvision.models as tv_models

# Load .env file from backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)
print(f"Loading .env from: {env_path}")

# =========================
# SERVER CONFIG (SINGLE SOURCE OF TRUTH)
# =========================
HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"

# =========================
# ML / IMAGE IMPORTS
# =========================
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from efficientnet_pytorch import EfficientNet
import numpy as np

# =========================
# FASTAPI IMPORTS
# =========================
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# =========================
# DEVICE
# =========================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", DEVICE)

# =========================
# CHECKPOINT
# =========================
CHECKPOINT_LOCATIONS = [
    "models/efficientnet_b0_best.pth",
    "../models/efficientnet_b0_best.pth",
]

CHECKPOINT_PATH = None
for p in CHECKPOINT_LOCATIONS:
    if os.path.exists(p):
        CHECKPOINT_PATH = p
        break

if not CHECKPOINT_PATH:
    raise FileNotFoundError("efficientnet_b0_best.pth not found")

# Insect checkpoint
INSECT_CHECKPOINT_LOCATIONS = [
    "models/efficientnet_insects.pth",
    "models/efficienntnet_insects.pth",  # common typo
    "../models/efficientnet_insects.pth",
    "../models/efficienntnet_insects.pth",
    str(Path.home() / "Downloads" / "efficientnet_insects.pth"),
    str(Path.home() / "Downloads" / "efficienntnet_insects.pth"),
]

INSECT_CHECKPOINT_PATH = None
for p in INSECT_CHECKPOINT_LOCATIONS:
    if os.path.exists(p):
        INSECT_CHECKPOINT_PATH = p
        break

if not INSECT_CHECKPOINT_PATH:
    print("⚠️ Insect checkpoint not found. Insect CNN will be disabled.")

# =========================
# DISEASE KNOWLEDGE
# =========================
DISEASE_KNOWLEDGE = """(UNCHANGED – same as your file)"""
# ⬆️ keep your full disease text here (unchanged)

CLASS_TO_TITLE = {
    "Pepper__bell___Bacterial_spot": "Pepper Bell Bacterial Spot",
    "Pepper__bell___healthy": "Pepper Bell Healthy",
    "Potato___Early_blight": "Potato Early Blight",
    "Potato___Late_blight": "Potato Late Blight",
    "Potato___healthy": "Potato Healthy",
    "Tomato_Bacterial_spot": "Tomato Bacterial Spot",
    "Tomato_Early_blight": "Tomato Early Blight",
    "Tomato_Late_blight": "Tomato Late Blight",
    "Tomato_Leaf_Mold": "Tomato Leaf Mold",
    "Tomato_Septoria_leaf_spot": "Tomato Septoria Leaf Spot",
    "Tomato_Spider_mites_Two_spotted_spider_mite": "Tomato Spider Mites",
    "Tomato__Target_Spot": "Tomato Target Spot",
    "Tomato__Tomato_mosaic_virus": "Tomato Mosaic Virus",
    "Tomato__Tomato_YellowLeaf__Curl_Virus": "Tomato Yellow Leaf Curl Virus",
    "Tomato_healthy": "Tomato Healthy",
}

# =========================
# LLM DETECTION
# =========================
def detect_llm():
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, timeout=2)
        return "ollama"
    except:
        return "stub"

LLM_TYPE = detect_llm()
print("LLM Mode:", LLM_TYPE)

def ask_llm(prompt: str) -> str:
    if LLM_TYPE == "ollama":
        try:
            p = subprocess.Popen(
                ["ollama", "run", "llama3.2:1b"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            out, _ = p.communicate(prompt, timeout=60)
            return out.strip() if out else "No response"
        except:
            return "LLM error"
    return "[STUB LLM] " + prompt[:120]

from services.rag import RAGService

# =========================
# RAG with ChromaDB
# =========================
# Basic plant + insect knowledge for retrieval
KNOWLEDGE_DOCS = [
    # Plant diseases (condensed)
    {
        "id": "tomato_early_blight",
        "category": "plant",
        "title": "Tomato Early Blight",
        "text": "Tomato Early Blight: Dark brown concentric leaf spots, yellowing lower leaves. Cause: Alternaria solani. Control: Remove infected leaves, copper/chlorothalonil/mancozeb sprays 7-10 days. Prevention: crop rotation, avoid overhead water, resistant varieties."
    },
    {
        "id": "tomato_late_blight",
        "category": "plant",
        "title": "Tomato Late Blight",
        "text": "Tomato Late Blight: Water-soaked lesions, white mold underside, rapid die-off. Cause: Phytophthora infestans. Control: mancozeb/chlorothalonil preventively weekly. Prevention: resistant varieties, good drainage, avoid overhead irrigation."
    },
    {
        "id": "tomato_bacterial_spot",
        "category": "plant",
        "title": "Tomato Bacterial Spot",
        "text": "Tomato Bacterial Spot: Small dark spots on leaves/fruit, yellowing, drop. Cause: Xanthomonas. Control: copper bactericides early. Prevention: clean seed, avoid working wet plants, rotate."
    },
    {
        "id": "potato_late_blight",
        "category": "plant",
        "title": "Potato Late Blight",
        "text": "Potato Late Blight: Water-soaked lesions, white mold, rapid collapse. Cause: Phytophthora infestans. Control: remove infected plants, copper/mancozeb preventively. Prevention: certified seed, drainage, spacing."
    },
    {
        "id": "pepper_bacterial_spot",
        "category": "plant",
        "title": "Pepper Bacterial Spot",
        "text": "Pepper Bacterial Spot: Water-soaked spots turning brown, defoliation. Cause: Xanthomonas. Control: copper sprays. Prevention: disease-free seed, avoid overhead irrigation, rotate."
    },
    # Insects
    {
        "id": "insect_aphids",
        "category": "insect",
        "title": "Aphids",
        "text": "Aphids: Small soft-bodied clusters on shoots/leaves, sticky honeydew, curled leaves. Control: water spray, neem/insecticidal soap, introduce ladybugs. Monitor under leaves; avoid excess nitrogen."
    },
    {
        "id": "insect_armyworms",
        "category": "insect",
        "title": "Armyworms",
        "text": "Armyworms/Fall Armyworms: Caterpillars skeletonize leaves, windowpaning, frass. Control: hand-pick early, Bt sprays, spinosad; monitor egg masses; use pheromone traps; maintain field sanitation."
    },
    {
        "id": "insect_corn_borers",
        "category": "insect",
        "title": "Corn Borers",
        "text": "Corn Borers: Larvae tunnel stalks/ears causing broken stalks, frass at entry holes. Control: Bt varieties, timely harvest, destroy residues, Bt or spinosad at tasseling, pheromone traps for timing."
    },
    {
        "id": "insect_tomato_hornworms",
        "category": "insect",
        "title": "Tomato Hornworms",
        "text": "Tomato Hornworms: Large green caterpillars, heavy defoliation, green droppings. Control: hand-pick, encourage parasitic wasps (white cocoons), use Bt/spinosad if severe; rotate and weed control."
    },
    {
        "id": "insect_spider_mites",
        "category": "insect",
        "title": "Spider Mites",
        "text": "Spider Mites: Yellow stippling, fine webbing under leaves, thrive hot/dry. Control: increase humidity, water spray, neem/miticides, remove heavily infested leaves; avoid drought stress."
    },
    {
        "id": "insect_thrips",
        "category": "insect",
        "title": "Thrips",
        "text": "Thrips: Silvery streaks, distorted buds, possible virus vectors. Control: blue/yellow sticky traps, spinosad/azadirachtin, remove weeds, reflective mulches, rotate insecticides."
    },
    {
        "id": "insect_fruit_flies",
        "category": "insect",
        "title": "Fruit Flies",
        "text": "Fruit Flies: Oviposition scars on fruit, maggots inside. Control: bait traps, sanitation (remove fallen fruit), bagging fruit, protein baits, timely harvest."
    },
    {
        "id": "insect_colorado_potato_beetle",
        "category": "insect",
        "title": "Colorado Potato Beetle",
        "text": "Colorado Potato Beetle: Yellow-black striped beetles, orange larvae defoliate potatoes. Control: hand-pick eggs/larvae, rotate crops, mulch, spinosad/pyrethroids with rotation to avoid resistance."
    },
    {
        "id": "insect_bmsb",
        "category": "insect",
        "title": "Brown Marmorated Stink Bug",
        "text": "Brown Marmorated Stink Bug: Shield-shaped, causes fruit catfacing and feeding spots. Control: perimeter monitoring, remove weeds, trap crops, use netting; targeted pyrethroids if severe."
    },
]

# Initialize ChromaDB client and collection
CHROMA_PATH = Path(__file__).parent / "data" / "chroma"
CHROMA_PATH.mkdir(parents=True, exist_ok=True)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
chroma_collection = chroma_client.get_or_create_collection(
    name="agrochat_knowledge",
    embedding_function=embedding_fn,
)

# Upsert knowledge docs (idempotent)
try:
    chroma_collection.upsert(
        ids=[doc["id"] for doc in KNOWLEDGE_DOCS],
        documents=[doc["text"] for doc in KNOWLEDGE_DOCS],
        metadatas=[{"title": doc["title"], "category": doc["category"]} for doc in KNOWLEDGE_DOCS],
    )
    print(f"ChromaDB loaded docs: {len(KNOWLEDGE_DOCS)}")
except Exception as e:
    print(f"⚠️ Failed to load ChromaDB docs: {e}")

# Helper for RAG retrieval
def query_knowledge(query: str, category: str | None = None, top_k: int = 3) -> str:
    where = {"category": category} if category else None
    try:
        res = chroma_collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        out_lines = []
        for doc, meta in zip(docs, metas):
            title = meta.get("title", "Knowledge")
            out_lines.append(f"{title}: {doc}")
        return "\n\n".join(out_lines) if out_lines else "No specific knowledge found."
    except Exception as e:
        return f"Knowledge lookup unavailable: {e}"

# =========================
# CNN LOAD
# =========================
checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
CLASS_NAMES = checkpoint["classes"]

MODEL = EfficientNet.from_pretrained(
    "efficientnet-b0",
    num_classes=len(CLASS_NAMES)
)
MODEL.load_state_dict(checkpoint["model"])
MODEL.to(DEVICE)
MODEL.eval()

# Insect model (optional)
INSECT_CLASSES = [
    'Africanized Honey Bees (Killer Bees)', 'Aphids', 'Armyworms', 'Brown Marmorated Stink Bugs',
    'Cabbage Loopers', 'Citrus Canker', 'Colorado Potato Beetles', 'Corn Borers', 'Corn Earworms',
    'Fall Armyworms', 'Fruit Flies', 'Spider Mites', 'Thrips', 'Tomato Hornworms', 'Western Corn Rootworms'
]

if INSECT_CHECKPOINT_PATH:
    try:
        insect_checkpoint = torch.load(INSECT_CHECKPOINT_PATH, map_location=DEVICE)

        # Handle different checkpoint formats
        state_dict = None
        if isinstance(insect_checkpoint, dict):
            if "model" in insect_checkpoint:
                state_dict = insect_checkpoint["model"]
            elif "state_dict" in insect_checkpoint:
                state_dict = insect_checkpoint["state_dict"]
            else:
                # If it looks like a pure state dict, try using it directly
                state_dict = {k: v for k, v in insect_checkpoint.items()} if insect_checkpoint else insect_checkpoint

            cls = insect_checkpoint.get("classes", INSECT_CLASSES)
            if isinstance(cls, list) and len(cls) == len(INSECT_CLASSES):
                INSECT_CLASSES = cls
        else:
            state_dict = insect_checkpoint

        # Use torchvision EfficientNet-B0 to match the checkpoint key format (features.*)
        INSECT_MODEL = tv_models.efficientnet_b0(weights=None)
        # Replace classifier for our number of insect classes
        INSECT_MODEL.classifier[1] = torch.nn.Linear(INSECT_MODEL.classifier[1].in_features, len(INSECT_CLASSES))
        missing, unexpected = INSECT_MODEL.load_state_dict(state_dict, strict=False)
        if missing or unexpected:
            print(f"⚠️ Insect model loaded with missing keys: {len(missing)}, unexpected keys: {len(unexpected)}")
        INSECT_MODEL.to(DEVICE)
        INSECT_MODEL.eval()
        print(f"Insect model loaded from: {INSECT_CHECKPOINT_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to load insect model from {INSECT_CHECKPOINT_PATH}: {e}")
        INSECT_MODEL = None
else:
    INSECT_MODEL = None

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="AgroChat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DB
# =========================
import db as persistence
persistence.init_db()

# =========================
# HEALTH
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# WEATHER
# =========================
OPENWEATHER_KEY = os.getenv("WEATHER_KEY")
if OPENWEATHER_KEY:
    print(f"✅ WEATHER_KEY found (OpenWeather), but using Open-Meteo (no key needed).")
else:
    print("ℹ️ No WEATHER_KEY set. Using Open-Meteo (no API key required).")

OPENMETEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Simple weather-code descriptions for Open-Meteo
WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@app.get("/weather")
async def weather(query: str):
    """Get current weather for a city using Open-Meteo (no API key)."""
    async def _fetch(lat: float, lon: float, label: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                OPENMETEO_WEATHER_URL,
                params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            cw = data.get("current_weather")
            if not cw:
                raise RuntimeError("No current_weather in response")
            code = cw.get("weathercode")
            desc = WEATHER_CODE_DESCRIPTIONS.get(code, "Current conditions")
            return {
                "success": True,
                "name": label,
                "main": {
                    "temp": cw.get("temperature"),
                    "feels_like": cw.get("temperature"),
                    "humidity": None,
                },
                "weather": [{"description": desc}],
                "wind": {"speed": cw.get("windspeed")},
            }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            geo = await client.get(
                OPENMETEO_GEOCODE_URL,
                params={"name": query, "count": 1, "language": "en", "format": "json"},
            )
            geo.raise_for_status()
            gdata = geo.json()
            if not gdata.get("results"):
                return {"success": False, "message": f"No location found for '{query}'"}
            loc = gdata["results"][0]
            lat = float(loc["latitude"])
            lon = float(loc["longitude"])
            label_parts = [loc.get("name")]
            if loc.get("country"):
                label_parts.append(loc["country"])
            label = ", ".join([p for p in label_parts if p])
            return await _fetch(lat, lon, label)
    except httpx.HTTPError as e:
        return {"success": False, "message": f"Weather API HTTP error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Weather lookup failed: {str(e)}"}


@app.get("/weather_coords")
async def weather_coords(lat: float = Query(...), lon: float = Query(...)):
    """Get current weather by coordinates using Open-Meteo."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                OPENMETEO_WEATHER_URL,
                params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            cw = data.get("current_weather")
            if not cw:
                return {
                    "success": False,
                    "message": "No current weather data available",
                    "temp": None,
                    "description": "Weather data unavailable",
                }
            code = cw.get("weathercode")
            desc = WEATHER_CODE_DESCRIPTIONS.get(code, "Current conditions")
            return {
                "success": True,
                "temp": cw.get("temperature"),
                "feels_like": cw.get("temperature"),
                "humidity": None,
                "description": desc,
                "wind_speed": cw.get("windspeed"),
                "location": f"{lat:.3f}, {lon:.3f}",
            }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "message": f"Weather API HTTP error: {str(e)}",
            "temp": None,
            "description": "Weather data unavailable",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error fetching weather: {str(e)}",
            "temp": None,
            "description": "Weather data unavailable",
        }

# =========================
# IMAGE ANALYSIS
# =========================
@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    question: str = Query("What treatment do you recommend?")
):
    img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)

    question_lower = question.lower()
    is_insect_query = '[insect]' in question_lower or 'insect' in question_lower

    # Insect branch
    if is_insect_query and INSECT_MODEL:
        with torch.no_grad():
            probs = F.softmax(INSECT_MODEL(tensor), dim=1)[0]
        conf, idx = torch.max(probs, 0)
        insect_class = INSECT_CLASSES[idx.item()]
        confidence_score = round(conf.item() * 100, 2)

        # RAG for insect knowledge
        knowledge = query_knowledge(f"{insect_class}. {question}", category="insect")
        advice = f"Detected insect: {insect_class}\nConfidence: {confidence_score}%\n\nRecommended actions:\n{knowledge}"

        return {
            "disease": insect_class,
            "disease_title": insect_class,
            "confidence": confidence_score,
            "advice": advice,
            "llm_mode": LLM_TYPE,
            "is_insect": True
        }
    elif is_insect_query and not INSECT_MODEL:
        return {
            "disease": "Insect Identification",
            "disease_title": "Insect Identification",
            "confidence": 0,
            "advice": "⚠️ Insect CNN model not available. Please place efficientnet_insects.pth in backend/models.",
            "llm_mode": LLM_TYPE,
            "is_insect": True
        }

    # Plant branch
    with torch.no_grad():
        probs = F.softmax(MODEL(tensor), dim=1)[0]

    conf, idx = torch.max(probs, 0)
    disease = CLASS_NAMES[idx.item()]
    confidence_score = round(conf.item() * 100, 2)
    
    # Get detailed advice from Chroma RAG
    knowledge = query_knowledge(f"{disease}. {question}", category="plant")
    advice = f"{knowledge}"

    disease_title = CLASS_TO_TITLE.get(disease, disease)
    
    return {
        "disease": disease,
        "disease_title": disease_title,
        "confidence": confidence_score,
        "advice": advice,
        "llm_mode": LLM_TYPE,
        "is_insect": False
    }

# =========================
# CHAT
# =========================
class ChatRequest(BaseModel):
    question: str
    context: list | None = None

@app.post("/chat")
async def chat(req: ChatRequest):
    question_original = req.question
    question = question_original.lower().strip()
    
    # Detect weather-related questions (more comprehensive)
    weather_keywords = ['weather', 'temperature', 'temp', 'rain', 'sunny', 'cloudy', 'forecast', 'humidity', 'wind', 'climate', 'meteorological']
    is_weather_query = any(keyword in question for keyword in weather_keywords)
    
    # Debug logging
    print(f"\n=== CHAT REQUEST ===")
    print(f"Original question: {question_original}")
    print(f"Lowercase question: {question}")
    print(f"Is weather query: {is_weather_query}")
    print(f"Has API key: {bool(OPENWEATHER_KEY)}")
    print(f"API key value: {OPENWEATHER_KEY[:8] if OPENWEATHER_KEY else 'None'}...")
    
    # ALWAYS check weather first if it's a weather query
    if is_weather_query:
        if not OPENWEATHER_KEY:
            return {"answer": "⚠️ Weather API is not configured. Please set WEATHER_KEY in backend/.env file."}
        
        print("Processing weather query...")
        # Try to extract location from question
        # Common city names or "my location" / "here"
        location = None
        
        # Check for common Indian cities
        cities = {
            'chennai': 'Chennai,IN',
            'mumbai': 'Mumbai,IN',
            'delhi': 'Delhi,IN',
            'bangalore': 'Bangalore,IN',
            'kolkata': 'Kolkata,IN',
            'hyderabad': 'Hyderabad,IN',
            'pune': 'Pune,IN',
            'ahmedabad': 'Ahmedabad,IN'
        }
        
        for city_key, city_query in cities.items():
            if city_key in question:
                location = city_query
                break
        
        # If no predefined city found, try to extract city name from question
        if not location:
            # Look for patterns like "in Chennai", "at Mumbai", "for Delhi"
            import re
            patterns = [
                r'(?:in|at|for)\s+(\w+)',
                r'(\w+)\s+(?:weather|temperature|temp)',
            ]
            for pattern in patterns:
                match = re.search(pattern, question, re.IGNORECASE)
                if match:
                    potential_city = match.group(1).lower()
                    # Try it as a city name
                    if len(potential_city) > 2:  # Avoid short words
                        location = f"{potential_city.capitalize()},IN"
                        print(f"Extracted city: {location}")
                        break
        
        if location:
            try:
                # Re-use internal /weather handler for robustness
                # Strip country code if present for nicer display
                city_query = location.split(",")[0]
                weather_raw = await weather(city_query)

                if not weather_raw.get("success"):
                    msg = weather_raw.get("message") or "Unknown weather service error."
                    return {"answer": f"⚠️ Weather service error: {msg}"}

                temp = weather_raw.get("main", {}).get("temp")
                feels_like = weather_raw.get("main", {}).get("feels_like")
                humidity = weather_raw.get("main", {}).get("humidity")
                description = weather_raw.get("weather", [{}])[0].get("description", "")
                wind_speed = weather_raw.get("wind", {}).get("speed")
                city_name = weather_raw.get("name", city_query)

                response = f"🌤️ Weather in {city_name}:\n\n"
                if temp is not None and feels_like is not None:
                    response += f"🌡️ Temperature: {temp:.1f}°C (feels like {feels_like:.1f}°C)\n"
                if description:
                    response += f"☁️ Conditions: {description.title()}\n"
                if humidity is not None:
                    response += f"💧 Humidity: {humidity}%\n"
                if wind_speed:
                    response += f"💨 Wind Speed: {wind_speed} m/s\n"

                return {"answer": response}
            except HTTPException as e:
                # Bubble up clear API error from /weather
                return {"answer": f"⚠️ Weather API error: {e.detail}"}
            except Exception as e:
                # Include the actual error so user can see what's wrong
                return {"answer": f"⚠️ Could not fetch weather data. Details: {str(e)}"}
        
        # If no location found, provide helpful message
        return {"answer": "🌤️ To get weather information, please mention your city name in your question.\n\nExamples:\n• 'What's the weather in Chennai?'\n• 'Weather in Mumbai'\n• 'Temperature in Delhi'\n\nOr click the weather button and allow location access."}
    
    # For non-weather questions, use LLM
    return {"answer": ask_llm(req.question)}

# =========================
# CONVERSATIONS
# =========================
@app.get("/conversations")
def list_convs():
    return {"conversations": persistence.get_all_conversations()}

@app.post("/conversations")
def save_conv(conv: dict = Body(...)):
    # Only save conversations that have at least one message
    messages = conv.get('messages', [])
    if not messages or len(messages) == 0:
        return {"success": False, "error": "Cannot save empty conversation"}
    persistence.upsert_conversation(conv)
    return {"success": True}

@app.delete("/conversations/{conv_id}")
def delete_conv(conv_id: str):
    deleted = persistence.delete_conversation(conv_id)
    if deleted:
        return {"success": True}
    raise HTTPException(404, "Conversation not found")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("=" * 60)
    print("AgroChat Backend Running")
    print(f"API  : {BASE_URL}")
    print(f"Docs : {BASE_URL}/docs")
    print("=" * 60)

    uvicorn.run(app, host=HOST, port=PORT)
