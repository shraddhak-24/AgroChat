from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change later to ["http://localhost:3000"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "dbc71fcca974cbc48c309237171b1f72"  # your OpenWeatherMap key
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# --- Root route ---
@app.get("/")
def root():
    return {"message": "Welcome to AgroGPT Weather API!"}


# --- Current Weather ---
@app.get("/weather")
def get_weather(city: str = Query(..., description="City name to fetch weather for")):
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if response.status_code != 200:
        return {"error": data.get("message", "Failed to fetch weather")}

    return {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"]
    }


# --- 5-Day Forecast ---
@app.get("/forecast")
def get_forecast(city: str = Query(..., description="City name for 5-day forecast")):
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    response = requests.get(FORECAST_URL, params=params)
    data = response.json()

    if response.status_code != 200:
        return {"error": data.get("message", "Failed to fetch forecast")}

    forecast_data = []
    for item in data["list"][:5]:
        forecast_data.append({
            "datetime": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "description": item["weather"][0]["description"]
        })

    return {"city": city, "forecast": forecast_data}


# --- Soil Information ---
@app.get("/soil")
def get_soil_info(city: str = Query(..., description="City name to fetch soil info")):
    # Dummy data for now
    soil_data = {
        "Hyderabad": {"soil_type": "Red Sandy", "ph": 6.8, "moisture": "Medium"},
        "Delhi": {"soil_type": "Alluvial", "ph": 7.2, "moisture": "Low"},
        "Chennai": {"soil_type": "Clayey", "ph": 6.5, "moisture": "High"}
    }

    return soil_data.get(city, {"error": f"No soil data found for {city}"})


# --- Crop Suggestion ---
@app.get("/crop_suggestion")
def crop_suggestion(city: str = Query(..., description="City name to suggest crops")):
    soil_info = get_soil_info(city)
    if "error" in soil_info:
        return soil_info

    suggestions = {
        "Red Sandy": ["Groundnut", "Millets", "Cotton"],
        "Alluvial": ["Wheat", "Rice", "Sugarcane"],
        "Clayey": ["Paddy", "Sugarcane", "Banana"]
    }

    crops = suggestions.get(soil_info["soil_type"], [])
    return {
        "city": city,
        "soil_type": soil_info["soil_type"],
        "recommended_crops": crops
    }
