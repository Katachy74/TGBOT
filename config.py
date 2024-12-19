import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Токен Telegram-бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# API-ключ AccuWeather
ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY")

# API-ключ GraphHopper
GRAPHHOPPER_API_KEY = os.getenv("GRAPHHOPPER_API_KEY")