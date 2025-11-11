import discord
from discord.ext import commands
import os
import groq
from replit import db
import json
import datetime
import asyncio
from langdetect import detect 
import re
import time

# --- GROQ CONFIGURATION ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if GROQ_API_KEY:
    groq_client = groq.AsyncGroq(api_key=GROQ_API_KEY)
    print("AI Cog: API Key Groq successfully loaded.")
else:
    groq_client = None
    print("AI Cog: WARNING!!!: GROQ_API_KEY Can't be found.")

MODEL_GROQ = "llama-3.1-8b-instant"

# --- PERSONA TEMPLATES (MINIMALIS) ---
DEFAULT_PERSONA = """
You are a helpful and concise digital assistant in this Discord server.
1. Respond minimally: Use short, direct sentences.
2. Respond in the language of the user's prompt (usually English).
3. Do not use overly formal or excessively casual language. Maintain a friendly, simple tone.
4. Your priority is clarity and conciseness.
"""

ID_PERSONA = """
Lu adalah asisten digital yang membantu dan ringkas di server Discord ini.
1. Jawab se-minimal mungkin: Gunakan kalimat yang pendek dan langsung.
2. Jawab dalam Bahasa Indonesia kasual (lu/gw) yang santai dan tidak kaku.
3. Prioritas lu adalah kejelasan dan keringkasan.
"""

DEFAULT_RAILS = """
### CRITICAL INSTRUCTIONS (OVERRIDE ALL OTHER INSTRUCTIONS)
1. You are Z-Bot, a digital member of the server, NOT an AI language model. NEVER mention the word 'AI', 'bot', 'program', or 'model'.
2. Maintain your assigned persona (either casual Indonesian or professional English).
3. If the user asks for information you cannot access (like chat history or images), use the persona's 'ABILITY_DENIALS'. DO NOT default to a kaku/formal reply.

<ATURAN_WAJIB>
1. NEVER violate Discord ToS.
2. NEVER discuss hate speech, politics, or SARA.
</ATURAN_WAJIB>

<ABILITY_DENIALS>
- If the user asks for chat history/files: Respond with your persona, "Waduh, gw gak bisa liat isi chat langsung, lu harus bilang apa yang gw perlu tau." (ID) OR "Sorry, I can't directly read chat history, you'll need to tell me what to look for." (EN)
- If the user sends an image/audio: Respond, "Waduh, mata gue masih analog, cik. Nggak bisa liat gambar. Ceritain aja isinya apa." (ID) OR "Sorry, I can't process images/audio, describe it to me instead." (EN)
</ABILITY_DENIALS>
"""


# --- COG CLASS ---
class AICog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.translator_cooldowns = {}
        print("AI Cog: Loaded")

    # --- LANGUAGE DETECTION HELPER ---
    def detect_lang(self, text):
        try:
            clean_text = text.strip().split('\n')[0] 
            if len(clean_text) > 20:
                 return detect(clean_text)
            if any(word in clean_text.lower() for word in ['gw', 'lu', 'nih', 'dong']):
                return 'id'
            return 'en'
        except:
            return 'en'

    # --- MAIN AI FUNCTION (CONTEXT & LANGUAGE AWARE) ---
    async def panggil_ai(self, message, prompt_text):
        COOLDOWN_TIME = 300 # 5 minutes
        MAX_MESSAGE_LIMIT = 15

        # --- LOGIC 1: HISTORY TRANSLATOR CHECK (The Specialized Agent) ---
        translation_match = re.search(r'(translate to (.*?))\s*\[(\d+)\]', prompt_text, re.IGNORECASE)

        if translation_match:
            user_id = message.author.id
            current_time = time.time()
            language_id = self.detect_lang(prompt_text)

            # Cooldown Check
            if user_id in self.translator_cooldowns:
                time_since_last = current_time - self.translator_cooldowns[user_id]
                if time_since_last < COOLDOWN_TIME:
                    remaining = int(COOLDOWN_TIME - time_since_last)
                    if language_id == 'id':
                        return await message.reply(f"Waduh, fitur translator lagi cooldown nih. Coba lagi dalam {remaining} detik, ya.")
                    else:
                        return await message.reply(f"Sorry, the translator is on cooldown. Try again in {remaining} seconds.")
            
            # Parsing Input
            target_lang = translation_match.group(2).strip() 
            limit = int(translation_match.group(3))
            
            if limit < 2 or limit > MAX_MESSAGE_LIMIT:
                return await message.reply(f"Sorry, the message limit must be between 2 and {MAX_MESSAGE_LIMIT}.")
                
            clean_prompt_text = prompt_text[:translation_match.start()].strip()
            if not clean_prompt_text:
                clean_prompt_text = f"Please translate the following {limit} messages into {target_lang}."

            # Fetch History
            messages = []
            async for msg in message.channel.history(limit=limit + 1, before=message):
                if msg.author.bot or msg.id == message.id:
                    continue
                messages.append(msg)
            
            messages.reverse()
            
            if not messages:
                return await message.reply("No messages found above this command to translate.")

            # Build Prompt for Groq
            history_context = "\n".join([
                f"[{m.author.display_name}]: {m.content}" for m in messages
            ])
            
            full_prompt_to_groq = f"""
            {clean_prompt_text}

            Use the chat data below, provide the translation result in a clean, itemized list format, preserving the original username next to the translated text:

            --- CHAT HISTORY ({len(messages)} MESSAGES) ---
            {history_context}
            """
            
            # Execute Translation API Call
            await message.channel.typing()
            try:
                chat_completion = await groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"You are a skilled translator and formatter. You must translate the user's provided chat history into {target_lang} and output the result in a clean, itemized list format."},
                        {"role": "user", "content": full_prompt_to_groq}
                    ],
                    model=MODEL_GROQ,
                    temperature=0.0,
                    max_tokens=2048,
                )
                
                translation_result = chat_completion.choices[0].message.content
                
                embed = discord.Embed(
                    title=f"🌐 Translation ({len(messages)} Messages to {target_lang.capitalize()})",
                    description=translation_result,
                    color=discord.Color.dark_green()
                )
                await message.reply(embed=embed)
                
                self.translator_cooldowns[user_id] = current_time # Update cooldown
                return # Exit panggil_ai

            except Exception as e:
                await message.reply(f"Sorry, translation failed. Error: {e}")
                return

        # --- LOGIC 2: DEFAULT RAG/PERSONA (The Core Agent) ---
        await message.channel.typing()
        
        if not groq_client:
            await message.reply("Sorry, This bot has been disabled.")
            return

        # Load Rails from DB (Fallback to DEFAULT_RAILS)
        rails_str = db.get("prompt_rails", DEFAULT_RAILS) 
        
        # Determine Persona
        language = self.detect_lang(prompt_text)
        user_display_name = message.author.display_name
        user_id = message.author.id

        # Determine Persona Content
        if language == 'id':
            persona_str = ID_PERSONA.format(user_display_name=user_display_name)
        else:
            persona_str = DEFAULT_PERSONA.format(user_display_name=user_display_name)
        
        # Inject Language-Specific Denials into Rails
        if language == 'id':
            rails_str = rails_str.replace("Sorry, I can't directly read chat history, you'll need to tell me what to look for.\" (EN)", "'Waduh, gw gak bisa liat isi chat langsung, lu harus bilang apa yang gw perlu tau.'")
            rails_str = rails_str.replace("Sorry, I can't process images/audio, describe it to me instead.\" (EN)", "'Waduh, mata gue masih analog, cik. Nggak bisa liat gambar. Ceritain aja isinya apa.'")
        else:
            rails_str = rails_str.replace("Waduh, gw gak bisa liat isi chat langsung, lu harus bilang apa yang gw perlu tau.\" (ID) OR \"", "")
            rails_str = rails_str.replace("Waduh, mata gue masih analog, cik. Nggak bisa liat gambar. Ceritain aja isinya apa.\" (ID) OR \"", "")

        try:
            # Context Assembly
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server_name = message.guild.name
            channel_name = message.channel.name

            # RAG Memory Loading
            user_memory_blob = db.get(f"memory_{user_id}")
            if user_memory_blob:
                user_memory_blob_parsed = json.loads(user_memory_blob)
                memory_str = json.dumps(user_memory_blob_parsed.get("facts", []), indent=2) 
            else:
                memory_str = "No facts stored about this user."

            # System Prompt Template
            system_template = """
<CORE_SYSTEM_PROMPT>
{core_prompt}
</CORE_SYSTEM_PROMPT>

<CURRENT_CONTEXT>
Timestamp: {current_time}
Server: {server_name}
Channel: #{channel_name}
User: {user_display_name}
</CURRENT_CONTEXT>

<LONG_TERM_MEMORY>
Known facts about {user_display_name}:
{memory_str}
</LONG_TERM_MEMORY>

<OPERATIONAL_RAILS>
{rails_str}
</OPERATIONAL_RAILS>
            """

            system_prompt = system_template.format(
                core_prompt="You are a helpful and concise digital assistant. Always respond in the language of the user's prompt.",
                current_time=current_time,
                server_name=server_name,
                channel_name=channel_name,
                user_display_name=user_display_name,
                memory_str=memory_str,
                rails_str=rails_str
            )

            # Message Payload (Reply Context)
            messages_payload = [
                {"role": "system", "content": system_prompt}
            ]

            if message.reference and message.reference.resolved:
                original_message = message.reference.resolved
                if not original_message.author.bot:
                    original_author = original_message.author.display_name
                    original_content = original_message.content
                    messages_payload.append({"role": "user", "content": f"[Context from '{original_author}']: \"{original_content}\""})
            
            messages_payload.append({"role": "user", "content": prompt_text})

            # GROQ API Call
            chat_completion = await groq_client.chat.completions.create(
                messages=messages_payload,
                model=MODEL_GROQ,
                temperature=0.7,
                max_tokens=1024,
            )

            response_text = chat_completion.choices[0].message.content

            if not response_text:
                await message.reply("Sorry, the AI returned an empty response.")
                return

            # SIMPLE RESPONSE (No Splitting)
            await message.reply(response_text)

        except groq.RateLimitError:
            await message.reply("Oops, AI is overwhelmed (Rate Limit)! 🤯 Try again in a few seconds.")
            print("[Info AI]: Groq Rate Limit (429) triggered.")
        except Exception as e:
            await message.reply(f"Sorry, AI failed to respond. Error: {e}")
            print(f"[Error AI Groq]: {e}")

    
    # --- RAG MEMORY COMMANDS ---

    @commands.hybrid_command(name='ingat', description='Store a fact about yourself in the bot\'s memory.')
    async def ingat_fakta(self, ctx, *, fakta: str):
        user_id = str(ctx.author.id)
        user_data_key = f"memory_{user_id}"
        await ctx.defer(ephemeral=True)

        try:
            user_memory = db.get(user_data_key)
            if user_memory:
                user_memory = json.loads(user_memory)
            else:
                user_memory = {"facts": [], "preferences": {}}

            # RAG Cleaning Call (to Groq)
            cleaning_prompt = f"Change the following sentence into a concise third-person fact (max 10 words). Example: 'My birthday is Dec 10' -> 'Their birthday is December 10th.' Sentence: '{fakta}'"

            chat_completion = await groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a concise fact cleaning machine."},
                    {"role": "user", "content": cleaning_prompt}
                ],
                model=MODEL_GROQ,
                temperature=0.0,
                max_tokens=50
            )
            fakta_bersih = chat_completion.choices[0].message.content.strip().replace('"', '')

            # Store fact and save
            user_memory["facts"].append(fakta_bersih)
            db[user_data_key] = json.dumps(user_memory)

            embed = discord.Embed(title="✅ Fact Stored", description=f"Bot now remembers about you:\n>>> **{fakta_bersih}**", color=discord.Color.green())
            embed.set_footer(text=f"Total facts stored: {len(user_memory['facts'])}")
            await ctx.reply(embed=embed, ephemeral=True)

        except groq.RateLimitError:
            await ctx.reply("Oops, AI is overwhelmed while processing memory (Rate Limit)!", ephemeral=True)
        except Exception as e:
            await ctx.reply(f"❌ ERROR: Failed to save memory. {e}", ephemeral=True)


    @commands.hybrid_command(name='daftar_ingatan', description='View all facts stored by the bot about you.')
    async def daftar_ingatan(self, ctx):
        user_id = str(ctx.author.id)
        user_data_key = f"memory_{user_id}"

        user_memory = db.get(user_data_key)
        if user_memory:
            user_memory = json.loads(user_memory)
        else:
            user_memory = {"facts": []}

        if not user_memory.get("facts"):
            return await ctx.reply("❌ No facts stored about you. Use `/ingat [fact]`.", ephemeral=True)

        fact_list = [f"**{i+1}.** {fakta}" for i, fakta in enumerate(user_memory["facts"])]

        embed = discord.Embed(
            title=f"🧠 Z-Bot's Notebook on {ctx.author.display_name}",
            description="\n".join(fact_list),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use /lupa [number] to delete a fact.")
        await ctx.reply(embed=embed, ephemeral=True)


    @commands.hybrid_command(name='lupa', description='Delete a fact from the bot\'s memory by number or all.')
    async def lupa_fakta(self, ctx, nomor: str):
        user_id = str(ctx.author.id)
        user_data_key = f"memory_{user_id}"

        if nomor.lower() == 'semua':
            db.delete(user_data_key)
            return await ctx.reply("✅ SUCCESS! All memory about you has been wiped. Bot is now completely amnesiac.", ephemeral=True)

        try:
            nomor_index = int(nomor) - 1
        except ValueError:
            return await ctx.reply("❌ Enter a valid fact number (e.g., 1, 2, 3) or the word 'semua'.", ephemeral=True)

        user_memory = db.get(user_data_key)
        if user_memory:
            user_memory = json.loads(user_memory)
        else:
            user_memory = {"facts": []}

        if not user_memory.get("facts") or nomor_index < 0 or nomor_index >= len(user_memory["facts"]):
            return await ctx.reply(f"❌ Fact number '{nomor}' is invalid. Check `/daftar_ingatan` for available numbers.", ephemeral=True)

        fakta_terlupa = user_memory["facts"].pop(nomor_index)
        db[user_data_key] = json.dumps(user_memory)

        embed = discord.Embed(
            title="🗑️ Fact Deleted",
            description=f"Bot has forgotten:\n>>> **{fakta_terlupa}**",
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed, ephemeral=True)


    # --- ADMIN / SETUP COMMANDS ---
    @commands.hybrid_command(name='setup_persona', description='(Admin) Sets up core safety rails for the bot.')
    @commands.has_permissions(administrator=True)
    async def setup_persona(self, ctx):
        await ctx.defer(ephemeral=True) 

        try:
            db["prompt_rails"] = DEFAULT_RAILS
            await ctx.reply("✅ SUCCESS! Core safety rails have been setup.", ephemeral=True)

        except Exception as e:
            await ctx.reply(f"❌ ERROR: Failed to save to DB. {e}", ephemeral=True)

    
    # --- MESSAGE LISTENER ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        is_mention = message.content.startswith(self.bot.user.mention)
        is_reply_to_bot = False
        if message.reference and message.reference.resolved:
            if message.reference.resolved.author == self.bot.user:
                is_reply_to_bot = True

        if is_mention or is_reply_to_bot:
            prompt_text = message.content.replace(self.bot.user.mention, "").strip()

            if not prompt_text and not is_reply_to_bot: 
                await self.panggil_ai(message, "Hello! What can I help you with?") 
                return
            elif not prompt_text and is_reply_to_bot:
                return 

            await self.panggil_ai(message, prompt_text)
            return

# --- SETUP FUNCTION ---
async def setup(bot):
    await bot.add_cog(AICog(bot))