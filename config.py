import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY")

GRAPHHOPPER_API_KEY = os.getenv("GRAPHHOPPER_API_KEY")
