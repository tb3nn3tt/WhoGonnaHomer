import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from unidecode import unidecode
import os
from datetime import datetime

# Safe print for file logging
def safe_print(*args, **kwargs):
    try:
        with open("scraper.log", "a", encoding="utf-8") as log_file:
            msg = " ".join(str(arg) for arg in args)
            log_file.write(msg + "\n")
    except Exception as e:
        print("[ERROR] Failed to write to log file:", e)

# Load normalized batter and pitcher names
batter_path = os.path.join("frontend", "src", "data", "normalized_batter_hr_data.json")
pitcher_path = os.path.join("frontend", "src", "data", "normalized_pitcher_hr_data.json")

with open(batter_path, encoding="utf-8") as f:
    batter_data = json.load(f)
with open(pitcher_path, encoding="utf-8") as f:
    pitcher_data = json.load(f)

known_batters = set(batter_data.keys())
known_pitchers = set(pitcher_data.keys())

normalized_batter_keys = {unidecode(k.lower()): k for k in known_batters}
normalized_pitcher_keys = {unidecode(k.lower()): k for k in known_pitchers}

safe_print(f"[OK] Loaded {len(known_batters)} known batters and {len(known_pitchers)} known pitchers.")

# Normalize helper
def title_case_name(name):
    return " ".join(word.capitalize() for word in name.split())

def resolve_full_name(abbrev, team):
    norm_abbrev = unidecode(abbrev.lower())
    if '.' in abbrev and ' ' in abbrev:
        initial, last = abbrev.split('. ')
        norm_last = unidecode(last.strip().lower())
        for norm_key in normalized_batter_keys:
            if norm_key.endswith(norm_last) and norm_key.startswith(initial.lower()):
                resolved = normalized_batter_keys[norm_key]
                safe_print(f"[RESOLVE] {abbrev} -> {resolved} ({team})")
                return resolved
    if norm_abbrev in normalized_batter_keys:
        resolved = normalized_batter_keys[norm_abbrev]
        safe_print(f"[RESOLVE] Exact match: {abbrev} -> {resolved} ({team})")
        return resolved
    safe_print(f"[WARN] Could not resolve full name for: {abbrev} ({team})")
    return abbrev.lower()

def resolve_pitcher_name(name):
    norm_name = unidecode(name).lower()
    if '.' in name and ' ' in name:
        initial, last = name.split('. ')
        norm_last = unidecode(last.strip().lower())
        for norm_key in normalized_pitcher_keys:
            if norm_key.endswith(norm_last) and norm_key.startswith(initial.lower()):
                resolved = normalized_pitcher_keys[norm_key]
                safe_print(f"[RESOLVE] {name} -> {resolved} (Pitcher)")
                return resolved
    if norm_name in normalized_pitcher_keys:
        resolved = normalized_pitcher_keys[norm_name]
        safe_print(f"[RESOLVE] Exact match: {name} -> {resolved} (Pitcher)")
        return resolved
    safe_print(f"[FALLBACK] No stats found for pitcher '{name}' — using fallback 100% multiplier")
    return name

# Scrape from Rotowire
url = "https://www.rotowire.com/baseball/daily-lineups.php"
safe_print(f"[FETCH] Scraping {url}...")
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
safe_print(f"[OK] Status: {response.status_code}, HTML parsed.")

data_pitching = []
data_batter = []
team_type = ''
order_count = 1

# Parse lineups
for i, box in enumerate(soup.select('.lineup__box')):
    safe_print(f"[BOX] Parsing lineup box #{i+1}...")
    for e in box.select("ul li"):
        if team_type != e.parent.get('class')[-1]:
            order_count = 1
            team_type = e.parent.get('class')[-1]

        gameblock = e.find_parent("div", class_="lineup__box")
        if not gameblock:
            safe_print("[WARN] Skipping: missing .lineup__box")
            continue

        game_time = e.find_previous('div', class_='lineup__time').get_text(strip=True)
        team = e.find_previous('div', class_=team_type).next.strip()

        if 'lineup__player-highlight' in e.get('class', []):
            pitcher = {
                'game_time': game_time,
                'pitcher_name': e.a.get_text(strip=True),
                'team': team,
                'pitcher_hand': e.span.get_text(strip=True)
            }
            data_pitching.append(pitcher)
            safe_print(f"[PITCHER] {pitcher}")
        elif 'lineup__player' in e.get('class', []):
            batter = {
                'game_time': game_time,
                'batter_name': e.a.get_text(strip=True),
                'team': team,
                'pos': e.div.get_text(strip=True),
                'batting_order': order_count,
                'batter_hand': e.span.get_text(strip=True)
            }
            data_batter.append(batter)
            safe_print(f"[BATTER] {batter}")
            order_count += 1

safe_print(f"[INFO] Parsed {len(data_batter)} batters, {len(data_pitching)} pitchers.")

df_pitching = pd.DataFrame(data_pitching)
df_batter = pd.DataFrame(data_batter)

# Track assigned pitchers per (opposing_team, game_time)
assigned_pitchers = {}

merged = []
for i, row in df_batter.iterrows():
    team = row['team']
    game_time = row['game_time']
    safe_print(f"[MATCHUP] Processing {row['batter_name']} ({team} @ {game_time})")

    # Find opposing pitchers (should be 1 team per matchup)
    opponent_pitchers = df_pitching[
        (df_pitching['game_time'] == game_time) & (df_pitching['team'] != team)
    ]

    if len(opponent_pitchers['team'].unique()) == 1:
        opponent_team = opponent_pitchers['team'].iloc[0]
        pitcher_key = (opponent_team, game_time)

        if pitcher_key in assigned_pitchers:
            assigned_pitcher = assigned_pitchers[pitcher_key]
        else:
            candidates = df_pitching[
                (df_pitching['game_time'] == game_time) & (df_pitching['team'] == opponent_team)
            ]
            if not candidates.empty:
                assigned_pitcher = candidates.iloc[0]
                assigned_pitchers[pitcher_key] = assigned_pitcher
                safe_print(f"[ASSIGN] Assigned {assigned_pitcher['pitcher_name']} to {opponent_team} @ {game_time}")
            else:
                safe_print(f"[WARN] No candidates found for {opponent_team} @ {game_time}")
                continue
    else:
        safe_print(f"[ERROR] Ambiguous or missing opponent for {team} @ {game_time}")
        continue

    full_name = resolve_full_name(row['batter_name'], team)
    resolved_pitcher_name = resolve_pitcher_name(assigned_pitcher['pitcher_name'])

    if full_name not in known_batters:
        safe_print(f"[FALLBACK] No stats for batter '{full_name}'")
    else:
        safe_print(f"[MATCH] Found stats for batter '{full_name}'")

    matchup = {
        "name": title_case_name(full_name),
        "hand": row["batter_hand"][0],
        "pitcher": resolved_pitcher_name,
        "pitcherHand": assigned_pitcher["pitcher_hand"][0],
        "park": f"{team} Park",
        "gameTime": game_time
    }
    merged.append(matchup)
    safe_print(f"[OK] Matchup added: {matchup}")

# Save results
with open("rotowire_lineups.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

safe_print(f"[DONE] Saved {len(merged)} matchups to rotowire_lineups.json")
