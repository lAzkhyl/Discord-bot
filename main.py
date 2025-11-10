import discord
from discord.ext import commands
from replit import db
import os
import time
import json
from keep_alive import keep_alive

ROLE_A_ID = 1234567890123456789
ROLE_B_ID = 9876543210987654321

XP_PER_MESSAGE = 15
XP_COOLDOWN = 60

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

user_cooldowns = {}

def xp_for_next_level(level):
    """Calculate XP required for the next level"""
    return 100 * (level + 1)

def get_user_data(user_id):
    """Retrieve user data from the database"""
    user_key = str(user_id)
    if user_key in db:
        try:
            return json.loads(db[user_key])
        except:
            return {
                "role_a": {"xp": 0, "level": 0},
                "role_b": {"xp": 0, "level": 0}
            }
    else:
        return {
            "role_a": {"xp": 0, "level": 0},
            "role_b": {"xp": 0, "level": 0}
        }

def save_user_data(user_id, data):
    """Save user data to the database"""
    user_key = str(user_id)
    db[user_key] = json.dumps(data)

def check_level_up(role_data):
    """Check if user has leveled up and return new level if so"""
    while role_data["xp"] >= xp_for_next_level(role_data["level"]):
        role_data["xp"] -= xp_for_next_level(role_data["level"])
        role_data["level"] += 1
    return role_data

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return
    
    current_time = time.time()
    user_id = message.author.id
    
    if user_id in user_cooldowns:
        time_since_last = current_time - user_cooldowns[user_id]
        if time_since_last < XP_COOLDOWN:
            await bot.process_commands(message)
            return
    
    has_role_a = any(role.id == ROLE_A_ID for role in message.author.roles)
    has_role_b = any(role.id == ROLE_B_ID for role in message.author.roles)
    
    if not has_role_a and not has_role_b:
        await bot.process_commands(message)
        return
    
    user_data = get_user_data(user_id)
    
    leveled_up_roles = []
    
    if has_role_a:
        old_level = user_data["role_a"]["level"]
        user_data["role_a"]["xp"] += XP_PER_MESSAGE
        user_data["role_a"] = check_level_up(user_data["role_a"])
        
        if user_data["role_a"]["level"] > old_level:
            leveled_up_roles.append(("Role A", user_data["role_a"]["level"]))
    
    if has_role_b:
        old_level = user_data["role_b"]["level"]
        user_data["role_b"]["xp"] += XP_PER_MESSAGE
        user_data["role_b"] = check_level_up(user_data["role_b"])
        
        if user_data["role_b"]["level"] > old_level:
            leveled_up_roles.append(("Role B", user_data["role_b"]["level"]))
    
    save_user_data(user_id, user_data)
    user_cooldowns[user_id] = current_time
    
    for role_name, new_level in leveled_up_roles:
        await message.channel.send(
            f"🎉 Congrats {message.author.mention}, you reached Level {new_level} for **{role_name}**!"
        )
    
    await bot.process_commands(message)

@bot.command(name='level')
async def level_command(ctx):
    """Display user's level and XP for both roles"""
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    
    embed = discord.Embed(
        title=f"📊 {ctx.author.display_name}'s Level Stats",
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    role_a_data = user_data["role_a"]
    role_a_xp_needed = xp_for_next_level(role_a_data["level"])
    embed.add_field(
        name="🔵 Role A",
        value=f"**Level:** {role_a_data['level']}\n"
              f"**XP:** {role_a_data['xp']}/{role_a_xp_needed}\n"
              f"**Progress:** {int((role_a_data['xp'] / role_a_xp_needed) * 100)}%",
        inline=True
    )
    
    role_b_data = user_data["role_b"]
    role_b_xp_needed = xp_for_next_level(role_b_data["level"])
    embed.add_field(
        name="🟢 Role B",
        value=f"**Level:** {role_b_data['level']}\n"
              f"**XP:** {role_b_data['xp']}/{role_b_xp_needed}\n"
              f"**Progress:** {int((role_b_data['xp'] / role_b_xp_needed) * 100)}%",
        inline=True
    )
    
    embed.set_footer(text=f"XP Cooldown: {XP_COOLDOWN} seconds | XP per message: {XP_PER_MESSAGE}")
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    keep_alive()
    
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not found in environment variables!")
        print("Please add your Discord bot token to Replit Secrets.")
    else:
        bot.run(token)
