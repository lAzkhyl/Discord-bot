import discord
from discord.ext import commands
from replit import db
import os
import time
import json
from keep_alive import keep_alive

ROLE_MV_ID = 1433114931313643681
ROLE_FRIENDS_ID = 1433120829016899757

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
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return
    
    if message.guild is None:
        await bot.process_commands(message)
        return
    
    current_time = time.time()
    user_id = message.author.id
    
    if user_id in user_cooldowns:
        time_since_last = current_time - user_cooldowns[user_id]
        if time_since_last < XP_COOLDOWN:
            await bot.process_commands(message)
            return
    
    has_role_mv = any(role.id == ROLE_MV_ID for role in message.author.roles)
    has_role_friends = any(role.id == ROLE_FRIENDS_ID for role in message.author.roles)
    
    if not has_role_mv and not has_role_friends:
        await bot.process_commands(message)
        return
    
    user_data = get_user_data(user_id)
    
    leveled_up_roles = []
    
    if has_role_mv:
        old_level = user_data["role_a"]["level"]
        user_data["role_a"]["xp"] += XP_PER_MESSAGE
        user_data["role_a"] = check_level_up(user_data["role_a"])
        
        if user_data["role_a"]["level"] > old_level:
            leveled_up_roles.append(("Role MV", user_data["role_a"]["level"]))
    
    if has_role_friends:
        old_level = user_data["role_b"]["level"]
        user_data["role_b"]["xp"] += XP_PER_MESSAGE
        user_data["role_b"] = check_level_up(user_data["role_b"])
        
        if user_data["role_b"]["level"] > old_level:
            leveled_up_roles.append(("Role Friends", user_data["role_b"]["level"]))
    
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
    
    role_mv_data = user_data["role_a"]
    role_mv_xp_needed = xp_for_next_level(role_mv_data["level"])
    embed.add_field(
        name="🔵 Role MV",
        value=f"**Level:** {role_mv_data['level']}\n"
              f"**XP:** {role_mv_data['xp']}/{role_mv_xp_needed}\n"
              f"**Progress:** {int((role_mv_data['xp'] / role_mv_xp_needed) * 100)}%",
        inline=True
    )
    
    role_friends_data = user_data["role_b"]
    role_friends_xp_needed = xp_for_next_level(role_friends_data["level"])
    embed.add_field(
        name="🟢 Role Friends",
        value=f"**Level:** {role_friends_data['level']}\n"
              f"**XP:** {role_friends_data['xp']}/{role_friends_xp_needed}\n"
              f"**Progress:** {int((role_friends_data['xp'] / role_friends_xp_needed) * 100)}%",
        inline=True
    )
    
    embed.set_footer(text=f"XP Cooldown: {XP_COOLDOWN} seconds | XP per message: {XP_PER_MESSAGE}")
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='test', description='Test command to verify the bot is working')
async def test_command(ctx):
    """Test command that works with both prefix (!) and slash (/)"""
    embed = discord.Embed(
        title="✅ Bot Test",
        description="The bot is working perfectly!",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Bot Status",
        value="🟢 Online and Ready",
        inline=False
    )
    
    embed.add_field(
        name="Server",
        value=f"{ctx.guild.name if ctx.guild else 'Direct Message'}",
        inline=True
    )
    
    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="Command Usage",
        value="This command works with:\n• Prefix: `!test`\n• Slash: `/test`",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='addxp', description='Add XP to a user for a specific role')
@commands.has_permissions(administrator=True)
async def add_xp(ctx, member: discord.Member, amount: int, role: str):
    """Add XP to a user (Admin only)"""
    role = role.lower()
    if role not in ['mv', 'friends']:
        await ctx.send("❌ Role must be either 'mv' or 'friends'", ephemeral=True)
        return
    
    if amount <= 0:
        await ctx.send("❌ Amount must be positive!", ephemeral=True)
        return
    
    user_data = get_user_data(member.id)
    role_key = "role_a" if role == "mv" else "role_b"
    role_name = "Role MV" if role == "mv" else "Role Friends"
    
    old_level = user_data[role_key]["level"]
    user_data[role_key]["xp"] += amount
    user_data[role_key] = check_level_up(user_data[role_key])
    
    save_user_data(member.id, user_data)
    
    embed = discord.Embed(
        title="✅ XP Added",
        color=discord.Color.green()
    )
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Role", value=role_name, inline=True)
    embed.add_field(name="XP Added", value=f"+{amount}", inline=True)
    embed.add_field(name="New Total XP", value=user_data[role_key]["xp"], inline=True)
    embed.add_field(name="Current Level", value=user_data[role_key]["level"], inline=True)
    
    if user_data[role_key]["level"] > old_level:
        embed.add_field(name="🎉 Level Up!", value=f"Leveled up to {user_data[role_key]['level']}!", inline=False)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='removexp', description='Remove XP from a user for a specific role')
@commands.has_permissions(administrator=True)
async def remove_xp(ctx, member: discord.Member, amount: int, role: str):
    """Remove XP from a user (Admin only)"""
    role = role.lower()
    if role not in ['mv', 'friends']:
        await ctx.send("❌ Role must be either 'mv' or 'friends'", ephemeral=True)
        return
    
    if amount <= 0:
        await ctx.send("❌ Amount must be positive!", ephemeral=True)
        return
    
    user_data = get_user_data(member.id)
    role_key = "role_a" if role == "mv" else "role_b"
    role_name = "Role MV" if role == "mv" else "Role Friends"
    
    user_data[role_key]["xp"] = max(0, user_data[role_key]["xp"] - amount)
    
    save_user_data(member.id, user_data)
    
    embed = discord.Embed(
        title="✅ XP Removed",
        color=discord.Color.orange()
    )
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Role", value=role_name, inline=True)
    embed.add_field(name="XP Removed", value=f"-{amount}", inline=True)
    embed.add_field(name="New Total XP", value=user_data[role_key]["xp"], inline=True)
    embed.add_field(name="Current Level", value=user_data[role_key]["level"], inline=True)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='setlevel', description='Set a user\'s level for a specific role')
@commands.has_permissions(administrator=True)
async def set_level(ctx, member: discord.Member, level: int, role: str):
    """Set a user's level (Admin only)"""
    role = role.lower()
    if role not in ['mv', 'friends']:
        await ctx.send("❌ Role must be either 'mv' or 'friends'", ephemeral=True)
        return
    
    if level < 0:
        await ctx.send("❌ Level must be 0 or higher!", ephemeral=True)
        return
    
    user_data = get_user_data(member.id)
    role_key = "role_a" if role == "mv" else "role_b"
    role_name = "Role MV" if role == "mv" else "Role Friends"
    
    user_data[role_key]["level"] = level
    user_data[role_key]["xp"] = 0
    
    save_user_data(member.id, user_data)
    
    embed = discord.Embed(
        title="✅ Level Set",
        color=discord.Color.blue()
    )
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Role", value=role_name, inline=True)
    embed.add_field(name="New Level", value=level, inline=True)
    embed.add_field(name="XP Reset", value="0", inline=True)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='resetuser', description='Reset all progress for a user')
@commands.has_permissions(administrator=True)
async def reset_user(ctx, member: discord.Member):
    """Reset a user's progress (Admin only)"""
    user_data = {
        "role_a": {"xp": 0, "level": 0},
        "role_b": {"xp": 0, "level": 0}
    }
    
    save_user_data(member.id, user_data)
    
    embed = discord.Embed(
        title="✅ User Reset",
        description=f"All progress has been reset for {member.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name="Role MV", value="Level 0 | 0 XP", inline=True)
    embed.add_field(name="Role Friends", value="Level 0 | 0 XP", inline=True)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='leaderboard', description='Show top users by level and XP')
async def leaderboard(ctx, role: str = "mv"):
    """Display leaderboard for a specific role"""
    role = role.lower()
    if role not in ['mv', 'friends']:
        await ctx.send("❌ Role must be either 'mv' or 'friends'", ephemeral=True)
        return
    
    role_key = "role_a" if role == "mv" else "role_b"
    role_name = "Role MV" if role == "mv" else "Role Friends"
    
    all_users = []
    for user_id in db.keys():
        try:
            user_data = json.loads(db[user_id])
            all_users.append({
                'id': int(user_id),
                'level': user_data[role_key]['level'],
                'xp': user_data[role_key]['xp']
            })
        except:
            continue
    
    all_users.sort(key=lambda x: (x['level'], x['xp']), reverse=True)
    top_users = all_users[:10]
    
    embed = discord.Embed(
        title=f"🏆 Leaderboard - {role_name}",
        description="Top 10 users by level and XP",
        color=discord.Color.gold()
    )
    
    if not top_users:
        embed.description = "No users have earned XP yet!"
    else:
        leaderboard_text = ""
        for idx, user_info in enumerate(top_users, 1):
            try:
                member = ctx.guild.get_member(user_info['id'])
                name = member.display_name if member else f"User {user_info['id']}"
            except:
                name = f"User {user_info['id']}"
            
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`{idx}.`"
            leaderboard_text += f"{medal} **{name}** - Level {user_info['level']} ({user_info['xp']} XP)\n"
        
        embed.description = leaderboard_text
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='rank', description='Check your rank on the leaderboard')
async def rank(ctx, member: discord.Member = None):
    """Check your rank or another user's rank"""
    target = member or ctx.author
    
    embed = discord.Embed(
        title=f"📊 {target.display_name}'s Rank",
        color=discord.Color.blue()
    )
    
    for role, role_key, role_name in [("mv", "role_a", "Role MV"), ("friends", "role_b", "Role Friends")]:
        all_users = []
        for user_id in db.keys():
            try:
                user_data = json.loads(db[user_id])
                all_users.append({
                    'id': int(user_id),
                    'level': user_data[role_key]['level'],
                    'xp': user_data[role_key]['xp']
                })
            except:
                continue
        
        all_users.sort(key=lambda x: (x['level'], x['xp']), reverse=True)
        
        rank = None
        for idx, user_info in enumerate(all_users, 1):
            if user_info['id'] == target.id:
                rank = idx
                break
        
        user_data = get_user_data(target.id)
        rank_text = f"Rank #{rank}/{len(all_users)}" if rank else "Unranked"
        
        embed.add_field(
            name=f"{'🔵' if role == 'mv' else '🟢'} {role_name}",
            value=f"{rank_text}\nLevel {user_data[role_key]['level']} | {user_data[role_key]['xp']} XP",
            inline=True
        )
    
    embed.set_thumbnail(url=target.display_avatar.url)
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    keep_alive()
    
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not found in environment variables!")
        print("Please add your Discord bot token to Replit Secrets.")
    else:
        bot.run(token)
