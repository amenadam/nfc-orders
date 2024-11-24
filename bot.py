from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from telegram.ext import ContextTypes
import pymongo
from pymongo import MongoClient
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# 

# Enable logging for debugging purposes
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_URI)  # Replace with your MongoDB connection string
db = client['your_database_name']  # Specify your database name here
users_collection = db.users
orders_collection = db.orders

# States for conversation
ORDER, NAME, EMAIL, PHONE, SHIPPING_ADDRESS = range(5)

# Start command to register the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    # Check if the user is already registered
    user = users_collection.find_one({"user_id": user_id})
    
    if user:
        await update.message.reply_text("Welcome back! You are already registered.")
    else:
        await update.message.reply_text("Hello! Welcome to ACELINKS V-card providing service. To get started, please enter your name to register.")
        return NAME

# Handle user registration
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    name = update.message.text
    context.user_data['name'] = name

    await update.message.reply_text(f"Thank you, {name}. Now, please provide your email address.")
    return EMAIL

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    context.user_data['email'] = email

    await update.message.reply_text(f"Thank you for providing your email: {email}. Please enter your phone number.")
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data['phone'] = phone

    await update.message.reply_text(f"Thank you for providing your phone number: {phone}. Now, please provide your shipping address.")
    return SHIPPING_ADDRESS

async def shipping_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shipping_address = update.message.text
    context.user_data['shipping_address'] = shipping_address

    user_id = update.message.from_user.id
    name = context.user_data['name']
    email = context.user_data['email']
    phone = context.user_data['phone']
    shipping_address = context.user_data['shipping_address']

    # Insert the order into MongoDB
    order_reference = f"ORD{user_id}{orders_collection.count_documents({}) + 1}"  # Create a unique order reference
    orders_collection.insert_one({
        "order_reference": order_reference,
        "user_id": user_id,
        "name": name,
        "email": email,
        "phone": phone,
        "shipping_address": shipping_address,
        "status": "Pending"  # Default status
    })

    await update.message.reply_text(f"Your order has been successfully placed!\n\n"
                                  f"Order Reference: {order_reference}\n"
                                  f"Name: {name}\n"
                                  f"Email: {email}\n"
                                  f"Phone: {phone}\n"
                                  f"Shipping Address: {shipping_address}\n"
                                  f"Status: Pending\n\n"
                                  "You will be notified once the status of your order changes.\n "
                                  "To see your order status /orderstatus")
    return ConversationHandler.END

# Place order function
async def place_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    if not user:
        await update.message.reply_text("You must be registered first. Please use /start to register.")
        return

    # Start the order process
    await update.message.reply_text("Let's start with your order. Please provide your name.")
    return NAME

# Admin can change order status
async def change_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user is admin (replace 655484188 with your admin user ID)
    if update.message.from_user.id == 655484188:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /change_status <order_reference> <new_status>")
            return

        order_reference = context.args[0]
        new_status = context.args[1]

        # Update the order status in MongoDB
        order = orders_collection.find_one({"order_reference": order_reference})

        if order:
            # Update the status of the order
            orders_collection.update_one({"order_reference": order_reference}, {"$set": {"status": new_status}})
            
            # Notify the user who placed the order
            user_chat_id = order['user_id']
            await update.message.reply_text(f"Order {order_reference} status updated to {new_status}.")
            
            # Send a notification to the user who placed the order (await this call)
            await context.bot.send_message(user_chat_id, f"Your order {order_reference} status has been updated to {new_status}.")
        else:
            await update.message.reply_text(f"No order found with reference {order_reference}.")
    else:
        await update.message.reply_text("You are not authorized to change the order status.")

# Admin command to check order status
async def order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    order = orders_collection.find_one({"user_id": user_id})

    if order:
        order_reference = order['order_reference']
        status = order['status']
        await update.message.reply_text(f"Your most recent order {order_reference} is currently {status}.")
    else:
        await update.message.reply_text("You have no orders placed.")

# Create the application and set up handlers
def main():
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler for user registration and placing orders
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT, name)],
            EMAIL: [MessageHandler(filters.TEXT, email)],
            PHONE: [MessageHandler(filters.TEXT, phone)],
            SHIPPING_ADDRESS: [MessageHandler(filters.TEXT, shipping_address)],
        },
        fallbacks=[],
    )

    # Register handlers
    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("place_order", place_order))
    application.add_handler(CommandHandler("change_status", change_order_status))
    application.add_handler(CommandHandler("orderstatus", order_status))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
