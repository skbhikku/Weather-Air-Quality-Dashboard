
"""
Weather and Air Quality Monitoring Dashboard
Flask backend using Open-Meteo APIs.
"""

from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 10

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
    3: "Overcast", 45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain",
    63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow",
    75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers",
    86: "Heavy snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def validate_city(city: str) -> str:
    """Validate and clean a city name."""
    if not isinstance(city, str):
        raise ValueError("City must be text.")

    city = city.strip()

    if not city:
        raise ValueError("Enter a city name.")

    if len(city) > 100:
        raise ValueError("City name is too long.")

    return city


def request_json(url, params):
    """Fetch JSON from an API with timeout and validation."""
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected API response.")

    return data


def geocode_city(city: str) -> dict:
    """Find coordinates for a city."""
    data = request_json(
        GEOCODING_URL,
        {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    results = data.get("results")

    if not results:
        raise ValueError(f"Location '{city}' not found.")

    place = results[0]

    parts = [
        place.get("name"),
        place.get("admin1"),
        place.get("country"),
    ]

    return {
        "name": ", ".join(p for p in parts if p),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "country": place.get("country", ""),
    }


def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch current weather and a seven-day forecast."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,wind_speed_10m,weather_code"
        ),
        "daily": (
            "weather_code,temperature_2m_max,"
            "temperature_2m_min"
        ),
        "timezone": "auto",
        "forecast_days": 7,
    }

    return request_json(WEATHER_URL, params)


def fetch_air_quality(lat: float, lon: float) -> dict:
    """Fetch AQI and air pollutant readings."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "us_aqi,pm2_5,pm10,carbon_monoxide,"
            "nitrogen_dioxide,sulphur_dioxide,ozone"
        ),
        "timezone": "auto",
    }

    return request_json(AIR_QUALITY_URL, params)


def safe_value(mapping: dict, key: str):
    """Return None when a value is unavailable."""
    if not mapping:
        return None

    return mapping.get(key)


def describe_weather(code):
    """Convert a weather code to a readable description."""
    if code is None:
        return "Unknown"

    try:
        return WEATHER_CODES.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def aqi_category(aqi):
    """Return the US AQI category and its display color."""
    if aqi is None:
        return "Unavailable", "#888888"

    try:
        aqi = float(aqi)
    except (TypeError, ValueError):
        return "Unknown", "#888888"

    if aqi < 0:
        return "Unknown", "#888888"
    if aqi <= 50:
        return "Good", "#00e400"
    if aqi <= 100:
        return "Moderate", "#ffff00"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups", "#ff7e00"
    if aqi <= 200:
        return "Unhealthy", "#ff0000"
    if aqi <= 300:
        return "Very Unhealthy", "#8f3f97"

    return "Hazardous", "#7e0023"


def make_daily_forecast(daily: dict) -> list:
    """Prepare daily forecast data for the frontend."""
    if not daily:
        return []

    dates = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])

    forecast = []

    for i, date in enumerate(dates):
        code = codes[i] if i < len(codes) else None

        forecast.append({
            "date": date,
            "high_c": highs[i] if i < len(highs) else None,
            "low_c": lows[i] if i < len(lows) else None,
            "weather_code": code,
            "description": describe_weather(code),
        })

    return forecast


def build_dashboard(city: str) -> dict:
    """Build the complete dashboard response."""
    city = validate_city(city)

    location = geocode_city(city)
    lat = location["latitude"]
    lon = location["longitude"]

    weather = fetch_weather(lat, lon)
    air = fetch_air_quality(lat, lon)

    current = weather.get("current") or {}
    air_current = air.get("current") or {}

    aqi = safe_value(air_current, "us_aqi")
    category, color = aqi_category(aqi)

    weather_code = safe_value(current, "weather_code")

    return {
        "location": location,
        "weather": {
            "current": {
                "temperature_c": safe_value(
                    current, "temperature_2m"
                ),
                "feels_like_c": safe_value(
                    current, "apparent_temperature"
                ),
                "humidity_percent": safe_value(
                    current, "relative_humidity_2m"
                ),
                "wind_speed_kmh": safe_value(
                    current, "wind_speed_10m"
                ),
                "weather_code": weather_code,
                "description": describe_weather(weather_code),
            },
            "daily": make_daily_forecast(
                weather.get("daily") or {}
            ),
        },
        "air_quality": {
            "current": {
                "aqi": aqi,
                "aqi_category": category,
                "aqi_color": color,
                "pm2_5": safe_value(air_current, "pm2_5"),
                "pm10": safe_value(air_current, "pm10"),
                "co": safe_value(air_current, "carbon_monoxide"),
                "no2": safe_value(air_current, "nitrogen_dioxide"),
                "so2": safe_value(air_current, "sulphur_dioxide"),
                "o3": safe_value(air_current, "ozone"),
            }
        },
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/dashboard")
def api_dashboard():
    city = request.args.get("city", "")

    try:
        return jsonify(build_dashboard(city))

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException:
        app.logger.exception("Weather API request failed")
        return jsonify({
            "error": "Could not reach the weather service. Try again."
        }), 502

    except Exception:
        app.logger.exception("Unexpected dashboard error")
        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
    )
