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

# =========================
# RAG
# =========================
from services.rag import RAGService

# Create comprehensive disease knowledge base
DISEASE_KNOWLEDGE_FULL = """
Tomato Early Blight:
- Symptoms: Dark brown spots with concentric rings on lower leaves, yellowing leaves, defoliation
- Cause: Fungus Alternaria solani, spreads in warm humid conditions
- Organic Control: Remove infected leaves, use copper-based fungicides, improve air circulation
- Chemical Control: Apply chlorothalonil or mancozeb fungicides every 7-10 days
- Prevention: Rotate crops, avoid overhead watering, use resistant varieties, space plants properly

Tomato Late Blight:
- Symptoms: Water-soaked lesions on leaves, white mold on undersides, rapid plant death
- Cause: Phytophthora infestans, thrives in cool wet weather
- Organic Control: Remove and destroy infected plants, use copper fungicides preventively
- Chemical Control: Apply mancozeb or chlorothalonil before infection, repeat weekly
- Prevention: Plant resistant varieties, avoid overhead irrigation, ensure good drainage

Tomato Bacterial Spot:
- Symptoms: Small dark spots on leaves and fruits, leaf yellowing and drop
- Cause: Xanthomonas bacteria, spreads through water and tools
- Organic Control: Remove infected plants, use copper-based sprays, sanitize tools
- Chemical Control: Apply copper-based bactericides early in season
- Prevention: Use disease-free seeds, avoid working when plants are wet, rotate crops

Tomato Leaf Mold:
- Symptoms: Yellow patches on upper leaf surface, gray mold on lower surface
- Cause: Passalora fulva fungus, common in greenhouse conditions
- Organic Control: Improve ventilation, remove infected leaves, use sulfur sprays
- Chemical Control: Apply chlorothalonil or mancozeb fungicides
- Prevention: Reduce humidity, increase air circulation, space plants adequately

Tomato Septoria Leaf Spot:
- Symptoms: Small circular spots with dark borders and light centers on leaves
- Cause: Septoria lycopersici fungus, spreads via water splash
- Organic Control: Remove lower infected leaves, use copper fungicides
- Chemical Control: Apply mancozeb or chlorothalonil every 7-10 days
- Prevention: Avoid overhead watering, mulch around plants, rotate crops

Tomato Spider Mites:
- Symptoms: Yellow stippling on leaves, fine webbing, leaf drop
- Cause: Two-spotted spider mites, thrive in hot dry conditions
- Organic Control: Spray with water to increase humidity, use neem oil or insecticidal soap
- Chemical Control: Apply miticides like abamectin or spiromesifen
- Prevention: Maintain adequate moisture, introduce beneficial insects, avoid over-fertilizing

Tomato Target Spot:
- Symptoms: Brown spots with target-like rings, leaf yellowing
- Cause: Corynespora cassiicola fungus
- Organic Control: Remove infected leaves, improve air circulation
- Chemical Control: Apply chlorothalonil or azoxystrobin fungicides
- Prevention: Use resistant varieties, avoid overhead watering, space plants properly

Tomato Mosaic Virus:
- Symptoms: Mottled yellow and green leaves, stunted growth, distorted fruits
- Cause: Tobacco mosaic virus, spreads through contact and tools
- Organic Control: Remove and destroy infected plants, sanitize tools
- Chemical Control: No effective chemical treatment available
- Prevention: Use virus-free seeds, avoid tobacco use near plants, sanitize tools regularly

Tomato Yellow Leaf Curl Virus:
- Symptoms: Yellowing and curling of leaves, stunted growth, reduced fruit
- Cause: Begomovirus transmitted by whiteflies
- Organic Control: Remove infected plants, control whiteflies with neem oil
- Chemical Control: Apply systemic insecticides for whitefly control
- Prevention: Use resistant varieties, control whiteflies early, use row covers

Potato Early Blight:
- Symptoms: Dark brown spots with concentric rings, yellowing lower leaves
- Cause: Alternaria solani fungus
- Organic Control: Remove infected leaves, use copper fungicides
- Chemical Control: Apply chlorothalonil or mancozeb every 7-10 days
- Prevention: Rotate crops, avoid overhead watering, use certified seed potatoes

Potato Late Blight:
- Symptoms: Water-soaked lesions, white mold, rapid plant collapse
- Cause: Phytophthora infestans
- Organic Control: Remove infected plants immediately, use copper fungicides
- Chemical Control: Apply mancozeb preventively, repeat weekly in wet conditions
- Prevention: Plant certified disease-free seed, ensure good drainage, space plants

Pepper Bell Bacterial Spot:
- Symptoms: Small water-soaked spots that turn brown, leaf drop
- Cause: Xanthomonas bacteria
- Organic Control: Remove infected plants, use copper-based sprays
- Chemical Control: Apply copper bactericides early in season
- Prevention: Use disease-free seeds, avoid overhead irrigation, rotate crops
"""

RAG = RAGService(DISEASE_KNOWLEDGE_FULL, CLASS_TO_TITLE)

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
    print(f"✅ Weather API key loaded: {OPENWEATHER_KEY[:8]}...")
else:
    print("⚠️ Weather API key not found in environment")

@app.get("/weather")
async def weather(query: str):
    if not OPENWEATHER_KEY:
        raise HTTPException(500, "WEATHER_KEY missing")

    async with httpx.AsyncClient() as client:
        geo = await client.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": query, "limit": 1, "appid": OPENWEATHER_KEY}
        )
        loc = geo.json()[0]
        w = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": loc["lat"],
                "lon": loc["lon"],
                "appid": OPENWEATHER_KEY,
                "units": "metric"
            }
        )
        return {"success": True, **w.json()}

@app.get("/weather_coords")
async def weather_coords(lat: float = Query(...), lon: float = Query(...)):
    if not OPENWEATHER_KEY:
        # Return a helpful message instead of error
        return {
            "success": False,
            "message": "Weather API key not configured. Please set WEATHER_KEY in .env file.",
            "temp": None,
            "description": "Weather data unavailable"
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            w = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": OPENWEATHER_KEY,
                    "units": "metric"
                }
            )
            w.raise_for_status()
            data = w.json()
            return {
                "success": True,
                "temp": data.get("main", {}).get("temp"),
                "feels_like": data.get("main", {}).get("feels_like"),
                "humidity": data.get("main", {}).get("humidity"),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "wind_speed": data.get("wind", {}).get("speed"),
                "location": data.get("name", "Unknown")
            }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "message": f"Weather API error: {str(e)}",
            "temp": None,
            "description": "Weather data unavailable"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error fetching weather: {str(e)}",
            "temp": None,
            "description": "Weather data unavailable"
        }

# =========================
# IMAGE ANALYSIS
# =========================
@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    question: str = Query("What treatment do you recommend?")
):
    # Check if this is an insect identification request
    question_lower = question.lower()
    is_insect_query = '[insect]' in question_lower or 'insect' in question_lower
    
    if is_insect_query:
        # For insects, use LLM to provide identification help
        # Since we don't have an insect CNN model, provide general insect identification advice
        insect_advice = ask_llm(f"""You are an agricultural expert. A user has uploaded an image of an insect and asked: "{question}"

Please provide:
1. Possible identification of the insect
2. Characteristics to look for
3. Whether it's beneficial or a pest
4. Control methods if it's a pest
5. Prevention tips

Be specific and helpful based on common agricultural insects.""")
        
        return {
            "disease": "Insect Identification",
            "disease_title": "Insect Identification",
            "confidence": 0,
            "advice": f"🐛 Insect Identification Help:\n\n{insect_advice}\n\nNote: For accurate identification, please describe the insect's size, color, location on plant, and any damage you see.",
            "llm_mode": LLM_TYPE,
            "is_insect": True
        }
    
    # For plant diseases, use CNN model
    img = Image.open(io.BytesIO(await image.read())).convert("RGB")
    tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        probs = F.softmax(MODEL(tensor), dim=1)[0]

    conf, idx = torch.max(probs, 0)
    disease = CLASS_NAMES[idx.item()]
    confidence_score = round(conf.item() * 100, 2)
    
    # Get detailed advice from RAG
    advice = RAG.query(question, disease)

    # Format response better
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
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # First get coordinates
                    geo = await client.get(
                        "http://api.openweathermap.org/geo/1.0/direct",
                        params={"q": location, "limit": 1, "appid": OPENWEATHER_KEY}
                    )
                    geo_data = geo.json()
                    if geo_data and len(geo_data) > 0:
                        lat = geo_data[0]["lat"]
                        lon = geo_data[0]["lon"]
                        city_name = geo_data[0].get("name", location)
                        
                        # Get weather
                        w = await client.get(
                            "https://api.openweathermap.org/data/2.5/weather",
                            params={
                                "lat": lat,
                                "lon": lon,
                                "appid": OPENWEATHER_KEY,
                                "units": "metric"
                            }
                        )
                        w.raise_for_status()
                        weather_data = w.json()
                        
                        temp = weather_data.get("main", {}).get("temp")
                        feels_like = weather_data.get("main", {}).get("feels_like")
                        humidity = weather_data.get("main", {}).get("humidity")
                        description = weather_data.get("weather", [{}])[0].get("description", "")
                        wind_speed = weather_data.get("wind", {}).get("speed")
                        
                        response = f"🌤️ Weather in {city_name}:\n\n"
                        response += f"🌡️ Temperature: {temp:.1f}°C (feels like {feels_like:.1f}°C)\n"
                        response += f"☁️ Conditions: {description.title()}\n"
                        response += f"💧 Humidity: {humidity}%\n"
                        if wind_speed:
                            response += f"💨 Wind Speed: {wind_speed} m/s\n"
                        
                        return {"answer": response}
            except httpx.HTTPError as e:
                return {"answer": f"⚠️ Weather service temporarily unavailable. Please try again later."}
            except Exception as e:
                return {"answer": f"⚠️ Could not fetch weather data. Please make sure you mentioned a city name (e.g., 'weather in Chennai')."}
        
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
