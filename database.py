from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import DuplicateKeyError
from config import MONGO_URI
import datetime

class DatabaseHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client.telegram_search_bot
        
        # Collections
        self.posts = self.db.posts
        self.users = self.db.users
        self.settings = self.db.settings
        self.requests = self.db.requests
        self.stats = self.db.stats
        
        # Create indexes
        self.posts.create_index([("caption", TEXT)])
        self.posts.create_index([("message_id", ASCENDING)])
        self.users.create_index([("user_id", ASCENDING)])
        
        # Initialize settings if not exists
        if not self.settings.find_one({"key": "mode"}):
            self.settings.insert_one({
                "key": "mode", 
                "value": "private"
            })
        if not self.settings.find_one({"key": "nrf_image"}):
            self.settings.insert_one({
                "key": "nrf_image", 
                "value": "https://example.com/default_nrf_image.jpg"
            })
        if not self.settings.find_one({"key": "private_link"}):
            self.settings.insert_one({
                "key": "private_link", 
                "value": ""
            })

    def add_post(self, message_id, caption, photo_id, date):
        return self.posts.insert_one({
            "message_id": message_id,
            "caption": caption,
            "photo_id": photo_id,
            "date": date,
            "added_at": datetime.datetime.now()
        })
    
    def search_posts(self, query, limit=10):
        # Using MongoDB text search with fuzzy matching
        return list(self.posts.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit))
    
    def add_user(self, user_id, username, first_name, last_name):
        try:
            return self.users.insert_one({
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "joined_at": datetime.datetime.now(),
                "search_count": 0,
                "last_seen": datetime.datetime.now()
            })
        except DuplicateKeyError:
            # User already exists, update last seen
            return self.update_user_last_seen(user_id)
    
    def update_user_last_seen(self, user_id):
        return self.users.update_one(
            {"user_id": user_id},
            {"$set": {"last_seen": datetime.datetime.now()}}
        )
    
    def increment_search_count(self, user_id):
        return self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"search_count": 1}}
        )
    
    def get_user_stats(self):
        total_users = self.users.count_documents({})
        total_searches = self.users.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$search_count"}}}
        ])
        total_searches = list(total_searches)[0]["total"] if total_searches else 0
        return total_users, total_searches
    
    def get_setting(self, key):
        setting = self.settings.find_one({"key": key})
        return setting["value"] if setting else None
    
    def update_setting(self, key, value):
        return self.settings.update_one(
            {"key": key},
            {"$set": {"value": value}},
            upsert=True
        )
    
    def add_admin_request(self, user_id, query):
        return self.requests.insert_one({
            "user_id": user_id,
            "query": query,
            "status": "pending",
            "requested_at": datetime.datetime.now()
        })
    
    def get_pending_requests(self):
        return list(self.requests.find({"status": "pending"}))
    
    def update_request_status(self, request_id, status):
        return self.requests.update_one(
            {"_id": request_id},
            {"$set": {"status": status}}
        )

# Global database instance
db = DatabaseHandler()
