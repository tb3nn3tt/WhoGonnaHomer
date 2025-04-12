import pandas as pd
import requests
from bs4 import BeautifulSoup
import json

# Load normalized batter names for name resolution
with open("frontend/src/data/normalized_batter_hr_data.json") as f:
    known_batters = set(json.load(f).keys())

def resolve_full_name(abbrev, team):
    if ' ' in abbrev and '.' in abbrev:
        initial, last = abbrev.split('. ')
        last = last.strip().lower()
        for name in known_batters:
            if name.endswith(last) and name.startswith(initial.lower()):
                return name
    return abbrev.lower()

url = "https://www.rotowire.com/baseball/daily-lineups.php"
soup = BeautifulSoup(requests.get(url).content, "html.parser")

data_pitching = []
data_batter = []
team_type = ''

for e in soup.select('.lineup__box ul li'):
    if team_type != e.parent.get('class')[-1]:
        order_count = 1
        team_type = e.parent.get('class')[-1]

    if e.get('class') and 'lineup__player-highlight' in e.get('class'):
        data_pitching.append({
            'date': e.find_previous('main').get('data-gamedate'),
            'game_time': e.find_previous('div', attrs={'class': 'lineup__time'}).get_text(strip=True),
            'pitcher_name': e.a.get_text(strip=True),
            'team': e.find_previous('div', attrs={'class': team_type}).next.strip(),
            'pitcher_hand': e.span.get_text(strip=True)
        })
    elif e.get('class') and 'lineup__player' in e.get('class'):
        data_batter.append({
            'date': e.find_previous('main').get('data-gamedate'),
            'game_time': e.find_previous('div', attrs={'class': 'lineup__time'}).get_text(strip=True),
            'batter_name': e.a.get_text(strip=True),
            'team': e.find_previous('div', attrs={'class': team_type}).next.strip(),
            'pos': e.div.get_text(strip=True),
            'batting_order': order_count,
            'batter_hand': e.span.get_text(strip=True)
        })
        order_count += 1

# Convert to DataFrames
df_pitching = pd.DataFrame(data_pitching)
df_batter = pd.DataFrame(data_batter)

# Merge batter with opposing pitcher info
merged = []
for i, row in df_batter.iterrows():
    opponent_pitchers = df_pitching[
        (df_pitching['game_time'] == row['game_time']) & (df_pitching['team'] != row['team'])
    ]
    if not opponent_pitchers.empty:
        pitcher = opponent_pitchers.iloc[0]
        full_name = resolve_full_name(row["batter_name"], row["team"])
        merged.append({
            "name": full_name,
            "hand": row["batter_hand"][0],
            "pitcher": pitcher["pitcher_name"],
            "pitcherHand": pitcher["pitcher_hand"][0],
            "park": f"{row['team']} Park",
            "gameTime": row["game_time"]
        })

# Save as JSON
with open("lineups.json", "w") as f:
    json.dump(merged, f, indent=2)

print(f"Saved {len(merged)} matchups to lineups.json")
