import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("7660400157:AAGOLlb2TDrp2nsEms7xHa1VBQJ72jrOgxY")
MONGO_URI = os.getenv("mongodb+srv://sseries:sseries@sseries.tqmstei.mongodb.net/?retryWrites=true&w=majority")
ADMIN_IDS = [int(id) for id in os.getenv("6687248633", "").split(",") if id]
DATABASE_CHANNEL = os.getenv("-1001790682728")
BOT_USERNAME = os.getenv("@Sseriesareamoviesearch_bot")

# Default settings
DEFAULT_NRF_IMAGE = "https://envs.sh/ij_.jpg/HGBOTZ.jpg"
DEFAULT_AUTO_DELETE_TIME = 60  # seconds
DEFAULT_MODE = "private"  # or "public"
