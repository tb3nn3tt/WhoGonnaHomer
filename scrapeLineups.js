import fetch from 'node-fetch';
import fs from 'fs/promises';

const getTodayDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const fetchSchedule = async (date) => {
  const url = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${date}`;
  const response = await fetch(url);
  const data = await response.json();
  return data.dates[0]?.games || [];
};

const fetchGameDetails = async (gamePk) => {
  const url = `https://statsapi.mlb.com/api/v1.1/game/${gamePk}/feed/live`;
  const response = await fetch(url);
  const data = await response.json();
  return data;
};

const fetchPlayerHandedness = async (playerId) => {
  const url = `https://statsapi.mlb.com/api/v1/people/${playerId}`;
  const response = await fetch(url);
  const data = await response.json();
  return data.people?.[0]?.pitchHand?.code || '?';
};

const displayGame = (game) => {
  console.log(`\n=============================================`);
  console.log(`${game.awayTeam} @ ${game.homeTeam}`);
  console.log(`Park: ${game.park}`);
  console.log(`Away SP: ${game.awayPitcher.name} (${game.awayPitcher.hand})`);
  console.log(`Home SP: ${game.homePitcher.name} (${game.homePitcher.hand})`);

  console.log(`\n--- ${game.awayTeam} Batting Order ---`);
  game.awayLineup.forEach((player, i) => {
    console.log(`${i + 1}. ${player.name} (${player.hand})`);
  });

  console.log(`\n--- ${game.homeTeam} Batting Order ---`);
  game.homeLineup.forEach((player, i) => {
    console.log(`${i + 1}. ${player.name} (${player.hand})`);
  });
};

const run = async () => {
  console.log("🔧 TEST MODE: Forcing fallback to test data...\n");
  const fallbackData = JSON.parse(await fs.readFile("testLineups.json", "utf-8"));
  fallbackData.forEach(displayGame);
};

run();
