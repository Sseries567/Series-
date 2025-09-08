import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ConversationHandler
)
from telegram.error import BadRequest
import datetime
import asyncio

from config import BOT_TOKEN, ADMIN_IDS, BOT_USERNAME
from database import db
from utils import format_results, get_random_emoji, fuzzy_search

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
BROADCAST_MESSAGE = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = (
        f"Hello {user.first_name}! 👋\n\n"
        "I'm an advanced search bot. You can search for content by typing any text.\n\n"
        "Just send me what you're looking for and I'll find it for you!"
    )
    
    await update.message.reply_text(welcome_text)

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.message.text
    
    # Update user stats
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    db.increment_search_count(user.id)
    
    # Check if private mode is enabled and if user has joined the channel
    mode = db.get_setting("mode")
    if mode == "private":
        private_link = db.get_setting("private_link")
        if private_link:
            # Check if user is a member of the channel
            try:
                member = await context.bot.get_chat_member(private_link, user.id)
                if member.status in ['left', 'kicked']:
                    join_button = InlineKeyboardMarkup([[
                        InlineKeyboardButton("Join Channel", url=private_link)
                    ]])
                    await update.message.reply_text(
                        "Please join our channel to use the search feature.",
                        reply_markup=join_button
                    )
                    return
            except BadRequest:
                logger.error("Error checking channel membership")
    
    # Send searching message
    searching_msg = await update.message.reply_text("🔎 Searching...")
    
    # Wait for 1 second
    await asyncio.sleep(1)
    
    # Delete searching message
    await searching_msg.delete()
    
    # Perform search
    results = db.search_posts(query)
    
    if results:
        # Format and send results
        private_mode = db.get_setting("mode") == "private"
        private_link = db.get_setting("private_link")
        formatted_results = format_results(results, private_mode, private_link)
        
        # Send results with a random emoji reaction
        sent_message = await update.message.reply_text(
            formatted_results, 
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        # Add reaction
        try:
            await update.message.react(get_random_emoji())
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
        
        # Auto-delete if enabled
        auto_delete = db.get_setting("auto_delete")
        if auto_delete == "on":
            delete_time = int(db.get_setting("auto_delete_time") or 60)
            await asyncio.sleep(delete_time)
            await sent_message.delete()
    else:
        # No results found
        nrf_image = db.get_setting("nrf_image")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Search by Release Date", callback_data=f"nrf_date:{query}")],
            [InlineKeyboardButton("Request Admin to Add", callback_data=f"nrf_request:{query}")]
        ])
        
        if nrf_image and nrf_image.startswith("http"):
            await update.message.reply_photo(
                photo=nrf_image,
                caption=f"❌ No results found for: {query}",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                f"❌ No results found for: {query}",
                reply_markup=keyboard
            )

async def add_db_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Implementation for adding database channel
    # This would typically involve processing channel posts
    await update.message.reply_text("🚧 Feature in development - Adding DB channel")

async def remove_db_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Implementation for removing database channel
    await update.message.reply_text("🚧 Feature in development - Removing DB channel")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    total_users, total_searches = db.get_user_stats()
    status_text = (
        "📊 Bot Status\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🔍 Total Searches: {total_searches}\n"
        f"📂 Database Posts: {db.posts.count_documents({})}\n"
        f"🌐 Mode: {db.get_setting('mode')}\n"
        f"🗑️ Auto Delete: {db.get_setting('auto_delete') or 'off'}"
    )
    
    await update.message.reply_text(status_text)

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    await update.message.reply_text("Please send the message you want to broadcast:")
    return BROADCAST_MESSAGE

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_text = update.message.text
    users = db.users.find()
    
    success = 0
    fail = 0
    
    for user in users:
        try:
            await context.bot.send_message(user['user_id'], broadcast_text)
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"Failed to send message to {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"Broadcast completed!\n\n✅ Success: {success}\n❌ Failed: {fail}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Broadcast cancelled.")
    return ConversationHandler.END

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setmode <private/public>")
        return
    
    mode = context.args[0].lower()
    if mode not in ["private", "public"]:
        await update.message.reply_text("Invalid mode. Use 'private' or 'public'.")
        return
    
    db.update_setting("mode", mode)
    await update.message.reply_text(f"✅ Mode set to {mode}")

async def auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /autodelete <on/off> [time_in_seconds]")
        return
    
    state = context.args[0].lower()
    if state not in ["on", "off"]:
        await update.message.reply_text("Invalid state. Use 'on' or 'off'.")
        return
    
    if state == "on":
        if len(context.args) > 1:
            try:
                time = int(context.args[1])
                db.update_setting("auto_delete_time", str(time))
            except ValueError:
                await update.message.reply_text("Invalid time. Please provide a number.")
                return
        db.update_setting("auto_delete", "on")
        await update.message.reply_text("✅ Auto delete enabled")
    else:
        db.update_setting("auto_delete", "off")
        await update.message.reply_text("✅ Auto delete disabled")

async def set_nrf_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setnrfimage <image_url>")
        return
    
    image_url = context.args[0]
    db.update_setting("nrf_image", image_url)
    await update.message.reply_text("✅ No results found image updated")

async def set_private_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setprivatelink <channel_link>")
        return
    
    channel_link = context.args[0]
    db.update_setting("private_link", channel_link)
    await update.message.reply_text("✅ Private link updated")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    if data.startswith("nrf_request:"):
        search_query = data.split(":", 1)[1]
        request_id = db.add_admin_request(user.id, search_query)
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Reply to User", callback_data=f"reply_req:{request_id.inserted_id}:{user.id}")
                ]])
                await context.bot.send_message(
                    admin_id,
                    f"📥 New content request from {user.first_name} (@{user.username}):\n\n{search_query}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")
        
        await query.edit_message_caption(
            caption=f"✅ Your request has been sent to admins for: {search_query}"
        )
    
    elif data.startswith("reply_req:"):
        # Handle admin reply to request
        parts = data.split(":")
        request_id = parts[1]
        user_id = int(parts[2])
        
        # Store in context for the conversation
        context.user_data['replying_to'] = {'request_id': request_id, 'user_id': user_id}
        await query.message.reply_text("Please send your reply to the user:")
        # Note: You would need to implement a conversation handler for this

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("adddb", add_db_channel))
    application.add_handler(CommandHandler("removedb", remove_db_channel))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("setmode", set_mode))
    application.add_handler(CommandHandler("autodelete", auto_delete))
    application.add_handler(CommandHandler("setnrfimage", set_nrf_image))
    application.add_handler(CommandHandler("setprivatelink", set_private_link))
    
    # Broadcast conversation handler
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)]
    )
    application.add_handler(broadcast_conv)
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
