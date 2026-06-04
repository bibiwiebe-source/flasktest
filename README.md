# WeatherScope Flask Dashboard

Modernes Wetterdashboard mit Flask-Backend, Frontend und Nginx-Reverse-Proxy. Die Wetterdaten kommen von Open-Meteo und funktionieren ohne API-Key.

## Start mit Docker und Nginx

```bash
docker compose up --build
```

Danach ist die App erreichbar unter:

```text
http://localhost:8080
```

## Lokale Entwicklung ohne Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Danach laeuft Flask unter:

```text
http://localhost:5000
```

## Struktur

```text
app.py                 Flask-App mit API-Endpunkten
templates/index.html   Frontend-Seite
static/css/styles.css  modernes UI-Styling
static/js/app.js       Ortssuche und Dashboard-Rendering
nginx/default.conf     Nginx Reverse Proxy
docker-compose.yml     Flask + Nginx Setup
Dockerfile             Flask Container
```

## API

- `GET /api/locations?q=Berlin` sucht Orte.
- `GET /api/weather?lat=52.52&lon=13.41&label=Berlin` liefert aktuelle Werte, Stundenprognose und 7-Tage-Prognose.
