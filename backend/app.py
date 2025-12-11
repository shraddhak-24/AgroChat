"""
AgroChat Backend API
Integrates CNN (disease detection) + RAG (knowledge retrieval) + LLM (advice) + Weather API
"""
# add near your other imports at the top of the file
from dotenv import load_dotenv
import httpx


import os
import sys
import json
import io
import subprocess
import traceback
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
from efficientnet_pytorch import EfficientNet

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

load_dotenv()   # <-- add this so os.getenv("WEATHER_KEY") works


# ============================================================================
# CONFIGURATION
# ============================================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", DEVICE)

# Auto-detect checkpoint path (same logic as notebook)
CHECKPOINT_LOCATIONS = [
    "models/efficientnet_b0_best.pth",
    "../models/efficientnet_b0_best.pth",
    "checkpoints/efficientnet_b0_best.pth",
    str(Path.home() / "Downloads" / "efficientnet_b0_best.pth"),
    str(Path.home() / "OneDrive" / "Documents" / "Desktop" / "AgroChat" / "models" / "efficientnet_b0_best.pth"),
]

CHECKPOINT_PATH = None
for path in CHECKPOINT_LOCATIONS:
    try:
        if os.path.exists(path):
            CHECKPOINT_PATH = path
            print(f"✅ Found checkpoint at: {path}")
            break
    except:
        pass

if not CHECKPOINT_PATH:
    raise FileNotFoundError("❌ Checkpoint file not found. Ensure efficientnet_b0_best.pth exists.")

# Disease knowledge base (same as notebook)
DISEASE_KNOWLEDGE = """
Pepper Bell Bacterial Spot:
- Symptoms: Small dark water-soaked spots on leaves and fruits, yellow halos
- Cause: Xanthomonas bacteria
- Organic Control: Neem oil, copper spray
- Chemical Control: Copper fungicide
- Prevention: Disease-free seeds, crop rotation

Pepper Bell Healthy:
- Condition: Normal growth, no infection
- Prevention: Proper irrigation, balanced fertilizer

Potato Early Blight:
- Symptoms: Brown concentric rings on lower leaves
- Cause: Alternaria solani
- Organic Control: Neem oil
- Chemical Control: Mancozeb
- Prevention: Crop rotation, avoid overhead irrigation

Potato Healthy:
- Condition: Normal leaf color, strong stems
- Prevention: Balanced nutrition, disease-free seed tubers

Potato Late Blight:
- Symptoms: Dark water-soaked lesions, white mold on leaf undersides, tuber rot
- Cause: Phytophthora infestans
- Organic Control: Neem oil, copper oxychloride
- Chemical Control: Mancozeb, Metalaxyl
- Prevention: Crop rotation, remove infected plant debris, avoid water stagnation

Tomato Bacterial Spot:
- Symptoms: Dark leaf spots, small scabby spots on fruit
- Cause: Xanthomonas bacteria
- Organic Control: Neem oil, copper sprays
- Chemical Control: Copper fungicides
- Prevention: Use certified seeds, avoid overhead irrigation

Tomato Early Blight:
- Symptoms: Brown leaf rings with concentric target-like spots
- Cause: Alternaria solani
- Organic Control: Neem oil, compost teas
- Chemical Control: Mancozeb, chlorothalonil
- Prevention: Crop rotation, remove infected leaves

Tomato Healthy:
- Condition: Healthy green leaves, no visible spots, good vigor
- Prevention: Proper irrigation, balanced fertilizer, good spacing

Tomato Late Blight:
- Symptoms: Black greasy lesions on leaves and stems, white mold under leaves
- Cause: Phytophthora infestans
- Organic Control: Neem oil, copper oxychloride
- Chemical Control: Mancozeb, Metalaxyl
- Prevention: Avoid water stagnation, remove infected plants

Tomato Leaf Mold:
- Symptoms: Yellow patches on upper leaf surface, olive-green mold on underside
- Cause: Passalora fulva (fungus)
- Organic Control: Good ventilation, pruning, neem oil
- Chemical Control: Fungicides containing copper or chlorothalonil
- Prevention: Avoid overcrowding, reduce humidity in greenhouse

Tomato Septoria Leaf Spot:
- Symptoms: Small circular brown spots with light centers and dark borders
- Cause: Septoria lycopersici fungus
- Organic Control: Neem oil, remove infected leaves
- Chemical Control: Protective fungicides (e.g., copper-based)
- Prevention: Crop rotation, avoid overhead watering

Tomato Spider Mites:
- Symptoms: Yellow speckling on leaves, fine webbing, leaf bronzing
- Cause: Spider mites (pest)
- Organic Control: Neem oil, insecticidal soap, water spray
- Prevention: Maintain plant health, avoid very dry dusty conditions

Tomato Target Spot:
- Symptoms: Circular dark spots with concentric rings, often on lower leaves
- Cause: Corynespora cassiicola fungus
- Organic Control: Neem oil, sanitation
- Chemical Control: Fungicidal sprays where permitted
- Prevention: Crop rotation, good airflow, remove infected debris

Tomato Mosaic Virus:
- Symptoms: Mottled light and dark green leaves, leaf distortion
- Cause: Tomato mosaic virus
- Organic Control: Remove infected plants, sanitize tools
- Prevention: Use virus-free seeds, avoid tobacco use near plants

Tomato Yellow Leaf Curl Virus:
- Symptoms: Curled yellow leaves, stunted plants
- Cause: Virus transmitted by whiteflies
- Organic Control: Yellow sticky traps, neem oil for whitefly control
- Prevention: Resistant varieties, whitefly management, remove infected plants
"""

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

# ============================================================================
# LLM & RAG CLASSES (identical to notebook)
# ============================================================================

def detect_available_llm():
    """Check which offline LLM is available."""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, timeout=2, text=True)
        if result.returncode == 0:
            return "ollama"
    except:
        pass
    
    try:
        from llama_cpp import Llama
        return "llama_cpp"
    except ImportError:
        pass
    
    return "stub"

LLM_TYPE = detect_available_llm()
print("LLM Mode:", LLM_TYPE.upper())

def ask_offline_llm(prompt: str) -> str:
    """Flexible offline LLM caller (ollama/llama_cpp/stub)."""
    global LLM_TYPE
    # ===== OLLAMA MODE =====
    if LLM_TYPE == "ollama":
        try:
            model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
            cmd = ["ollama", "run", model]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            output, error = process.communicate(prompt, timeout=60)
            if output and output.strip():
                return output.strip()
            else:
                return "⚠️ Ollama returned no output."
        except subprocess.TimeoutExpired:
            return "⚠️ Ollama timeout."
        except Exception as e:
            print(f"❌ Ollama failed: {e}. Falling back to stub.")
            LLM_TYPE = "stub"
    
    # ===== LLAMA_CPP MODE =====
    if LLM_TYPE == "llama_cpp":
        try:
            from llama_cpp import Llama
            model_path = os.getenv("LLAMA_MODEL_PATH")
            if not model_path or not os.path.exists(model_path):
                return "⚠️ LLAMA_MODEL_PATH env var not set or file not found."
            
            llm = Llama(model_path=model_path, n_gpu_layers=-1)
            resp = llm.create(prompt=prompt, max_tokens=512, temperature=0.1)
            choices = resp.get("choices", [])
            if choices:
                return choices[0].get("text", "").strip()
            return "⚠️ llama_cpp returned empty response."
        except Exception as e:
            print(f"❌ llama_cpp failed: {e}. Falling back to stub.")
            LLM_TYPE = "stub"
    
    # ===== STUB MODE =====
    if LLM_TYPE == "stub":
        return f"[STUB LLM] Question: {prompt[:80]}... | Answer: Install Ollama or llama-cpp-python for real responses."
    
    return "❌ Unknown LLM mode."

class OfflineAgriculturalRAG:
    def __init__(self, knowledge_base: str, class_to_title: dict):
        self.knowledge_base = knowledge_base.strip()
        self.class_to_title = class_to_title

    def _get_block_for_class(self, disease_class: str) -> str:
        title = self.class_to_title.get(disease_class)
        if not title:
            return self.knowledge_base
        blocks = self.knowledge_base.split("\n\n")
        for block in blocks:
            first_line = block.splitlines()[0].rstrip(":").strip()
            if first_line.lower() == title.lower():
                return block
        return self.knowledge_base

    def query(self, user_question: str, disease_class: str) -> str:
        """
        Query RAG for disease-specific knowledge.
        Args:
            user_question: User's question
            disease_class: CNN-predicted disease class (e.g., 'Tomato_Early_blight')
        Returns:
            Formatted advice with disease info and knowledge
        """
        filtered_knowledge = self._get_block_for_class(disease_class)
        disease_title = self.class_to_title.get(disease_class, disease_class)

        # If an LLM runtime is available, synthesize a concise, safe reply
        # using the RAG knowledge as the only source. Otherwise return raw knowledge.
        try:
            if LLM_TYPE != "stub":
                # Build a constrained prompt that prevents hallucination
                prompt = (
                    "You are a concise agricultural assistant. Only use the information in the KNOWLEDGE section below. "
                    "If the knowledge does not contain an answer, respond exactly: 'Not specified in knowledge.'\n\n"
                    "USER QUESTION:\n" + user_question + "\n\n"
                    "KNOWLEDGE:\n" + filtered_knowledge + "\n\n"
                    "INSTRUCTIONS:\n1) Provide a one- or two-sentence direct answer.\n2) Then list up to three practical numbered steps the user can take.\n3) Do not add any information not in KNOWLEDGE.\n\n"
                    "RESPONSE:"
                )
                llm_out = ask_offline_llm(prompt)
                if llm_out and llm_out.strip():
                    # Return LLM output plus the raw knowledge as details
                    return f"{llm_out}\n\nDetails:\n{filtered_knowledge}"
        except Exception as e:
            print(f"LLM synthesis failed: {e}")

        # Fallback: return formatted knowledge directly (no LLM wrapping)
        response = f"Disease: {disease_title}\n\nInformation:\n{filtered_knowledge}"
        return response

# ============================================================================
# CNN MODEL LOADING
# ============================================================================

def load_cnn_model():
    """Load EfficientNet-B0 model with checkpoint."""
    try:
        checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
        class_names = checkpoint["classes"]
        
        model = EfficientNet.from_pretrained(
            "efficientnet-b0",
            num_classes=len(class_names)
        )
        model.load_state_dict(checkpoint["model"])
        model.to(DEVICE)
        model.eval()
        
        print("CNN Model Loaded. Classes:", len(class_names))
        return model, class_names
    except Exception as e:
        print(f"❌ Failed to load CNN model: {e}")
        raise

MODEL, CLASS_NAMES = load_cnn_model()
RAG = OfflineAgriculturalRAG(DISEASE_KNOWLEDGE, CLASS_TO_TITLE)

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="AgroChat Backend", version="1.0.0")

# CORS Configuration (allow frontend on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize persistence DB
try:
    from . import db as persistence
except Exception:
    import db as persistence

try:
    persistence.init_db()
    DB_STATUS = True
except Exception as e:
    print(f"Failed to initialize DB: {e}")
    DB_STATUS = False

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health")
def health_check():
    """System health status."""
    return {
        "status": "healthy",
        "llm_mode": LLM_TYPE,
        "device": str(DEVICE),
        "cnn_classes": len(CLASS_NAMES),
        "db_ok": DB_STATUS,
    }

# -------------------------------
# WEATHER: OpenWeather Geocoding + Weather
# -------------------------------
OPENWEATHER_KEY = os.getenv("WEATHER_KEY")
if not OPENWEATHER_KEY:
    print("Warning: WEATHER_KEY not set in .env — /weather endpoint will fail until you set it.")

# TTL (hours) for stored weather memory
WEATHER_TTL_HOURS = float(os.getenv("WEATHER_TTL_HOURS", "24"))

@app.get("/weather")
async def get_weather(query: str = Query(..., description="City or locality, e.g. 'Bengaluru Indiranagar'")):
    """
    Returns simplified weather for any city/locality string.
    Uses OpenWeather Geocoding API to convert the query into lat/lon,
    then fetches weather using lat/lon for better locality handling.
    """
    if not OPENWEATHER_KEY:
        raise HTTPException(status_code=500, detail="WEATHER_KEY not configured in server environment")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1) Geocoding: query -> lat/lon
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": query, "limit": 1, "appid": OPENWEATHER_KEY}
        geo_resp = await client.get(geo_url, params=geo_params)
        if geo_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Geocoding service failed")
        geo_json = geo_resp.json()
        if not geo_json:
            raise HTTPException(status_code=404, detail=f"Location not found for '{query}'")

        lat = geo_json[0].get("lat")
        lon = geo_json[0].get("lon")
        name = geo_json[0].get("name")
        state = geo_json[0].get("state")
        country = geo_json[0].get("country")

        # 2) Weather by lat/lon - fetch current + 3-day forecast using OpenWeather "forecast" endpoint
        # Note: the free forecast API returns 3-hour steps for 5 days; we aggregate into daily summaries
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"}
        fresp = await client.get(forecast_url, params=forecast_params)
        if fresp.status_code != 200:
            raise HTTPException(status_code=502, detail="Forecast service failed")
        fjson = fresp.json()

        # current weather (best-effort): try using first item or separate current endpoint
        # We'll call the current weather endpoint too to get instantaneous values
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"}
        wresp = await client.get(weather_url, params=weather_params)
        if wresp.status_code != 200:
            w = {}
        else:
            w = wresp.json()

        # Aggregate forecast into days (local date strings)
        from datetime import datetime, timezone
        daily = {}
        try:
            for item in fjson.get("list", []):
                ts = item.get("dt")
                if ts is None:
                    continue
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                day_key = dt.date().isoformat()
                temps = daily.setdefault(day_key, {"temps": [], "descs": []})
                temps["temps"].append(item.get("main", {}).get("temp"))
                desc = (item.get("weather") or [{}])[0].get("description")
                if desc:
                    temps["descs"].append(desc)
        except Exception:
            daily = {}

        # Build forecast list for next 3 calendar days (skip today if needed)
        today_key = datetime.utcnow().date().isoformat()
        forecast_days = []
        for dkey in sorted(daily.keys()):
            if len(forecast_days) >= 3:
                break
            # include today and next days; this returns up to 3 days
            temps = daily[dkey].get("temps", [])
            descs = daily[dkey].get("descs", [])
            if temps:
                forecast_days.append({
                    "date": dkey,
                    "temp_min": min(temps),
                    "temp_max": max(temps),
                    "description": max(set(descs), key=descs.count) if descs else None,
                })

        location_display = f"{name}{', ' + state if state else ''}, {country}"
        result = {
            "success": True,
            "queried": query,
            "location": location_display,
            "lat": lat,
            "lon": lon,
            "temperature_c": w.get("main", {}).get("temp"),
            "feels_like_c": w.get("main", {}).get("feels_like"),
            "humidity": w.get("main", {}).get("humidity"),
            "wind_m_s": w.get("wind", {}).get("speed"),
            "description": (w.get("weather") or [{}])[0].get("description"),
            "forecast_3days": forecast_days,
            "raw_forecast": fjson,
        }

        # Persist the result into the DB for memory retrieval
        try:
            # use the incoming query string as the memory key so variations like 'Bengaluru' are distinct
            persistence.upsert_weather(location=query, location_display=location_display, lat=lat, lon=lon, data=result)
        except Exception as e:
            print(f"Warning: failed to save weather memory: {e}")

        return result


# --- Weather by coordinates (lat, lon) - useful for browser geolocation ---
@app.get("/weather_coords")
async def get_weather_coords(lat: float = Query(..., description="Latitude"), lon: float = Query(..., description="Longitude")):
    """
    Returns weather using latitude and longitude directly (avoids geocoding step).
    """
    if not OPENWEATHER_KEY:
        raise HTTPException(status_code=500, detail="WEATHER_KEY not configured in server environment")

    async with httpx.AsyncClient(timeout=10.0) as client:
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"}
        wresp = await client.get(weather_url, params=params)
        if wresp.status_code != 200:
            raise HTTPException(status_code=502, detail="Weather service failed")
        w = wresp.json()

    location_display = f"{w.get('name') or ''}{', ' + (w.get('sys') or {}).get('country') if (w.get('sys') or {}).get('country') else ''}".strip(', ')
    result = {
        "success": True,
        "lat": lat,
        "lon": lon,
        "location": location_display,
        "temperature_c": w.get("main", {}).get("temp"),
        "feels_like_c": w.get("main", {}).get("feels_like"),
        "humidity": w.get("main", {}).get("humidity"),
        "wind_m_s": w.get("wind", {}).get("speed"),
        "description": (w.get("weather") or [{}])[0].get("description"),
    }
    return result


@app.get("/weather_memory/{location}")
def read_weather_memory(location: str):
    """Return stored weather memory for a given location key (normalized)."""
    try:
        mem = persistence.get_weather(location)
        if not mem:
            raise HTTPException(status_code=404, detail="No stored weather for that location")
        return {"found": True, "memory": mem}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN ANALYSIS ENDPOINT
# ============================================================================

@app.post("/analyze")
async def analyze_plant(
    image: UploadFile = File(...),
    question: str = Query("What treatment do you recommend?"),
    context: str = Form(None),
):
    """
    Analyze plant image for disease detection + RAG-guided advice.
    
    Args:
        image: Uploaded plant image file
        question: User's question about the disease/treatment
    
    Returns:
        {
            "disease": "Tomato Early Blight",
            "confidence": 0.95,
            "advice": "...",
            "llm_mode": "ollama"
        }
    """
    try:
        # Read image
        image_data = await image.read()
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Preprocess
        img_tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)
        
        # CNN Inference
        with torch.no_grad():
            logits = MODEL(img_tensor)
            probs = F.softmax(logits, dim=1)[0]
        
        conf, idx = torch.max(probs, 0)
        disease = CLASS_NAMES[idx.item()]
        confidence = float(conf)
        
        # If context provided from frontend (previous messages), prepend to question
        if context:
            try:
                ctx = context.strip()
                question = f"Context:\n{ctx}\n\nFollow-up question:\n{question}"
            except Exception:
                pass

        # RAG + LLM Query
        advice = RAG.query(user_question=question, disease_class=disease)
        
        return {
            "success": True,
            "disease": disease,
            "confidence": round(confidence * 100, 2),
            "advice": advice,
            "llm_mode": LLM_TYPE,
        }
    
    except Exception as e:
        print("Error in /analyze:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# Conversation persistence
# ==========================

@app.get('/conversations')
def list_conversations():
    try:
        convs = persistence.get_all_conversations()
        return {"total": len(convs), "conversations": convs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/conversations')
def upsert_conversation(conv: dict = Body(...)):
    try:
        if not conv.get('id'):
            raise HTTPException(status_code=400, detail='Conversation must have id')
        persistence.upsert_conversation(conv)
        return {"success": True, "id": conv.get('id')}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/conversations/{conv_id}')
def get_conversation(conv_id: str):
    try:
        conv = persistence.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail='Not found')
        return conv
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# GENERAL TEXT CHAT ENDPOINT (NO IMAGE REQUIRED)
# ============================================================================

from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    context: list | None = None  # list of {"type": "user"/"bot", "text": "..."}

@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    """
    General text chat endpoint.
    Uses your offline LLM system (ollama / llama_cpp / stub).
    """

    # Build context string from last few messages
    ctx_lines = []
    if payload.context:
        for msg in payload.context[-6:]:
            role = msg.get("type", "user")
            txt = msg.get("text", "")
            ctx_lines.append(f"{role.upper()}: {txt}")
    context_text = "\n".join(ctx_lines)

    # Build prompt for the offline LLM
    prompt = (
        "You are AgroChat, an agricultural assistant. "
        "Stick to safe and common agricultural knowledge. "
        "If uncertain, say you are not sure.\n\n"
    )

    if context_text:
        prompt += f"Conversation so far:\n{context_text}\n\n"

    prompt += f"User question:\n{payload.question}\n\nAnswer:"
    # Special-case: if the user is asking about weather, fetch weather first
    q = (payload.question or "").lower()
    weather_keywords = ["weather", "temperature", "climate", "forecast", "rain", "rainfall"]
    if any(k in q for k in weather_keywords):
        # Try to extract a location from the question (very lightweight)
        import re
        loc_match = re.search(r"(?:in|at|for)\s+([A-Za-z0-9 ,]+)", payload.question or "", re.IGNORECASE)
        location = None
        if loc_match:
            location = loc_match.group(1).strip()

        # If we have a location, first check stored weather memory in DB
        if location:
            try:
                weather_data = None
                try:
                    stored = persistence.get_weather(location)
                except Exception:
                    stored = None

                import time, httpx
                now = time.time()
                if stored and stored.get("updated_at") and (stored.get("updated_at") + WEATHER_TTL_HOURS * 3600) >= now:
                    # Use stored data
                    weather_data = stored.get("data")
                else:
                    # Fetch fresh via internal /weather endpoint which also persists
                    geo_url = f"http://127.0.0.1:8005/weather?query={httpx.utils.quote(location)}"
                    try:
                        with httpx.Client(timeout=10.0) as client:
                            resp = client.get(geo_url)
                            if resp.status_code == 200:
                                weather_data = resp.json()
                    except Exception:
                        weather_data = None

                # Normalize fields and respond
                if weather_data and weather_data.get("success"):
                    temp = weather_data.get("temperature_c") or weather_data.get("temperature")
                    feels = weather_data.get("feels_like_c") or weather_data.get("feels_like")
                    humidity = weather_data.get("humidity")
                    desc = weather_data.get("description") or (weather_data.get("weather") or [{}])[0].get("description")
                    location_display = weather_data.get("location") or weather_data.get("city") or location

                    # If an LLM is available, ask it to craft a friendly weather reply including stored forecast
                    if LLM_TYPE != "stub":
                        # include the 3-day forecast if present
                        forecast = weather_data.get("forecast_3days") or []
                        forecast_lines = "\n".join([f"{f.get('date')}: {f.get('description')} (min {f.get('temp_min')}°C / max {f.get('temp_max')}°C)" for f in forecast])
                        weather_prompt = (
                            "You are a friendly assistant. The user asked about the weather.\n"
                            f"Location: {location_display}\n"
                            f"Temperature: {temp} C\n"
                            f"Feels like: {feels} C\n"
                            f"Humidity: {humidity}%\n"
                            f"Conditions: {desc}\n\n"
                            f"3-day forecast:\n{forecast_lines}\n\n"
                            "Provide a concise conversational reply (2-3 sentences) and one short suggestion for the user (e.g., take an umbrella)."
                        )
                        llm_resp = ask_offline_llm(weather_prompt)
                        return {"answer": llm_resp}
                    else:
                        forecast = weather_data.get("forecast_3days") or []
                        forecast_text = ", ".join([f"{f.get('date')}: {f.get('description')}" for f in forecast])
                        text = f"Weather in {location_display}: {desc or 'N/A'}. Temperature {temp}°C (feels like {feels}°C). Humidity {humidity}%. Forecast: {forecast_text}"
                        return {"answer": text}
            except Exception as e:
                # Fall through to default behavior if weather call fails
                print(f"Weather handling error: {e}")

    # Call your offline LLM for other queries
    answer = ask_offline_llm(prompt)

    return {"answer": answer}


# ============================================================================
# BATCH ANALYSIS ENDPOINT (multiple images)
# ============================================================================

@app.post("/analyze_batch")
async def analyze_batch(
    images: list[UploadFile] = File(...),
    question: str = Query("What treatment do you recommend?"),
):
    """Analyze multiple plant images."""
    results = []
    
    for image in images:
        try:
            image_data = await image.read()
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                logits = MODEL(img_tensor)
                probs = F.softmax(logits, dim=1)[0]
            
            conf, idx = torch.max(probs, 0)
            disease = CLASS_NAMES[idx.item()]
            confidence = float(conf)
            
            prediction = {"disease": disease, "confidence": confidence}
            # RAG.query expects (user_question, disease_class)
            try:
                advice = RAG.query(user_question=question, disease_class=disease)
            except TypeError:
                # Backwards-compatibility: some older callers may pass a dict
                advice = RAG.query(user_question=question, disease_class=prediction.get('disease'))
            
            results.append({
                "image": image.filename,
                "disease": disease,
                "confidence": round(confidence * 100, 2),
                "advice": advice,
            })
        except Exception as e:
            results.append({
                "image": image.filename,
                "error": str(e),
            })
    
    return {"results": results}

# ============================================================================
# DISEASE INFO ENDPOINT
# ============================================================================

@app.get("/disease/{disease_name}")
def get_disease_info(disease_name: str):
    """Get knowledge base info for a specific disease."""
    rag_instance = OfflineAgriculturalRAG(DISEASE_KNOWLEDGE, CLASS_TO_TITLE)
    block = rag_instance._get_block_for_class(disease_name)
    
    if not block or block == DISEASE_KNOWLEDGE:
        raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found.")
    
    return {
        "disease": disease_name,
        "knowledge": block,
    }

# ============================================================================
# AVAILABLE DISEASES ENDPOINT
# ============================================================================

@app.get("/diseases")
def list_diseases():
    """List all recognized diseases."""
    return {
        "total": len(CLASS_NAMES),
        "classes": CLASS_NAMES,
        "class_to_title_mapping": CLASS_TO_TITLE,
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("AgroChat Backend Starting...")
    print("="*60)
    print("API: http://127.0.0.1:8005")
    print("Docs: http://127.0.0.1:8005/docs")
    print("LLM:", LLM_TYPE.upper())
    print("="*60 + "\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
