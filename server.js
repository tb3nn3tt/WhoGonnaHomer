// server.js
import express from "express";
import cors from "cors";
import { exec } from "child_process";
import fs from "fs";
import getWeatherMultipliers from "./weather.js";

const app = express();
const port = 3001;

app.use(cors());

app.get("/api/lineups", async (req, res) => {
  console.log("🔍 /api/lineups hit. Running Python scraper...");

  exec("python rotoScraper.py", async (error, stdout, stderr) => {
    if (error) {
      console.error("❌ Python error:", error);
      return res.status(500).json({ error: "Python script failed" });
    }

    console.log("📄 Python script completed. Reading rotowire_lineups.json...");
    fs.readFile("rotowire_lineups.json", "utf8", async (err, data) => {
      if (err) {
        console.error("❌ Error reading JSON:", err);
        return res.status(500).json({ error: "Could not read scraped data" });
      }

      try {
        const lineups = JSON.parse(data);
        const weather = await getWeatherMultipliers();

        // Enrich each entry with weather multipliers and raw weather metadata
        const enriched = lineups.map((entry) => {
          const team = entry.park.replace(" Park", "");
          const hand = entry.hand;
          const wMult = weather[team]?.[hand] ?? 1.0;
          const raw = weather[team]?.raw ?? {};

          return {
            ...entry,
            weatherMultiplier: wMult,
            weather: raw, // frontend expects .emoji, .temp, .humidity, etc.
          };
        });

        console.log("✅ Returning enriched data");
        res.json(enriched);
      } catch (parseError) {
        console.error("❌ JSON Parse Error:", parseError);
        res.status(500).json({ error: "Malformed JSON" });
      }
    });
  });
});

app.listen(port, () => {
  console.log(`🚀 Server running at http://localhost:${port}`);
});
