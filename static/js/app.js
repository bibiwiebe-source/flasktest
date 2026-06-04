const searchForm = document.querySelector("#searchForm");
const cityInput = document.querySelector("#cityInput");
const locationList = document.querySelector("#locationList");
const statusBar = document.querySelector("#statusBar");

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

async function fetchJson(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "Die Anfrage ist fehlgeschlagen.");
  }
  return body;
}

async function searchLocations(query) {
  setStatus("Suche passende Orte...");
  locationList.innerHTML = "";
  const data = await fetchJson(`/api/locations?q=${encodeURIComponent(query)}`);
  if (!data.locations.length) {
    setStatus("Kein Ort gefunden. Probiere eine andere Schreibweise.", true);
    return;
  }
  setStatus("Waehle einen Treffer aus der Liste.");
  locationList.innerHTML = data.locations.map((location, index) => `
    <button class="location-option" type="button" data-index="${index}">
      ${formatLocation(location)}
    </button>
  `).join("");
  [...locationList.querySelectorAll(".location-option")].forEach((button) => {
    button.addEventListener("click", () => loadWeather(data.locations[button.dataset.index]));
  });
  loadWeather(data.locations[0]);
}

async function loadWeather(location) {
  const label = formatLocation(location);
  setStatus(`Lade Wetterdaten fuer ${label}...`);
  const params = new URLSearchParams({ lat: location.latitude, lon: location.longitude, label });
  const data = await fetchJson(`/api/weather?${params.toString()}`);
  renderWeather(data);
  setStatus(`Aktualisiert fuer ${data.location}.`);
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
    <article class="hour-card"><span>${formatHour(hour.time)}</span><strong>${number(hour.temperature)} deg C</strong><span>${number(hour.rainChance)} % Regen</span></article>
  `).join("");
  document.querySelector("#dailyList").innerHTML = data.daily.map((day) => `
    <article class="day-row"><strong>${formatDay(day.time)}</strong><span>${day.description}</span><span>${number(day.low)} deg / ${number(day.high)} deg</span><span>${number(day.rainChance)} % Regen</span><span>${number(day.windSpeed)} km/h</span></article>
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

searchForm.dispatchEvent(new Event("submit"));
