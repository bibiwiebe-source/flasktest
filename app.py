from datetime import datetime, timedelta, timezone
from os import environ

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

FALLBACK_LOCATIONS = [
    {"name": "Berlin", "admin1": "Berlin", "country": "Germany", "latitude": 52.52, "longitude": 13.405, "timezone": "Europe/Berlin"},
    {"name": "Hamburg", "admin1": "Hamburg", "country": "Germany", "latitude": 53.5511, "longitude": 9.9937, "timezone": "Europe/Berlin"},
    {"name": "Munich", "admin1": "Bavaria", "country": "Germany", "latitude": 48.1374, "longitude": 11.5755, "timezone": "Europe/Berlin"},
    {"name": "Cologne", "admin1": "North Rhine-Westphalia", "country": "Germany", "latitude": 50.9375, "longitude": 6.9603, "timezone": "Europe/Berlin"},
    {"name": "Frankfurt am Main", "admin1": "Hesse", "country": "Germany", "latitude": 50.1109, "longitude": 8.6821, "timezone": "Europe/Berlin"},
    {"name": "Stuttgart", "admin1": "Baden-Wuerttemberg", "country": "Germany", "latitude": 48.7758, "longitude": 9.1829, "timezone": "Europe/Berlin"},
    {"name": "Dusseldorf", "admin1": "North Rhine-Westphalia", "country": "Germany", "latitude": 51.2277, "longitude": 6.7735, "timezone": "Europe/Berlin"},
    {"name": "New York", "admin1": "New York", "country": "United States", "latitude": 40.7128, "longitude": -74.006, "timezone": "America/New_York"},
    {"name": "London", "admin1": "England", "country": "United Kingdom", "latitude": 51.5072, "longitude": -0.1276, "timezone": "Europe/London"},
    {"name": "Paris", "admin1": "Ile-de-France", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone": "Europe/Paris"},
]

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


def normalize_location(item):
    return {
        "id": f"{item['latitude']},{item['longitude']}",
        "name": item.get("name"),
        "country": item.get("country"),
        "admin1": item.get("admin1"),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "timezone": item.get("timezone"),
    }


def fallback_location_search(query):
    needle = query.casefold()
    matches = [
        normalize_location(item)
        for item in FALLBACK_LOCATIONS
        if needle in item["name"].casefold()
    ]
    return matches or [normalize_location(FALLBACK_LOCATIONS[0])]


def fallback_weather(label):
    now = datetime.now(timezone.utc)
    return {
        "location": label,
        "timezone": "offline-demo",
        "generatedAt": now.isoformat(),
        "offline": True,
        "current": {
            "temperature": 20,
            "feelsLike": 19,
            "humidity": 62,
            "precipitation": 0,
            "windSpeed": 12,
            "windDirection": 180,
            "description": "Offline demo data",
            "icon": "cloud-sun",
            "isDay": True,
        },
        "hourly": [
            {
                "time": (now + timedelta(hours=hour)).isoformat(),
                "temperature": 18 + (hour % 5),
                "rainChance": 20 + (hour % 4) * 5,
                "description": "Demo weather",
            }
            for hour in range(12)
        ],
        "daily": [
            {
                "time": (now + timedelta(days=day)).date().isoformat(),
                "high": 21 + day,
                "low": 12 + day,
                "rainChance": 25 + day * 3,
                "windSpeed": 14 + day,
                "description": "Demo forecast",
                "icon": "cloud-sun",
            }
            for day in range(7)
        ],
    }


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
        return jsonify({"locations": fallback_location_search(query), "offline": True})

    results = response.json().get("results", [])
    locations = [
        normalize_location(item)
        for item in results
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    return jsonify({"locations": locations or fallback_location_search(query)})


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
                "hourly": ["temperature_2m", "precipitation_probability", "weather_code"],
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
        return jsonify(fallback_weather(label))

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
