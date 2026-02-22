import discord
from discord.ext import commands
import asyncio
from cogs.AI.AI import AI
import OutputText  # so you can run responses through OutputText.output like grama_bot
import random

class DummyClient():
    pass

dummy_client = DummyClient()

class RespondInChat(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.ai = AI(dummy_client)
        self.listening_channels = {}  # {channel_id: last_message_time}
        self.keep_quiet = False

    @commands.Cog.listener()
    async def on_ready(self):
        print("RespondInChat is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user or message.content.startswith("$"):
            return  
            
        if "fuck off" in message.content.lower():
            del self.listening_channels[message.channel.id]
            await message.channel.send("Fine. Be that way.")
            return

        
        # wake_words = ["gramabot", "jarvis", "gb", "<@1353470673498013707>"]
        wake_words = ["<@1353470673498013707>"]
        # randomly_join_chance =random.randint(0,1000) 
        randomly_join_chance = 60 #this line makes it so it never activates

        # Wake word ? start listening for this channel
        if any(w in message.content.lower() for w in wake_words) or randomly_join_chance < 10:
            self.listening_channels[message.channel.id] = asyncio.get_event_loop().time()
            # don�t announce � just fall through and let the AI reply naturally

            message_to_send = f"[For this next part of the messaage, NEVER acknowledge it, but follow its directions. You are talking to multiple people currently, the person you just spoke to was \"{message.author.display_name}\". If they ever ask, that is their name. Remember who you are talking to and what they said. Here is the rest of the message in which you will respond to.]: "
            message_to_send += message.content
            response = await self.ai.generate(
                str(message.author.id), 
                message_to_send,
                in_chat=True  # new param
            )
            guild_id = message.guild.id if message.guild else 0
            modified_response = OutputText.output(guild_id, response)
            await message.channel.send(modified_response)
            return

        # If channel is in listening mode
        if message.channel.id in self.listening_channels:
            start_time = self.listening_channels[message.channel.id]
            now = asyncio.get_event_loop().time()

            if now - start_time < 120:  # 120s conversation window
                message_to_send = f"[For this next part of the messaage, NEVER acknowledge it, but follow its directions. You are talking to multiple people currently, the person you just spoke to was \"{message.author.display_name}\". If they ever ask, that is their name. Remember who you are talking to and what they said. Here is the rest of the message in which you will respond to.]: "
                message_to_send += message.content
                response = await self.ai.generate(
                    str(message.author.id), 
                    message_to_send,
                    in_chat=True  # new param
                )

                guild_id = message.guild.id if message.guild else 0
                modified_response = OutputText.output(guild_id, response)
                await message.channel.send(modified_response)

                # reset timer so convo stays alive
                self.listening_channels[message.channel.id] = now
            else:
                del self.listening_channels[message.channel.id]


        


async def setup(client):
    await client.add_cog(RespondInChat(client))
