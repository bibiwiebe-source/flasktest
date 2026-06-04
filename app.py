from datetime import datetime, timezone
from os import environ

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: ("Clear sky", "sun"),
    1: ("Mainly clear", "sun"),
    2: ("Partly cloudy", "cloud-sun"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "cloud-fog"),
    48: ("Depositing rime fog", "cloud-fog"),
    51: ("Light drizzle", "cloud-drizzle"),
    53: ("Moderate drizzle", "cloud-drizzle"),
    55: ("Dense drizzle", "cloud-drizzle"),
    61: ("Slight rain", "cloud-rain"),
    63: ("Moderate rain", "cloud-rain"),
    65: ("Heavy rain", "cloud-rain"),
    71: ("Slight snow", "cloud-snow"),
    73: ("Moderate snow", "cloud-snow"),
    75: ("Heavy snow", "cloud-snow"),
    80: ("Rain showers", "cloud-rain"),
    81: ("Heavy showers", "cloud-rain"),
    82: ("Violent showers", "cloud-rain"),
    95: ("Thunderstorm", "cloud-lightning"),
    96: ("Thunderstorm with hail", "cloud-lightning"),
    99: ("Thunderstorm with heavy hail", "cloud-lightning"),
}


def weather_label(code):
    return WEATHER_CODES.get(code, ("Unknown conditions", "cloud-question"))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/locations")
def locations():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"locations": []})

    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": query, "count": 8, "language": "en", "format": "json"},
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"error": "Location search is currently unavailable."}), 502

    results = response.json().get("results", [])
    locations = [
        {
            "id": f"{item['latitude']},{item['longitude']}",
            "name": item.get("name"),
            "country": item.get("country"),
            "admin1": item.get("admin1"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "timezone": item.get("timezone"),
        }
        for item in results
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    return jsonify({"locations": locations})


@app.get("/api/weather")
def weather():
    latitude = request.args.get("lat")
    longitude = request.args.get("lon")
    label = request.args.get("label", "Selected location")

    if not latitude or not longitude:
        return jsonify({"error": "Latitude and longitude are required."}), 400

    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "is_day",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                ],
                "hourly": [
                    "temperature_2m",
                    "precipitation_probability",
                    "weather_code",
                ],
                "daily": [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                ],
                "timezone": "auto",
                "forecast_days": 7,
            },
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"error": "Weather data is currently unavailable."}), 502

    payload = response.json()
    current = payload.get("current", {})
    code = current.get("weather_code")
    description, icon = weather_label(code)
    hourly = payload.get("hourly", {})
    daily = payload.get("daily", {})

    return jsonify(
        {
            "location": label,
            "timezone": payload.get("timezone"),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "current": {
                "temperature": current.get("temperature_2m"),
                "feelsLike": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "precipitation": current.get("precipitation"),
                "windSpeed": current.get("wind_speed_10m"),
                "windDirection": current.get("wind_direction_10m"),
                "description": description,
                "icon": icon,
                "isDay": current.get("is_day") == 1,
            },
            "hourly": [
                {
                    "time": time,
                    "temperature": temp,
                    "rainChance": rain,
                    "description": weather_label(code)[0],
                }
                for time, temp, rain, code in zip(
                    hourly.get("time", [])[:12],
                    hourly.get("temperature_2m", [])[:12],
                    hourly.get("precipitation_probability", [])[:12],
                    hourly.get("weather_code", [])[:12],
                )
            ],
            "daily": [
                {
                    "time": time,
                    "high": high,
                    "low": low,
                    "rainChance": rain,
                    "windSpeed": wind,
                    "description": weather_label(code)[0],
                    "icon": weather_label(code)[1],
                }
                for time, high, low, rain, wind, code in zip(
                    daily.get("time", []),
                    daily.get("temperature_2m_max", []),
                    daily.get("temperature_2m_min", []),
                    daily.get("precipitation_probability_max", []),
                    daily.get("wind_speed_10m_max", []),
                    daily.get("weather_code", []),
                )
            ],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)), debug=True)
