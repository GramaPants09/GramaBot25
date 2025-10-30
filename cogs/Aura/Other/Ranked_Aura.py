import discord
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import random
import OutputText
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import hashlib
from PIL import Image
import requests
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

class Ranked_Aura(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.daily_scoreboard_time = (0, 0)
        self.normal_change = True

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        if not self.timed_scoreboard.is_running():
            self.timed_scoreboard.start()
        print("Ranked_Aura.py is ready")

    @commands.command(name="forcedaily")
    async def force_daily_update(self, ctx):
        # Only bot owner can run this
        if ctx.author.id != 448854769306435584:
            await ctx.send("You are not authorized to use this command.")
            return
        await ctx.send("Forcing daily aura update...")
        await self.timed_scoreboard.__call__()

    async def decide_aura(self, guild_id, user_id):
        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            print("Aura_Manager cog not loaded.")
            return 0

        member_aura = await aura_manager.get_aura(guild_id, user_id)
        digits = len(str(abs(member_aura)))
        disaster_chance = min(0.01 * (digits**2), 0.9)

        if digits >= 9:
            self.normal_change = False
            return int(-1 * member_aura * random.uniform(0.01, 0.1))
        elif random.random() < disaster_chance:
            self.normal_change = False
            return int(-member_aura * random.uniform(0.25, 0.8))
        elif random.randint(1, 100) == 56:
            self.normal_change = False
            return member_aura * random.randint(2, 10)
        else:
            self.normal_change = True
            return random.randint(-9, 9) * 10

    @tasks.loop(hours=24)
    async def timed_scoreboard(self):
        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            print("Aura_Manager cog not loaded.")
            return

        # Load JSON files
        try:
            with open("cogs/jsonfiles/ranked_aura.json", "r") as f:
                ranked_aura = json.load(f)
        except FileNotFoundError:
            ranked_aura = {}

        try:
            with open("cogs/jsonfiles/aura_channel.json", "r") as f:
                channels = json.load(f)
        except FileNotFoundError:
            print("aura_channel.json not found.")
            return

        # Loop over all guilds
        for guild_id_str, channel_id in channels.items():
            guild_id = str(guild_id_str)
            channel_id = int(channel_id)
            channel = self.client.get_channel(channel_id)
            if not channel:
                print(f"Channel {channel_id} not found.")
                continue

            server_data = ranked_aura.setdefault(guild_id, {}).setdefault("users", {})
            change_messages = []

            # Lists for random messages
            disaster_list = [
                "got hit by a car,", "got struck by lightning,", "got thrown away by a tornado,",
                "got shrunk down and stepped on by an ant,", "tried to cheese plinko,",
                "thought they were the main character,", "got swallowed alive by an earthquake,",
                "jumped out of a plane with no parachute,", "believes in the 13 month calendar,"
            ]
            luck_list = [
                "is simply better,", "knows how to gamble correctly,", "paid off GramaBot,",
                "has ginged all the gangs,", "won the lottery,", "truly is the main character,",
                "put a vertical line on the minus sign,", "knows how many months there should be (hint: not 13),"
            ]

            # Iterate over all members
            for member in channel.guild.members:
                if member.bot or member.id in getattr(aura_manager, "alt_list", []):
                    continue

                user_id = str(member.id)
                user_data = server_data.setdefault(user_id, {"Username": member.name, "ScoreHistory": [0]})

                # Maintain a 7-day history
                history = user_data.get("ScoreHistory", [])
                if len(history) < 7:
                    history = [history[0]] * (7 - len(history)) + history
                history = history[1:] + [history[-1]]
                user_data["ScoreHistory"] = history

                # Calculate daily change
                daily_change = await self.decide_aura(channel.guild.id, member.id)
                await aura_manager.add_aura(channel.guild.id, member.id, daily_change)

                updated_aura = await aura_manager.get_aura(channel.guild.id, member.id)
                user_data["ScoreHistory"][-1] = updated_aura

                # Prepare message
                if daily_change > 0 and self.normal_change:
                    change_messages.append(f"{member.name}, good shit, +{daily_change} aura.")
                elif daily_change < 0 and self.normal_change:
                    change_messages.append(f"{member.name}, not cool, -{abs(daily_change)} aura.")
                elif daily_change > 0 and not self.normal_change:
                    change_messages.append(f"{member.name} {random.choice(luck_list)} +{daily_change} aura.")
                elif daily_change < 0 and not self.normal_change:
                    change_messages.append(f"{member.name} {random.choice(disaster_list)} -{abs(daily_change)} aura.")
                else:
                    change_messages.append(f"{member.name} maintained their aura score.")

            # Send updates
            if change_messages:
                change_report = "\n".join(change_messages)
                await channel.send(OutputText.output(int(guild_id), f"**Daily Aura Updates:**\n{change_report}"))

            # Send scoreboard and graph
            embed = self.make_scoreboard(int(guild_id))
            if embed:
                await channel.send(embed=embed)
            await self.post_daily_graph(channel)

        # Save JSON at the end
        with open("cogs/jsonfiles/ranked_aura.json", "w") as f:
            json.dump(ranked_aura, f, indent=4)

    @timed_scoreboard.before_loop
    async def before_timed_scoreboard(self):
        await self.client.wait_until_ready()
        now = datetime.now()
        hour, minute = self.daily_scoreboard_time
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        print(f"? Waiting {int(wait_seconds)} seconds until next aura drop at {hour:02d}:{minute:02d}")
        await asyncio.sleep(wait_seconds)

    def make_scoreboard(self, guild_id):
        try:
            with open("cogs/jsonfiles/ranked_aura.json", "r") as f:
                ranked_aura = json.load(f)
        except FileNotFoundError:
            print("Error: ranked_aura.json file not found.")
            return None

        guild = self.client.get_guild(guild_id)
        if not guild:
            print("Error: Could not fetch guild.")
            return None

        server_data = ranked_aura.get(str(guild_id), {}).get("users", {})
        sorted_users = sorted(
            [(uid, data) for uid, data in server_data.items() if guild.get_member(int(uid)) and not guild.get_member(int(uid)).bot],
            key=lambda x: x[1]["ScoreHistory"][-1] if x[1]["ScoreHistory"] else 0,
            reverse=True
        )

        embed = discord.Embed(title="Ranked Aura Board", description="Top users by aura", color=discord.Color.gold())
        embed.set_thumbnail(url="https://c.tenor.com/JStWg_VUdBEAAAAd/tenor.gif")

        if sorted_users:
            for _, user_data in sorted_users:
                latest_score = user_data["ScoreHistory"][-1] if user_data["ScoreHistory"] else 0
                embed.add_field(name=user_data['Username'], value=f"Aura: {latest_score}", inline=False)
        else:
            embed.add_field(name="No scores available", value="No users have a score yet.", inline=False)

        return embed

    async def post_daily_graph(self, channel):
        guild_id = str(channel.guild.id)
        try:
            with open("cogs/jsonfiles/ranked_aura.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            await channel.send("Aura data not found.")
            return

        users_data = data.get(guild_id, {}).get("users", {})
        if not users_data:
            await channel.send("No aura data available to graph.")
            return

        fig, ax = plt.subplots(figsize=(14, 8))
        used_labels = set()

        def user_color(uid):
            seed = int(hashlib.md5(uid.encode()).hexdigest(), 16)
            random.seed(seed)
            return random.choice(list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values()))

        today = datetime.now().weekday()
        all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        rotated_days = all_days[-6 + today:] + all_days[: -6 + today]

        end_points = {}
        for user_id, info in users_data.items():
            history = info.get("ScoreHistory", [])
            label = info["Username"]
            if label in used_labels:
                label = f"{label}_{user_id[:4]}"
            used_labels.add(label)

            if history:
                if len(history) < 7:
                    history = [history[0]] * (7 - len(history)) + history
                x = list(range(7))
                color = user_color(user_id)
                ax.plot(x, history[-7:], label=label, linewidth=2.5, marker='o', markersize=7, color=color, alpha=0.9)
                end_points[label] = (x[-1], history[-1], user_id)

        ax.set_title("Daily Aura Graph", fontsize=20, fontweight='bold')
        ax.set_xlabel("Day of Week", fontsize=14)
        ax.set_ylabel("Aura Score", fontsize=14)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.set_xticks(range(7))
        ax.set_xticklabels(rotated_days, rotation=45, fontsize=12)
        ax.tick_params(axis='y', labelsize=12)

        for label, (x_end, y_end, user_id) in end_points.items():
            try:
                user = await self.client.fetch_user(int(user_id))
                avatar_url = getattr(user.avatar, "url", None)
                if avatar_url:
                    response = requests.get(avatar_url)
                    img = Image.open(io.BytesIO(response.content)).resize((35, 35))
                    imagebox = OffsetImage(img, zoom=1.2)
                    ab = AnnotationBbox(imagebox, (x_end, y_end), frameon=False)
                    ax.add_artist(ab)
            except Exception as e:
                print(f"Error fetching avatar for {label}: {e}")

        fig.text(0.5, 0.92, "Aura Market", fontsize=36, alpha=0.07, ha='center', va='center', rotation=30)
        plt.tight_layout(rect=[0, 0, 0.85, 1])

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        await channel.send(file=discord.File(fp=buf, filename="daily_aura_market.png"))

    @commands.command(name="graph")
    async def manual_aura_graph(self, ctx):
        await self.post_daily_graph(ctx.channel)

    @commands.command(name="scoreboard")
    async def manual_scoreboard(self, ctx):
        embed = self.make_scoreboard(ctx.guild.id)
        if embed:
            await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(Ranked_Aura(client))