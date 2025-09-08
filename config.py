import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
DATABASE_CHANNEL = os.getenv("DATABASE_CHANNEL")
BOT_USERNAME = os.getenv("BOT_USERNAME")

# Default settings
DEFAULT_NRF_IMAGE = "https://envs.sh/ij_.jpg/HGBOTZ.jpg"
DEFAULT_AUTO_DELETE_TIME = 60  # seconds
DEFAULT_MODE = "private"  # or "public"
