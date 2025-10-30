import asyncio
import threading
from discord.ext import commands
from Local_Voice.main import voice_loop_entrypoint

# Controlls the voice listening activation. Main loop in Local_Voice folder, main file.

class VoiceListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_started = False
        self.listen_enabled = True  # toggle this via commands

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[VoiceListener] Cog loaded. Bot logged in as {self.bot.user}")
        

    def start_voice_loop(self):
        print("[VoiceListener] Starting voice loop thread...")
        self.voice_started = True
        voice_thread = threading.Thread(
            target=lambda: asyncio.run(voice_loop_entrypoint(self.bot)),
            daemon=True
        )
        voice_thread.start()

    @commands.command(name="togglelisten")
    @commands.is_owner()
    async def toggle_listen(self, ctx):
        """Toggles whether the bot listens in person."""
        self.listen_enabled = not self.listen_enabled
        await ctx.send(f"?? Listening mode is now: **{self.listen_enabled}**")

        # If we just enabled it and it hasn't started yet, start now
        if self.listen_enabled and not self.voice_started:
            self.start_voice_loop()

async def setup(bot):
    await bot.add_cog(VoiceListener(bot))
