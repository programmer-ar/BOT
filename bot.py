import os
import discord
from discord.ext import commands
from discord import app_commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('MTUwNzgzODU5MDYzMjIwMjM3Mg.GlCYQ6.hl3Bue4Mg8TC399OujetcM5MfmdXDSuyuswOU0')
GEMINI_KEY = os.getenv('AIzaSyA6s6ODA6wjH98VbZE0XlQjxW4WnKYVDpE')
LOG_CHANNEL_ID = int(os.getenv('1482416963346239588', 0))

# Initialize Gemini Client
ai_client = genai.Client(api_key=GEMINI_KEY)

# Initialize Discord Bot with Intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read messages for AI assistant/moderation
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user.name} (ID: {bot.user.id})')
    try:
        # Sync slash commands globally
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

---
## INTERACTIVE AI ASSISTANT FEATURES

@bot.event
async def on_message(message):
    # Don't let the bot respond to itself
    if message.author == bot.user:
        return

    # Check if the bot was tagged or command was used
    if bot.user.mentioned_in(message) or message.content.startswith('!ask '):
        ctx = await bot.get_context(message)
        
        # Clean up the prompt text
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask ', '').strip()
        
        if not prompt:
            await message.reply("Hey! Did you need help with something? Try `@bot text` or `!ask your question`.")
            return

        async with ctx.typing():
            try:
                # Prompt tuning for a helpful Discord assistant
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="You are a helpful, friendly, and concise Discord server assistant. Keep answers readable and formatting clean using markdown. Avoid long-winded essays."
                    )
                )
                
                # Discord character limit safety check (2000 chars)
                reply_text = response.text
                if len(reply_text) > 2000:
                    reply_text = reply_text[:1990] + "... (truncated)"
                
                await message.reply(reply_text)
            except Exception as e:
                await message.reply("Sorry, I stumbled while processing that request. Try again shortly!")
                print(f"Gemini Error: {e}")

    # Pass handling over to automation/moderation scans
    await bot.process_commands(message)
    await auto_moderation_scan(message)


---
## AUTOMATED AI MODERATION

async def auto_moderation_scan(message):
    """Scans messages using Gemini to flag toxic behavior for moderators."""
    if message.author.bot or not LOG_CHANNEL_ID:
        return

    # Skip checking if it's a short, common message to save API calls
    if len(message.content) < 4:
        return

    try:
        mod_instruction = (
            "Analyze the following discord message. If it contains extreme toxicity, "
            "severe insults, hate speech, explicit harassment, or dangerous links, respond with the word 'FLAGGED' "
            "followed by a one-sentence reason. If it is safe, respond ONLY with 'SAFE'."
        )
        
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Message: {message.content}",
            config=types.GenerateContentConfig(system_instruction=mod_instruction)
        )
        
        result = response.text.strip()
        
        if result.startswith("FLAGGED"):
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="⚠️ AI Moderation Alert", color=discord.Color.red())
                embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Flagged Message", value=f'"{message.content}"', inline=False)
                embed.add_field(name="AI Assessment", value=result.replace("FLAGGED", "").strip(), inline=False)
                
                await log_channel.send(embed=embed)
                
    except Exception as e:
        print(f"Mod Scan Error: {e}")


---
## MODERATOR SLASH COMMANDS

@bot.tree.command(name="kick", description="Kicks a user from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"🚫 **{member.name}** has been kicked. Reason: {reason}", ephemeral=True)

@bot.tree.command(name="ban", description="Bans a user from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 **{member.name}** has been banned. Reason: {reason}", ephemeral=True)

@bot.tree.command(name="clear", description="Deletes a specified number of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1:
        await interaction.response.send_message("You must delete at least 1 message.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Cleared {len(deleted)} messages.", ephemeral=True)

# Error handling for unauthorized command use
@kick.error
@ban.error
@clear.error
async def mod_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

# Run the Bot
bot.run(DISCORD_TOKEN)