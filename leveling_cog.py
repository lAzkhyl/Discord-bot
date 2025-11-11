import discord
from discord.ext import commands
from replit import db
import os
import time
import json


ROLE_MV_ID = 1433114931313643681
ROLE_FRIENDS_ID = 1433120829016899757
XP_PER_MESSAGE = 15
XP_COOLDOWN = 60

# 2. DATABASE
def xp_for_next_level(level):
    return 100 * (level + 1)

def get_user_data(user_id):
    user_key = str(user_id)
    if user_key in db:
        try:
            return json.loads(db[user_key])
        except:
            return {"role_a": {"xp": 0, "level": 0}, "role_b": {"xp": 0, "level": 0}}
    else:
        return {"role_a": {"xp": 0, "level": 0}, "role_b": {"xp": 0, "level": 0}}

def save_user_data(user_id, data):
    user_key = str(user_id)
    db[user_key] = json.dumps(data)

def check_level_up(role_data):
    while role_data["xp"] >= xp_for_next_level(role_data["level"]):
        role_data["xp"] -= xp_for_next_level(role_data["level"])
        role_data["level"] += 1
    return role_data

# 3. COG LEVELING
class LevelingCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {} 
        print("Leveling Cog: Modul Leveling telah di-load.")

    # 4. ON_MESSAGE XP
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Abaikan DM
        if message.guild is None:
            return

        # ! PENTING: Cek apakah pesan ini ditujukan untuk AI.
        # Jika ya, JANGAN berikan XP.
        if message.content.startswith(self.bot.user.mention):
            return
        if message.reference and message.reference.resolved:
            if message.reference.resolved.author == self.bot.user:
                return

        # --- Logika Leveling Anda ---
        current_time = time.time()
        user_id = message.author.id

        if user_id in self.user_cooldowns:
            time_since_last = current_time - self.user_cooldowns[user_id]
            if time_since_last < XP_COOLDOWN:
                return # Masih cooldown, hentikan

        has_role_mv = any(role.id == ROLE_MV_ID for role in message.author.roles)
        has_role_friends = any(role.id == ROLE_FRIENDS_ID for role in message.author.roles)

        if not has_role_mv and not has_role_friends:
            return # Tidak punya role, hentikan

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
        self.user_cooldowns[user_id] = current_time

        for role_name, new_level in leveled_up_roles:
            await message.channel.send(
                f"🎉 Congrats {message.author.mention}, you reached Level {new_level} for **{role_name}**!"
            )

        # PENTING: Setelah semua listener on_message selesai,
        # kita perlu memproses $command jika ada.
        await self.bot.process_commands(message)


    # --- 5. SEMUA COMMAND LEVELING ---
    # Pindahkan SEMUA command Anda ke sini, di dalam kelas LevelingCog

    @commands.command(name='level')
    async def level_command(self, ctx):
        """Display user's level and XP for both roles"""
        user_id = ctx.author.id
        user_data = get_user_data(user_id)
        embed = discord.Embed(title=f"📊 {ctx.author.display_name}'s Level Stats", color=discord.Color.blue())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        # Role MV
        role_mv_data = user_data["role_a"]
        role_mv_xp_needed = xp_for_next_level(role_mv_data["level"])
        embed.add_field(
            name="🔵 Role MV",
            value=f"**Level:** {role_mv_data['level']}\n"
                  f"**XP:** {role_mv_data['xp']}/{role_mv_xp_needed}\n"
                  f"**Progress:** {int((role_mv_data['xp'] / role_mv_xp_needed) * 100)}%",
            inline=True
        )
        # Role Friends
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


    @commands.hybrid_command(name='test', description='Test command to verify the bot is working')
    async def test_command(self, ctx):
        embed = discord.Embed(title="✅ Bot Test", description="The bot is working perfectly!", color=discord.Color.green())
        embed.add_field(name="Bot Status", value="🟢 Online and Ready", inline=False)
        embed.add_field(name="Server", value=f"{ctx.guild.name if ctx.guild else 'Direct Message'}", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)


    @commands.hybrid_command(name='addxp', description='Add XP to a user for a specific role')
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: int, role: str):
        # (Salin sisa kode command addxp Anda di sini)
        role = role.lower()
        if role not in ['mv', 'friends']:
            await ctx.send("❌ Role must be either 'mv' or 'friends'", ephemeral=True)
            return

        user_data = get_user_data(member.id)
        role_key = "role_a" if role == "mv" else "role_b"
        role_name = "Role MV" if role == "mv" else "Role Friends"

        old_level = user_data[role_key]["level"]
        user_data[role_key]["xp"] += amount
        user_data[role_key] = check_level_up(user_data[role_key])

        save_user_data(member.id, user_data)

        embed = discord.Embed(title="✅ XP Added", color=discord.Color.green())
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role_name, inline=True)
        embed.add_field(name="XP Added", value=f"+{amount}", inline=True)
        embed.add_field(name="New Total XP", value=user_data[role_key]["xp"], inline=True)
        embed.add_field(name="Current Level", value=user_data[role_key]["level"], inline=True)
        # ... (tambahkan sisa field embed Anda jika ada)
        await ctx.send(embed=embed)


    # ... (Tambahkan SEMUA command Anda yang lain: removexp, setlevel, resetuser, leaderboard, rank) ...
    # ... Cukup copy-paste dari kode lama Anda, pastikan 'self' ada di parameter pertama ...

    @commands.hybrid_command(name='leaderboard', description='Show top users by level and XP')
    async def leaderboard(self, ctx, role: str = "mv"):
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

        embed = discord.Embed(title=f"🏆 Leaderboard - {role_name}", description="Top 10 users by level and XP", color=discord.Color.gold())

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


# --- 6. SETUP FUNCTION ---
# Wajib ada agar main.py bisa memuat Cog ini
async def setup(bot):
    await bot.add_cog(LevelingCog(bot))