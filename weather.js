// weather.js (ESM Compatible)
import axios from "axios";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const API_KEY = "2f584ee563f56a67450565518b95b606";
const CACHE_PATH = path.join(__dirname, "weather_cache.json");
const CACHE_TTL = 1000 * 60 * 60; // 1 hour

const stadiumLocations = {
  "Yankees": "New York,US",
  "Orioles": "Baltimore,US",
  "Red Sox": "Boston,US",
  "Blue Jays": "Toronto,CA",
  "Rays": "St. Petersburg,US",
  "White Sox": "Chicago,US",
  "Guardians": "Cleveland,US",
  "Tigers": "Detroit,US",
  "Royals": "Kansas City,US",
  "Twins": "Minneapolis,US",
  "Astros": "Houston,US",
  "Mariners": "Seattle,US",
  "Rangers": "Arlington,US",
  "Angels": "Anaheim,US",
  "Athletics": "Oakland,US",
  "Mets": "New York,US",
  "Nationals": "Washington,US",
  "Braves": "Atlanta,US",
  "Phillies": "Philadelphia,US",
  "Marlins": "Miami,US",
  "Cubs": "Chicago,US",
  "Cardinals": "St. Louis,US",
  "Reds": "Cincinnati,US",
  "Pirates": "Pittsburgh,US",
  "Brewers": "Milwaukee,US",
  "Dodgers": "Los Angeles,US",
  "Giants": "San Francisco,US",
  "Padres": "San Diego,US",
  "Rockies": "Denver,US",
  "Diamondbacks": "Phoenix,US"
};

const parkDirections = {
  "Yankees": 22, "Orioles": 16, "Red Sox": 20, "Blue Jays": 25, "Rays": 10,
  "White Sox": 28, "Guardians": 23, "Tigers": 0, "Royals": 24, "Twins": 27,
  "Astros": 29, "Mariners": 25, "Rangers": 15, "Angels": 20, "Athletics": 45,
  "Mets": 22, "Nationals": 18, "Braves": 25, "Phillies": 20, "Marlins": 15,
  "Cubs": 10, "Cardinals": 30, "Reds": 19, "Pirates": 20, "Brewers": 18,
  "Dodgers": 30, "Giants": 21, "Padres": 27, "Rockies": 0, "Diamondbacks": 25
};

function windToMultiplier(speed, deg, parkDir, hand) {
  const offset = hand === "R" ? 0 : hand === "L" ? 180 : 0;
  const angle = Math.abs((deg - parkDir + offset + 360) % 360);
  const directionalEffect = Math.cos((angle * Math.PI) / 180);
  return 1 + (speed / 20) * directionalEffect * 0.1;
}

function tempHumidityToMultiplier(tempF, humidity) {
  const tempBoost = (tempF - 70) * 0.005;
  const humidityPenalty = (humidity - 50) * -0.002;
  return 1 + tempBoost + humidityPenalty;
}

function combine(windMult, tempMult) {
  return Math.max(0.85, Math.min(1.15, windMult * tempMult));
}

function getArrowEmoji(deg) {
  const arrows = ['⬆️','↗️','➡️','↘️','⬇️','↙️','⬅️','↖️'];
  return arrows[Math.round(((deg % 360) / 45)) % 8];
}

function getWindDirectionText(deg, parkDir) {
  const angle = (deg - parkDir + 360) % 360;
  if (angle < 45 || angle > 315) return "Blowing out to CF";
  if (angle < 135) return "Blowing out to RF";
  if (angle < 225) return "Blowing in from CF";
  return "Blowing out to LF";
}

function getFavorabilityText(batterHand, deg, parkDir) {
  const angle = (deg - parkDir + (batterHand === "L" ? 180 : 0) + 360) % 360;
  const cos = Math.cos((angle * Math.PI) / 180);
  if (cos > 0.25) return `Favorable for ${batterHand}HH`;
  if (cos < -0.25) return `Unfavorable for ${batterHand}HH`;
  return "Neutral";
}

function loadCache() {
  if (fs.existsSync(CACHE_PATH)) {
    const { timestamp, data } = JSON.parse(fs.readFileSync(CACHE_PATH, "utf8"));
    if (Date.now() - timestamp < CACHE_TTL) return data;
  }
  return null;
}

function saveCache(data) {
  fs.writeFileSync(CACHE_PATH, JSON.stringify({ timestamp: Date.now(), data }, null, 2));
}

async function fetchWeather(city) {
  const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(city)}&appid=${API_KEY}&units=imperial`;
  const res = await axios.get(url);
  return res.data;
}

export default async function getWeatherMultipliers(force = false) {
  if (!force) {
    const cached = loadCache();
    if (cached) {
      console.log("📦 Loaded weather data from cache");
      return cached;
    }
  }

  const data = {};

  for (const [team, city] of Object.entries(stadiumLocations)) {
    try {
      const weather = await fetchWeather(city);
      const windSpeed = weather.wind.speed;
      const windDeg = weather.wind.deg;
      const temp = weather.main.temp;
      const humidity = weather.main.humidity;
      const parkDir = parkDirections[team] || 0;

      const tempMult = tempHumidityToMultiplier(temp, humidity);
      const windR = windToMultiplier(windSpeed, windDeg, parkDir, "R");
      const windL = windToMultiplier(windSpeed, windDeg, parkDir, "L");
      const windS = (windR + windL) / 2;

      const finalR = combine(windR, tempMult);
      const finalL = combine(windL, tempMult);
      const finalS = combine(windS, tempMult);

      const arrow = getArrowEmoji(windDeg);

      data[team] = {
        R: finalR,
        L: finalL,
        S: finalS,
        raw: {
          windSpeed,
          windDeg,
          temp,
          humidity,
          windArrow: arrow,
          emoji: `${arrow} 🌡️${temp.toFixed(1)}°F 💧${humidity}% 💨${windSpeed.toFixed(1)}mph`,
          windDirectionText: getWindDirectionText(windDeg, parkDir),
          favorability: {
            R: getFavorabilityText("R", windDeg, parkDir),
            L: getFavorabilityText("L", windDeg, parkDir),
            S: "Neutral"
          }
        }
      };

      console.log(`🌤️ ${team}: Wind ${windSpeed}mph @ ${windDeg}°, Temp ${temp}°F, Humidity ${humidity}%`);
    } catch (err) {
      console.warn(`⚠️ Weather fetch failed for ${team}: ${err.message}`);
      data[team] = {
        R: 1,
        L: 1,
        S: 1,
        raw: {
          windArrow: "❓",
          emoji: "❓",
          windDirectionText: "Unknown",
          favorability: { R: "", L: "", S: "" }
        }
      };
    }
  }

  saveCache(data);
  return data;
}
