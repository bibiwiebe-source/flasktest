const searchForm = document.querySelector("#searchForm");
const cityInput = document.querySelector("#cityInput");
const locationList = document.querySelector("#locationList");
const statusBar = document.querySelector("#statusBar");
const searchButton = document.querySelector("#searchButton");

const iconMap = {
  "sun": "SUN",
  "cloud-sun": "SUN+",
  "cloud": "CLD",
  "cloud-fog": "FOG",
  "cloud-drizzle": "DRZ",
  "cloud-rain": "RAIN",
  "cloud-snow": "SNOW",
  "cloud-lightning": "THR",
  "cloud-question": "?"
};

function setStatus(message, isError = false) {
  statusBar.textContent = message;
  statusBar.classList.toggle("error", isError);
}

function formatLocation(location) {
  return [location.name, location.admin1, location.country].filter(Boolean).join(", ");
}

function formatHour(value) {
  return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatDay(value) {
  return new Intl.DateTimeFormat("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" }).format(new Date(value));
}

function number(value, fallback = "--") {
  return value === null || value === undefined ? fallback : Math.round(value);
}

function demoWeather(location, reason) {
  const now = new Date();
  return {
    location: formatLocation(location),
    timezone: "browser-demo",
    offline: true,
    errorReason: reason,
    current: {
      temperature: 20,
      feelsLike: 19,
      humidity: 62,
      precipitation: 0,
      windSpeed: 12,
      description: "Demo weather",
      icon: "cloud-sun"
    },
    hourly: Array.from({ length: 12 }, (_, index) => ({
      time: new Date(now.getTime() + index * 60 * 60 * 1000).toISOString(),
      temperature: 18 + (index % 5),
      rainChance: 20 + (index % 4) * 5
    })),
    daily: Array.from({ length: 7 }, (_, index) => ({
      time: new Date(now.getTime() + index * 24 * 60 * 60 * 1000).toISOString(),
      high: 21 + index,
      low: 12 + index,
      rainChance: 25 + index * 3,
      windSpeed: 14 + index,
      description: "Demo forecast"
    }))
  };
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);

  let response;
  try {
    response = await fetch(url, { signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Die Anfrage hat zu lange gedauert. Bitte nochmal versuchen.");
    }
    throw new Error("Netzwerkfehler beim Laden. Bitte pruefe, ob die Container laufen.");
  } finally {
    clearTimeout(timeout);
  }

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : { error: await response.text() };

  if (!response.ok) {
    throw new Error(body.error || "Die Anfrage ist fehlgeschlagen.");
  }
  return body;
}

async function searchLocations(query) {
  setStatus("Suche passende Orte...");
  searchButton.disabled = true;
  searchButton.textContent = "Sucht...";
  locationList.innerHTML = "";

  try {
    const data = await fetchJson(`/api/locations?q=${encodeURIComponent(query)}`);
    if (!data.locations.length) {
      setStatus("Kein Ort gefunden. Probiere eine andere Schreibweise.", true);
      return;
    }

    setStatus(data.offline
      ? "Externe Ortssuche nicht erreichbar. Nutze lokale Treffer."
      : "Waehle einen Treffer aus der Liste."
    );
    locationList.innerHTML = data.locations.map((location, index) => `
      <button class="location-option" type="button" data-index="${index}">
        ${formatLocation(location)}
      </button>
    `).join("");

    [...locationList.querySelectorAll(".location-option")].forEach((button) => {
      button.addEventListener("click", () => loadWeather(data.locations[button.dataset.index]));
    });

    await loadWeather(data.locations[0]);
  } finally {
    searchButton.disabled = false;
    searchButton.textContent = "Suchen";
  }
}

async function loadWeather(location) {
  const label = formatLocation(location);
  setStatus(`Lade Wetterdaten fuer ${label}...`);

  const params = new URLSearchParams({
    lat: location.latitude,
    lon: location.longitude,
    label
  });

  try {
    const data = await fetchJson(`/api/weather?${params.toString()}`);
    renderWeather(data);
    setStatus(data.offline
      ? `Offline-Demodaten fuer ${data.location}. Pruefe Internet/DNS der VM fuer Live-Wetter.`
      : `Aktualisiert fuer ${data.location}.`
    );
  } catch (error) {
    const data = demoWeather(location, error.message);
    renderWeather(data);
    setStatus(`Wetter-API nicht erreichbar: ${error.message}`, true);
  }
}

function renderWeather(data) {
  const current = data.current;
  document.querySelector("#locationName").textContent = data.location;
  document.querySelector("#currentTemp").textContent = number(current.temperature);
  document.querySelector("#condition").textContent = current.description;
  document.querySelector("#weatherMark").textContent = iconMap[current.icon] || "?";
  document.querySelector("#feelsLike").textContent = `${number(current.feelsLike)} deg C`;
  document.querySelector("#humidity").textContent = `${number(current.humidity)} %`;
  document.querySelector("#wind").textContent = `${number(current.windSpeed)} km/h`;
  document.querySelector("#precipitation").textContent = `${current.precipitation ?? "--"} mm`;
  document.querySelector("#timezone").textContent = `Zeitzone: ${data.timezone || "--"}`;

  document.querySelector("#hourlyStrip").innerHTML = data.hourly.map((hour) => `
    <article class="hour-card">
      <span>${formatHour(hour.time)}</span>
      <strong>${number(hour.temperature)} deg C</strong>
      <span>${number(hour.rainChance)} % Regen</span>
    </article>
  `).join("");

  document.querySelector("#dailyList").innerHTML = data.daily.map((day) => `
    <article class="day-row">
      <strong>${formatDay(day.time)}</strong>
      <span>${day.description}</span>
      <span>${number(day.low)} deg / ${number(day.high)} deg</span>
      <span>${number(day.rainChance)} % Regen</span>
      <span>${number(day.windSpeed)} km/h</span>
    </article>
  `).join("");
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = cityInput.value.trim();
  if (query.length < 2) {
    setStatus("Bitte gib mindestens zwei Zeichen ein.", true);
    return;
  }

  try {
    await searchLocations(query);
  } catch (error) {
    setStatus(error.message, true);
  }
});

setStatus("Gib einen Ort ein und klicke auf Suchen.");
