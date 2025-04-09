import requests
import json
from datetime import datetime

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def fetch_schedule(date):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
    res = requests.get(url)
    data = res.json()
    return data.get("dates", [])[0].get("games", []) if data.get("dates") else []

def fetch_game_details(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    res = requests.get(url)
    return res.json() if res.status_code == 200 else {"error": f"Failed to fetch game {game_pk}"}

def main():
    date = get_today_date()
    games = fetch_schedule(date)
    game_pks = [game["gamePk"] for game in games]

    all_data = {}
    for pk in game_pks:
        print(f"Fetching gamePk: {pk}")
        all_data[pk] = fetch_game_details(pk)

    with open("mlb_full_lineup_data.json", "w") as f:
        json.dump(all_data, f, indent=2)

    print("✅ Saved to mlb_full_lineup_data.json")

if __name__ == "__main__":
    main()
