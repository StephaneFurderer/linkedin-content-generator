"""
Telegram Bot Integration - Webhook-based for Production
Supports the 12-pillar content generation workflow
"""
import os
import re
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
import telebot
from telebot import types

from src.tools.chat_store import ChatStore, Coordinator
from openai import OpenAI


# Create router for Telegram webhook
telegram_router = APIRouter(prefix="/telegram", tags=["telegram"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")  # e.g., https://your-app.railway.app

if TELEGRAM_BOT_TOKEN:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
    
    # Initialize dependencies
    store = ChatStore()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    coordinator = Coordinator(store, client)
else:
    bot = None
    store = None
    coordinator = None


def setup_webhook(webhook_url: str) -> bool:
    """Set up webhook for Telegram bot"""
    if not bot or not webhook_url:
        return False
    
    try:
        # Remove any existing webhook
        bot.remove_webhook()
        
        # Set new webhook
        success = bot.set_webhook(url=f"{webhook_url}/telegram/webhook")
        
        if success:
            print(f"✅ Telegram webhook set to: {webhook_url}/telegram/webhook")
            # Get webhook info
            webhook_info = bot.get_webhook_info()
            print(f"📊 Webhook info: URL={webhook_info.url}, Pending={webhook_info.pending_update_count}")
        else:
            print("❌ Failed to set Telegram webhook")
        
        return success
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False


def remove_webhook() -> bool:
    """Remove webhook (useful for local development to switch back to polling)"""
    if not bot:
        return False
    
    try:
        bot.remove_webhook()
        print("✅ Telegram webhook removed")
        return True
    except Exception as e:
        print(f"❌ Error removing webhook: {e}")
        return False


@telegram_router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Handle incoming Telegram updates via webhook
    """
    if not bot:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        # Get the update from Telegram
        json_data = await request.json()
        update = telebot.types.Update.de_json(json_data)
        
        # Process the update
        bot.process_new_updates([update])
        
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Error processing Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@telegram_router.get("/webhook-info")
async def get_webhook_info():
    """Get current webhook information"""
    if not bot:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        webhook_info = bot.get_webhook_info()
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates,
        }
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@telegram_router.post("/setup-webhook")
async def setup_webhook_endpoint(request: Request):
    """Manually setup webhook (useful for deployment)"""
    if not bot:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    data = await request.json()
    webhook_url = data.get("webhook_url") or WEBHOOK_URL
    
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url is required")
    
    success = setup_webhook(webhook_url)
    
    if success:
        return {"status": "success", "webhook_url": f"{webhook_url}/telegram/webhook"}
    else:
        raise HTTPException(status_code=500, detail="Failed to setup webhook")


# Message Handlers
if bot and coordinator and store:
    
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        welcome_text = """🤖 LinkedIn Content Generator Bot

Commands:
/ideas - 🎨 Generate 12 content ideas from Readwise (NEW!)
/select - 📝 Generate full article from selected idea
/create_post - Generate a LinkedIn post (simplified)
/post - Generate a LinkedIn post (advanced YAML)

🎨 12-Pillar Workflow (Recommended for Readwise):

1. Generate 12 ideas:
/ideas https://read.readwise.io/new/read/01abc123...

2. Select an idea to expand:
/select <conversation_id> 3

This gives you 12 strategic content angles (Attract, Nurture, Convert) to choose from!

Simple Direct Post:
Send /create_post followed by URL and your notes:

/create_post https://example.com/article
This is amazing! I learned that...

Target audience: Insurance leaders, C-level executives, data leaders, financial services

Advanced YAML:
Send /post followed by your YAML input:

/post
- url: https://example.com/article
- icp: target audience
- dream: desired outcome
- category: attract|nurture|convert
- format: belief_shift|framework|how_to|etc
"""
        bot.reply_to(message, welcome_text)
    
    @bot.message_handler(commands=['ideas'])
    def handle_ideas_command(message):
        """NEW: Generate 12 content ideas from a Readwise URL"""
        try:
            # Extract URL from message
            text = message.text.replace('/ideas', '').strip()
            
            # Check if it's a Readwise URL
            readwise_pattern = r'https?://(?:www\.)?(?:read\.)?readwise\.io/(?:new/)?(?:read|reader/shared)/[\w-]+'
            readwise_match = re.search(readwise_pattern, text)
            
            if not readwise_match:
                bot.reply_to(message, "❌ Please provide a Readwise URL after /ideas command\n\nExample: /ideas https://read.readwise.io/new/read/01abc123...")
                return
            
            readwise_url = readwise_match.group(0)
            
            # Send processing message
            processing_msg = bot.reply_to(message, "🎨 Generating 12 content ideas from your article...")
            
            # Create conversation
            conv = store.create_conversation(title=f"12 Ideas from Readwise")
            
            # Generate 12 ideas using new workflow
            result = coordinator.generate_ideas(readwise_url, conv["id"])
            
            if result.get("ideas"):
                ideas = result["ideas"]["ideas"]
                
                # Format ideas message
                ideas_text = f"✅ **Generated 12 Content Ideas!**\n\n"
                ideas_text += f"📖 Source: {result['ideas']['source_title']}\n\n"
                ideas_text += "**Select an idea to expand into a full post:**\n\n"
                
                for i, idea in enumerate(ideas, 1):
                    ideas_text += f"**{i}. {idea['pillar_type']}** ({idea['pillar_category']})\n"
                    ideas_text += f"💡 {idea['content_idea'][:100]}...\n\n"
                
                ideas_text += f"\n🔗 View all ideas in the UI:\nhttps://linkedin-content-generator-sand.vercel.app\n"
                ideas_text += f"📋 Conversation ID: {conv['id']}\n"
                ideas_text += f"\n💬 To generate a post from idea #3, reply with:\n/select {conv['id']} 3"
                
                # Send ideas
                if len(ideas_text) > 4000:
                    chunks = [ideas_text[i:i+4000] for i in range(0, len(ideas_text), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            bot.edit_message_text(chunk, chat_id=message.chat.id, message_id=processing_msg.message_id)
                        else:
                            bot.send_message(message.chat.id, chunk)
                else:
                    bot.edit_message_text(ideas_text, chat_id=message.chat.id, message_id=processing_msg.message_id)
            else:
                bot.edit_message_text("❌ Failed to generate ideas. Please try again.", chat_id=message.chat.id, message_id=processing_msg.message_id)
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
    
    @bot.message_handler(commands=['select'])
    def handle_select_command(message):
        """Select an idea and generate full article"""
        import time
        
        try:
            # Parse: /select <conversation_id> <idea_index>
            parts = message.text.replace('/select', '').strip().split()
            
            if len(parts) < 2:
                bot.reply_to(message, "❌ Usage: /select <conversation_id> <idea_number>\n\nExample: /select abc123 3")
                return
            
            conv_id = parts[0]
            idea_index = int(parts[1]) - 1  # Convert to 0-indexed
            
            # Validate conversation ID format
            if not conv_id or len(conv_id) < 3:
                bot.reply_to(message, "❌ Invalid conversation ID. Please check the ID and try again.")
                return
            
            # Send processing message with timeout info
            processing_msg = bot.reply_to(message, f"📝 Generating full article from idea #{idea_index + 1}...\n⏱️ This may take up to 5 minutes")
            
            # Track start time
            start_time = time.time()
            max_duration = 300  # 5 minutes max
            
            try:
                # Generate article from selected idea with timeout protection
                result = coordinator.generate_from_idea(conv_id, idea_index)
                
                # Check if we're still within timeout
                if time.time() - start_time > max_duration:
                    bot.edit_message_text(
                        "⏰ Generation timed out after 5 minutes. Please try again with a different idea or contact support.",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                    return
                
                if result.get("final_output"):
                    output = result["final_output"]
                    generation_time = result.get("generation_time", time.time() - start_time)
                    
                    # Add metadata
                    selected_idea = result.get("selected_idea", {})
                    header = f"✅ **Generated from Idea #{idea_index + 1}**\n"
                    header += f"📌 {selected_idea.get('pillar_type', 'N/A')}\n"
                    header += f"⏱️ Generated in {generation_time:.1f}s\n\n"
                    
                    full_output = header + output
                    
                    # Send result
                    if len(full_output) > 4000:
                        chunks = [full_output[i:i+4000] for i in range(0, len(full_output), 4000)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                bot.edit_message_text(chunk, chat_id=message.chat.id, message_id=processing_msg.message_id)
                            else:
                                bot.send_message(message.chat.id, chunk)
                    else:
                        bot.edit_message_text(full_output, chat_id=message.chat.id, message_id=processing_msg.message_id)
                else:
                    bot.edit_message_text(
                        "❌ Failed to generate article. Please try again with a different idea.",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                    
            except TimeoutError:
                bot.edit_message_text(
                    "⏰ Generation timed out. Please try again with a different idea.",
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id
                )
            except ValueError as e:
                # Handle specific validation errors
                error_msg = str(e)
                if "No ideas found" in error_msg:
                    bot.edit_message_text(
                        "❌ No ideas found for this conversation. Please generate ideas first using /ideas command.",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                elif "Invalid idea index" in error_msg:
                    bot.edit_message_text(
                        f"❌ {error_msg}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                else:
                    bot.edit_message_text(
                        f"❌ Validation error: {error_msg}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
            except Exception as e:
                # Handle other errors
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    bot.edit_message_text(
                        "⏰ Generation timed out. Please try again.",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                else:
                    bot.edit_message_text(
                        f"❌ Error generating article: {error_msg}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
                
        except ValueError as e:
            # Handle parsing errors
            bot.reply_to(message, f"❌ Invalid input: {str(e)}\n\nUsage: /select <conversation_id> <idea_number>\nExample: /select abc123 3")
        except Exception as e:
            # Handle unexpected errors
            bot.reply_to(message, f"❌ Unexpected error: {str(e)}")
    
    @bot.message_handler(commands=['create_post'])
    def handle_create_post_command(message):
        """Simplified command: just URL + notes, AI picks template"""
        try:
            # Extract URL and notes from message
            text = message.text.replace('/create_post', '').strip()
            
            if not text:
                bot.reply_to(message, "❌ Please provide URL and your notes after /create_post command")
                return
            
            # Check if it's a Readwise URL - use new workflow
            readwise_pattern = r'https?://(?:www\.)?(?:read\.)?readwise\.io/(?:new/)?(?:read|reader/shared)/[\w-]+'
            if re.search(readwise_pattern, text):
                bot.reply_to(message, "💡 Detected Readwise URL! Use /ideas command for the 12-pillar workflow:\n\n/ideas " + text)
                return
            
            # Send processing message
            processing_msg = bot.reply_to(message, "🔄 Analyzing article and finding best template...")
            
            # Generate a meaningful title from the article URL and user notes
            try:
                # Extract domain/article info for title generation
                url_match = re.search(r'https?://([^/]+)', text)
                domain = url_match.group(1) if url_match else "Article"
                
                # Create a title based on URL and notes (first 50 chars of notes)
                notes_preview = text.split('\n', 1)[1] if '\n' in text else text
                notes_preview = notes_preview[:50] + "..." if len(notes_preview) > 50 else notes_preview
                
                generated_title = f"Post from {domain}: {notes_preview}"
            except:
                generated_title = "Telegram Generated Post"
            
            # Create conversation with generated title
            conv = store.create_conversation(title=generated_title)
            
            # Let AI determine category and format automatically
            simplified_input = f"""
- url: {text}
- notes: {text}
- icp: insurance leaders, chief insurance officers, data leaders, financial services executives
- dream: improved operational efficiency, better risk management, data-driven decision making
- auto_categorize: true
- auto_format: true
"""
            
            result = coordinator.process_request(simplified_input, conv["id"])
            
            # Send result
            if result.get("final_output"):
                output = result["final_output"]
                if len(output) > 4000:
                    chunks = [output[i:i+4000] for i in range(0, len(output), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            bot.edit_message_text(
                                f"✅ **Generated LinkedIn Post:**\n\n{chunk}",
                                chat_id=message.chat.id,
                                message_id=processing_msg.message_id
                            )
                        else:
                            bot.send_message(message.chat.id, chunk)
                else:
                    bot.edit_message_text(
                        f"✅ **Generated LinkedIn Post:**\n\n{output}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
            else:
                bot.edit_message_text(
                    "❌ Failed to generate post. Please try again.",
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id
                )
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
    
    @bot.message_handler(commands=['post'])
    def handle_post_command(message):
        """Advanced command: Full YAML control"""
        try:
            # Extract YAML from message
            yaml_input = message.text.replace('/post', '').strip()
            
            if not yaml_input:
                bot.reply_to(message, "❌ Please provide YAML input after /post command")
                return
            
            # Send processing message
            processing_msg = bot.reply_to(message, "🔄 Processing your request...")
            
            # Create conversation and process
            conv = store.create_conversation(title="Telegram Generated Post")
            result = coordinator.process_request(yaml_input, conv["id"])
            
            # Send result
            if result.get("final_output"):
                output = result["final_output"]
                if len(output) > 4000:
                    chunks = [output[i:i+4000] for i in range(0, len(output), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            bot.edit_message_text(
                                f"✅ **Generated LinkedIn Post:**\n\n{chunk}",
                                chat_id=message.chat.id,
                                message_id=processing_msg.message_id
                            )
                        else:
                            bot.send_message(message.chat.id, chunk)
                else:
                    bot.edit_message_text(
                        f"✅ **Generated LinkedIn Post:**\n\n{output}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id
                    )
            else:
                bot.edit_message_text(
                    "❌ Failed to generate post. Please check your YAML format.",
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id
                )
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")

