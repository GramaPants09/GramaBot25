import discord
import json
from datetime import datetime
from discord.ext import commands

class Aura_Manager(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.filepath = "cogs/jsonfiles/ranked_aura.json"
        self.alt_list = [893607874641670175, 1346763297214431244, 1219808283272020110, 1145363441524166758]

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Aura_Manager.py is ready")

    def load_data(self):
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("ranked_aura.json not found.")
            return {}

    def save_data(self, data):
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=4)

    def is_same_day(self, guild_id, user_id, data):
        """Determine if last ScoreHistory entry is from today."""
        # For now, assume one score per day, and append new if len(history) < today's day count
        history_length = len(data[guild_id]["users"][user_id]["ScoreHistory"])
        current_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        return history_length >= current_weekday + 1

    async def add_aura(self, guild_id: int, user_id: int, amount: int):
        data = self.load_data()
        guild_id = str(guild_id)
        user_id = str(user_id)

        if guild_id not in data:
            data[guild_id] = {"users": {}}

        if user_id not in data[guild_id]["users"]:
            data[guild_id]["users"][user_id] = {
                "Username": "Unknown",
                "ScoreHistory": [0]
            }

        user_data = data[guild_id]["users"][user_id]

        if not user_data["ScoreHistory"]:
            user_data["ScoreHistory"].append(0)

        if self.is_same_day(guild_id, user_id, data):
            # Modify today's value
            user_data["ScoreHistory"][-1] += amount
        else:
            # New day, append based on yesterday's score
            last_score = user_data["ScoreHistory"][-1]
            user_data["ScoreHistory"].append(last_score + amount)

        if len(user_data["ScoreHistory"]) > 7:
            user_data["ScoreHistory"] = user_data["ScoreHistory"][-7:]

        self.save_data(data)

    async def sub_aura(self, guild_id: int, user_id: int, amount: int):
        await self.add_aura(guild_id, user_id, -amount)

    async def get_aura(self, guild_id: int, user_id: int) -> int:
        data = self.load_data()
        guild_id = str(guild_id)
        user_id = str(user_id)

        try:
            return data[guild_id]["users"][user_id]["ScoreHistory"][-1]
        except KeyError:
            return 0

    async def set_aura(self, guild_id: int, user_id: int, new_score: int):
        data = self.load_data()
        guild_id = str(guild_id)
        user_id = str(user_id)

        if guild_id not in data:
            data[guild_id] = {"users": {}}

        if user_id not in data[guild_id]["users"]:
            data[guild_id]["users"][user_id] = {
                "Username": "Unknown",
                "ScoreHistory": []
            }

        user_data = data[guild_id]["users"][user_id]

        if not user_data["ScoreHistory"]:
            user_data["ScoreHistory"].append(new_score)
        elif self.is_same_day(guild_id, user_id, data):
            user_data["ScoreHistory"][-1] = new_score
        else:
            user_data["ScoreHistory"].append(new_score)

        if len(user_data["ScoreHistory"]) > 7:
            user_data["ScoreHistory"] = user_data["ScoreHistory"][-7:]

        self.save_data(data)

async def setup(client):
    await client.add_cog(Aura_Manager(client))