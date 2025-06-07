import os

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found")
