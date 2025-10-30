# cog_manager.py

# Import all specific cog command handlers
from cogs.Misc.What_Ghost import handle_command as ghost_handler
from cogs.Audio.Music import handle_command as music_handler
from cogs.PVP.Shoot import handle_command as shoot_handler
from cogs.PVP.ThirteenMonth import handle_command as month_handler

# Import AI fallback handler
from cogs.AI.AI import handle_command as ai_fallback_handler

# Registered cog handlers
COG_HANDLERS = [
    ghost_handler,
    music_handler,
    shoot_handler,
    month_handler,
]

async def handle_voice_command(command: str, client) -> str:
    """
    Routes a voice command to the appropriate handler.
    If no handler returns a response, fallback to AI.
    """
    command = command.lower().strip()

    for handler in COG_HANDLERS:
        try:
            response = await handler(command, client)
            if response:
                return response
        except Exception as e:
            print(f"[CogManager] Error in handler {handler.__name__}: {e}")

    # Fallback to AI
    print("[CogManager] No match found, using AI fallback.")
    return await ai_fallback_handler(command, client)
