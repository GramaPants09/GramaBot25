import json
from pathlib import Path

FILE = Path("cogs/jsonfiles/ranked_aura.json")

if not FILE.exists():
    print("ranked_aura.json not found.")
    raise SystemExit(1)

with FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

count_users = 0
for guild_id, guild_data in data.items():
    users = guild_data.get("users", {})
    for uid, info in users.items():
        hist = info.get("ScoreHistory")
        if not hist:
            hist = [100]
        n = len(hist)
        info["ScoreHistory"] = [100] * n
        count_users += 1

with FILE.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print(f"Set aura to 100 for {count_users} users in {FILE}")
