import discord
from discord.ext import commands
import os
import asyncio

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

# --- EVENT ON_READY ---
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')

# --- COG LOADER & MAIN LOOP ---
async def main():
    # Hanya memuat Cog AI
    cogs_to_load = [
        "ai_cog",
    ]

    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f"Successfully loaded module: {cog}")
        except Exception as e:
            print(f"ERROR: Failed to load module {cog}: {e}")

    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not found!")
        return

    # Keep_alive dihapus total karena Anda akan deploy di Railway/Render
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())