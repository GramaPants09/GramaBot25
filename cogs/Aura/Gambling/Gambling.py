import random
import asyncio
import discord
from discord.ext import commands
import OutputText
from PIL import Image, ImageDraw, ImageFont
import io
import math



class Gambling(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Gambling.py is ready")


    async def able_to_gamble(self, guildID, userID, min_bet=5) -> bool:
        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            return False

        current_aura = await aura_manager.get_aura(guildID, userID)
        return current_aura >= min_bet


    @commands.command(name="balance")
    async def aura_balance(self, ctx, user: discord.Member = None):
        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            await ctx.send("Aura Manager not loaded.")
            return

        if user is None:
            user = ctx.author  # If no user mentioned, default to command sender

        balance = await aura_manager.get_aura(ctx.guild.id, user.id)
        await ctx.send(OutputText.output(ctx.guild.id,f"`{user.display_name} has {balance} aura.`"))


    @commands.command(name="slot")
    async def slot(self, ctx, *, aura_bet: str):
        emojis = [":cherries:", ":lemon:", ":bell:", ":star:", ":seven:"]
        reel = ["?", "?", "?"]
        spacing = "     "
        spin_speed = 0.4
        guild_ID = ctx.guild.id
        user_ID = ctx.author.id
        negative_slot = False

        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            await ctx.send("Aura Manager not loaded.")
            return

        try:
            bet = int(aura_bet)
        except Exception:
            await ctx.send(OutputText.output(ctx.guild.id,"Your bet must be numerical."))
            return

        if bet < 5:
            await ctx.send(OutputText.output(ctx.guild.id,"You must bet at least 5 aura to play."))
            return
        
        

        current_aura = await aura_manager.get_aura(guild_ID, user_ID)

        if current_aura < -1000:
            await ctx.send(OutputText.output(ctx.guild.id, "Sorry, but you are in too deep. Try taking out a loan. [NOT AVAILABLE]"))
            return
        
        if current_aura <= 0 and bet < abs(current_aura):
            await ctx.send(OutputText.output(ctx.guild.id,"Initiating Negative Gambling."))
            negative_slot = True

            

        
        if current_aura < bet and not negative_slot:
            await ctx.send(OutputText.output(ctx.guild.id,f"Why are you trying to cheat the system? You don't have {bet} aura, you only have {current_aura} aura."))
            return

        await aura_manager.sub_aura(guild_ID, user_ID, bet)

        # Slot machine spin animations below (your existing code)


        msg = await ctx.send(f"**:slot_machine:{spacing}{' | '.join(reel)}**")

        # Frame 1: All spinning
        for i in range(2):
            reel = [random.choice(emojis) for _ in range(3)]
            await msg.edit(content=f"**:slot_machine:{spacing}{' | '.join(reel)}**")
            await asyncio.sleep(spin_speed)

        # Frame 2: Lock left, spin mid/right
        left = random.choice(emojis)
        for _ in range(2):
            mid = random.choice(emojis)
            right = random.choice(emojis)
            await msg.edit(content=f"**:slot_machine:{spacing}{left} | {mid} | {right}**")
            await asyncio.sleep(spin_speed)

        # Frame 3: Lock middle, suspense pause
        mid = random.choice(emojis)
        await msg.edit(content=f"**:slot_machine:{spacing}{left} | {mid} | ?**")
        await asyncio.sleep(1.2)

        # Frame 4: Lock final
        right = random.choice(emojis)
        result_line = f"{left} | {mid} | {right}"
        await asyncio.sleep(0.4)

        # Determine winnings
        final = [left, mid, right]
        if final[0] == final[1] == final[2]:
            if negative_slot:
                amount = bet*3 + int(bet/5)
            else:
                amount = bet*5
            result = f":tada: **JACKPOT!  You won {amount} Aura!**"
            await aura_manager.add_aura(guild_ID, user_ID, bet*5)
        elif len(set(final)) == 2:
            if negative_slot:
                amount = bet + int(bet/4)
            else:
                amount = bet*2
            result = f":tada: **You matched two!  You won {amount} Aura!**"
            await aura_manager.add_aura(guild_ID, user_ID, bet*2)
        else:
            if negative_slot:
                loss_multiplier = len(str(current_aura)) - 1
                lost_aura = bet*loss_multiplier
                await aura_manager.sub_aura(guild_ID, user_ID, lost_aura)
                result = f":cry: **You lost!**\n **As a risk of negative gambling you lost an additional {lost_aura} aura!**"
            else:   
                result = ":cry: **You lost!**"
            
        current_aura = await aura_manager.get_aura(guild_ID, user_ID)

        await msg.edit(content=f"**:slot_machine:{spacing}{result_line}**\n{result}       You now have {current_aura} aura.")


    


    @commands.command(name="roulette")
    async def roulette(self, ctx, bet_color: str, bet_amount: str):
        import io
        import math
        import asyncio
        import random
        from PIL import Image, ImageDraw, ImageFont

        image_size = 500
        center = image_size // 2
        radius = 200
        sectors = 38
        frames_count = 70
        font_size = 16

        spins = 8
        slow_down_extra_spins = 3
        base_rotation = 360 * (spins + slow_down_extra_spins)

        # REAL American roulette layout
        real_order = ["0", "28", "9", "26", "30", "11", "7", "20", "32", "17", "5",
                      "22", "34", "15", "3", "24", "36", "13", "1", "00", "27",
                      "10", "25", "29", "12", "8", "19", "31", "18", "6", "21",
                      "33", "16", "4", "23", "35", "14", "2"]

        red_numbers = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        black_numbers = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

        sector_labels = real_order
        sector_colors = []
        for label in real_order:
            if label == "0" or label == "00":
                sector_colors.append("green")
            else:
                num = int(label)
                if num in red_numbers:
                    sector_colors.append("red")
                elif num in black_numbers:
                    sector_colors.append("black")
                else:
                    sector_colors.append("green")

        guild_ID = ctx.guild.id
        user_ID = ctx.author.id

        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            await ctx.send("Aura Manager not loaded.")
            return

        try:
            bet = int(bet_amount)
        except Exception:
            await ctx.send(OutputText.output(ctx.guild.id, "Your bet amount must be a number."))
            return

        if bet < 5:
            await ctx.send(OutputText.output(ctx.guild.id, "You must bet at least 5 aura to play."))
            return

        bet_color = bet_color.lower()
        if bet_color not in ["red", "black", "green"]:
            await ctx.send(OutputText.output(ctx.guild.id, "You must bet on 'red', 'black', or 'green'."))
            return

        current_aura = await aura_manager.get_aura(guild_ID, user_ID)
        if current_aura < bet:
            await ctx.send(OutputText.output(ctx.guild.id, f"You don't have {bet} aura, you only have {current_aura} aura."))
            return

        await aura_manager.sub_aura(guild_ID, user_ID, bet)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # --- Create base wheel ---
        base_wheel = Image.new("RGBA", (image_size, image_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(base_wheel)

        for i in range(sectors):
            start_angle = i * (360 / sectors)
            end_angle = start_angle + (360 / sectors)
            draw.pieslice(
                [center - radius, center - radius, center + radius, center + radius],
                start=start_angle,
                end=end_angle,
                fill=sector_colors[i],
                outline="black"
            )

        for i in range(sectors):
            label_angle = math.radians((i + 0.5) * (360 / sectors))
            x = center + int((radius - 60) * math.cos(label_angle))
            y = center + int((radius - 60) * math.sin(label_angle))
            draw.text((x - 10, y - 10), sector_labels[i], fill="white", font=font)

        frames = []

        # ?? ADD RANDOM FINAL OFFSET
        random_offset = random.uniform(0, 360)

        # Final total rotation
        final_total_rotation = base_rotation + random_offset

        easing_angles = []
        for i in range(frames_count):
            t = i / (frames_count - 1)
            eased = 1 - (1 - t)**3
            angle = eased * final_total_rotation
            easing_angles.append(angle)

        final_angle = easing_angles[-1]

        # Add bounce
        bounce_offsets = [3, -2, 1, -1, 0]
        for offset in bounce_offsets:
            easing_angles.append(final_angle + offset)

        for rotation in easing_angles:
            frame = Image.new("RGBA", (image_size, image_size), (255, 255, 255, 255))
            rotated = base_wheel.rotate(rotation, resample=Image.BICUBIC, center=(center, center))
            frame.paste(rotated, (0, 0), rotated)

            draw_frame = ImageDraw.Draw(frame)

            peg_size = 20
            peg_color = "gray"
            peg_coords = [(center - peg_size // 2, center - radius - 10),
                          (center + peg_size // 2, center - radius - 10),
                          (center, center - radius + 20)]
            draw_frame.polygon(peg_coords, fill=peg_color)

            frames.append(frame.convert("RGB"))

        # Save gif
        gif_buffer = io.BytesIO()
        frames[0].save(gif_buffer, format="GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
        gif_buffer.seek(0)

        # Save final frame
        final_img_buffer = io.BytesIO()
        frames[-1].save(final_img_buffer, format="PNG")
        final_img_buffer.seek(0)

        # Send GIF
        gif_message = await ctx.send(file=discord.File(gif_buffer, filename="roulette_spin.gif"))
        await asyncio.sleep(7)
        await gif_message.delete()

        # Send final freeze frame
        await ctx.send(file=discord.File(final_img_buffer, filename="roulette_result.png"))

        # --- NOW SCORE PROPERLY ---

        # Correct final sector based on PEG at top
        peg_angle = (final_angle + 270) % 360
        sector_width = 360 / sectors
        landed_sector = int((peg_angle) / sector_width) % sectors

        winning_color = sector_colors[landed_sector]
        winning_label = sector_labels[landed_sector]

        winnings = 0
        result_text = ""
        if bet_color == winning_color:
            if winning_color == "green":
                winnings = bet * 10
                result_text = f":tada: **You guessed Green (0 or 00) correctly! You won {winnings} aura!**"
            else:
                winnings = bet * 2
                result_text = f":tada: **You guessed {bet_color.capitalize()} correctly! You won {winnings} aura!**"
            await aura_manager.add_aura(guild_ID, user_ID, winnings)
        else:
            result_text = f":cry: **You guessed {bet_color.capitalize()}, but it landed on {winning_color.capitalize()} ({winning_label}). You lost!**"

        current_aura = await aura_manager.get_aura(guild_ID, user_ID)

        await ctx.send(f":dart: Final: **{winning_label} ({winning_color.capitalize()})**\n{result_text}\nYou now have {current_aura} aura.")

    @commands.command(name="plinko")
    async def plinko(self, ctx, balls: int, bet_per_ball: int):
        import io
        import random
        from PIL import Image, ImageDraw, ImageFont
        import asyncio

        width = 1000
        height = 1200
        rows = 12
        slots = 17
        ball_radius = 10
        spacing_x = width // slots
        spacing_y = height // (rows + 5)
        font_size = 22

        gravity = 0.5
        bounce_strength = 1.2
        frame_delay = 33
        max_frames = 600

        prizes = [10, 5, 2, 1, 0.5, 0.25, 0.1, 0.05, 0, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10]

        guild_ID = ctx.guild.id
        user_ID = ctx.author.id

        aura_manager = self.client.get_cog("Aura_Manager")
        if aura_manager is None:
            await ctx.send("Aura Manager not loaded.")
            return

        if balls <= 0 or bet_per_ball < 5:
            await ctx.send("You must drop at least 1 ball and bet at least 5 aura per ball.")
            return

        if balls > 1000:
            await ctx.send("That's too many balls. Please limit to 1000 or less.")
            return

        total_bet = balls * bet_per_ball
        current_aura = await aura_manager.get_aura(guild_ID, user_ID)
        if current_aura < total_bet:
            await ctx.send(f"You don't have enough aura. You have {current_aura}, but need {total_bet}.")
            return

        await aura_manager.sub_aura(guild_ID, user_ID, total_bet)

        # Run heavy work in background thread
        gif_buffer, final_img_buffer, frame_counter, ball_objects = await asyncio.to_thread(
            self.create_plinko_gif_and_images,
            balls, bet_per_ball, width, height, rows, slots, ball_radius,
            spacing_x, spacing_y, font_size, gravity, bounce_strength,
            frame_delay, max_frames, prizes
        )

        # Send GIF
        gif_message = await ctx.send(file=discord.File(gif_buffer, filename="plinko.gif"))
        await asyncio.sleep((frame_counter * frame_delay) / 1000 + 1)
        await gif_message.delete()
        await ctx.send(file=discord.File(final_img_buffer, filename="plinko_result.png"))

        # Scoring
        total_winnings = 0
        for ball in ball_objects:
            slot_index = min(max(int(ball["x"] // spacing_x), 0), slots - 1)
            winnings = bet_per_ball * prizes[slot_index]
            total_winnings += winnings

        total_winnings *= 0.95  # house edge
        max_payout = balls * bet_per_ball * 5
        total_winnings = min(total_winnings, max_payout)
        total_winnings = int(total_winnings)

        await aura_manager.add_aura(guild_ID, user_ID, total_winnings)
        current_aura = await aura_manager.get_aura(guild_ID, user_ID)

        await ctx.send(f":wolf: You dropped {balls} balls at {bet_per_ball} aura each!\n"
                       f"Total winnings: {total_winnings} aura!\n"
                       f"You now have {current_aura} aura.")


    # Helper function runs in background thread
    def create_plinko_gif_and_images(self, balls, bet_per_ball, width, height, rows, slots,
                                     ball_radius, spacing_x, spacing_y, font_size,
                                     gravity, bounce_strength, frame_delay, max_frames, prizes):
        import io
        import random
        from PIL import Image, ImageDraw, ImageFont

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        pegs = []
        for r in range(1, rows + 1):
            peg_count = max(1, slots - abs(r - rows // 2))
            spacing = width / peg_count
            for c in range(peg_count):
                peg_x = c * spacing + spacing / 2
                peg_y = r * spacing_y
                pegs.append((peg_x, peg_y))

        ball_objects = []
        colors = ["red", "blue", "green", "purple", "orange", "cyan", "magenta", "gold", "pink", "lime"]
        for _ in range(balls):
            ball = {
                "x": width // 2,
                "y": 0,
                "vx": random.uniform(-1, 1),
                "vy": 0,
                "color": random.choice(colors),
                "stopped": False,
                "bounced": False
            }
            ball_objects.append(ball)

        frames = []
        frame_counter = 0
        while frame_counter < max_frames:
            frame_counter += 1
            img = Image.new("RGB", (width, height), color="white")
            draw = ImageDraw.Draw(img)

            for peg_x, peg_y in pegs:
                draw.ellipse([peg_x - 5, peg_y - 5, peg_x + 5, peg_y + 5], fill="gray")

            for i in range(slots):
                slot_x = i * spacing_x
                draw.rectangle([slot_x, height - 60, slot_x + spacing_x, height], outline="black")
                draw.line([(slot_x, height - 60), (slot_x, height)], fill="black", width=3)
                draw.text((slot_x + spacing_x // 2 - 12, height - 50), f"x{prizes[i]}", fill="black", font=font)

            for ball in ball_objects:
                if not ball["stopped"]:
                    ball["vy"] += gravity
                    ball["x"] += ball["vx"]
                    ball["y"] += ball["vy"]

                    ball["x"] = max(ball_radius, min(ball["x"], width - ball_radius))

                    for peg_x, peg_y in pegs:
                        dist = ((ball["x"] - peg_x) ** 2 + (ball["y"] - peg_y) ** 2) ** 0.5
                        if dist < ball_radius + 5:
                            ball["vy"] *= 0.7
                            center_bias = (width / 2 - ball["x"]) / (width / 2)
                            bias_adjustment = center_bias * random.uniform(0.1, 0.3)
                            ball["vx"] += random.choice([-bounce_strength, bounce_strength]) * 0.5 + bias_adjustment
                            break

                    if ball["y"] >= height - 65:
                        slot_index = min(max(int(ball["x"] // spacing_x), 0), slots - 1)
                        slot_center = slot_index * spacing_x + spacing_x / 2

                        if abs(ball["x"] - slot_center) <= spacing_x / 3 or ball["bounced"]:
                            ball["vy"] = 0
                            ball["vx"] = 0
                            ball["y"] = height - 60 + ball_radius // 2
                            ball["stopped"] = True
                        else:
                            ball["vy"] = -5
                            ball["vx"] = random.uniform(-1, 1)
                            ball["bounced"] = True

                draw.ellipse([ball["x"] - ball_radius, ball["y"] - ball_radius,
                              ball["x"] + ball_radius, ball["y"] + ball_radius], fill=ball["color"])

            frames.append(img)


            if all(ball["stopped"] for ball in ball_objects):
                break

        gif_buffer = io.BytesIO()
        frames[0].save(gif_buffer, format="GIF", save_all=True, append_images=frames[1:], duration=frame_delay, loop=0)
        gif_buffer.seek(0)

        final_img = Image.new("RGB", (width, height), color="white")
        draw_final = ImageDraw.Draw(final_img)
        for peg_x, peg_y in pegs:
            draw_final.ellipse([peg_x - 5, peg_y - 5, peg_x + 5, peg_y + 5], fill="gray")
        for i in range(slots):
            slot_x = i * spacing_x
            if prizes[i] >= 10:
                draw_final.rectangle([slot_x, height - 60, slot_x + spacing_x, height], fill="yellow", outline="black")
            else:
                draw_final.rectangle([slot_x, height - 60, slot_x + spacing_x, height], outline="black")
            draw_final.text((slot_x + spacing_x // 2 - 12, height - 50), f"x{prizes[i]}", fill="black", font=font)
        for ball in ball_objects:
            draw_final.ellipse([ball["x"] - ball_radius, ball["y"] - ball_radius,
                                ball["x"] + ball_radius, ball["y"] + ball_radius], fill=ball["color"])

        final_img_buffer = io.BytesIO()
        final_img.save(final_img_buffer, format="PNG")
        final_img_buffer.seek(0)

        return gif_buffer, final_img_buffer, frame_counter, ball_objects

async def setup(client):
    await client.add_cog(Gambling(client))
