import os
import uuid
from typing import Any, Dict, Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import telebot
import asyncio
import threading
import redis

from src.tools.chat_store import ChatStore, Coordinator


load_dotenv()

# Get port from environment variable, default to 8000
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(title="Standalone Chat Coordinator API")

# CORS for local Next.js dev and Vercel deployment
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://linkedin-content-generator-sand.vercel.app",
    "https://*.vercel.app",  # Allow all Vercel preview deployments
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = ChatStore()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
coordinator = Coordinator(store, client)


class StartRequest(BaseModel):
    user_request: str
    conversation_title: str | None = None
    category: str | None = None  # attract, nurture, convert


class ContinueRequest(BaseModel):
    conversation_id: str
    user_response: str

class FormatAgentRequest(BaseModel):
    conversation_id: str
    draft: str
    template_id: Optional[str] = None
    category: Optional[str] = None
    format: Optional[str] = None
    feedback: Optional[str] = None

class TemplateRequest(BaseModel):
    title: str
    content: str
    category: str
    format: str
    author: Optional[str] = None
    linkedin_url: Optional[str] = None
    tags: Optional[List[str]] = None
    screenshot_url: Optional[str] = None


@app.post("/coordinator/start")
def start(req: StartRequest) -> Dict[str, Any]:
    try:
        conv = store.create_conversation(title=req.conversation_title or "New conversation")
        result = coordinator.process_request(req.user_request, conv["id"], req.category)
        return {"conversation_id": conv["id"], **result}
    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/coordinator/continue")
def continue_(req: ContinueRequest) -> Dict[str, Any]:
    try:
        result = coordinator.continue_after_user_input(req.conversation_id, req.user_response)
        return {"conversation_id": req.conversation_id, **result}
    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/format-agent/transform")
def format_agent_transform(req: FormatAgentRequest) -> Dict[str, Any]:
    try:
        print(f"🔧 Format Agent Transform Request: {req.category}/{req.format}")
        
        if req.feedback:
            content = coordinator._call_format_agent_with_feedback(  # noqa: SLF001
                req.conversation_id,
                req.draft,
                req.feedback,
                template_id=req.template_id,
                category=req.category,
                format=req.format,
            )
        else:
            content = coordinator._call_format_agent(  # noqa: SLF001
                req.conversation_id,
                req.draft,
                template_id=req.template_id,
                category=req.category,
                format=req.format,
            )
        
        print(f"✅ Format Agent completed: {len(content)} characters")
        return {"conversation_id": req.conversation_id, "content": content}
    except Exception as e:  # pylint: disable=broad-except
        print(f"❌ Format Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template endpoints
@app.get("/templates")
async def get_templates(category: Optional[str] = None, format: Optional[str] = None):
    try:
        templates = store.get_templates(category=category, format=format)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/templates")
async def create_template(req: TemplateRequest):
    try:
        template = store.create_template(
            title=req.title,
            content=req.content,
            category=req.category,
            format=req.format,
            author=req.author,
            linkedin_url=req.linkedin_url,
            tags=req.tags,
            screenshot_url=req.screenshot_url
        )
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    try:
        template = store.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    try:
        success = store.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-redis")
async def test_redis():
    """Test Redis connection"""
    try:
        # Try different Redis URL environment variables (prioritize public URL)
        redis_url = os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_URL") or os.getenv("REDIS_PRIVATE_URL")
        if not redis_url:
            return {"error": "No Redis URL found in environment variables"}
        
        # Show all available Redis URLs for debugging
        all_redis_urls = {
            "REDIS_PUBLIC_URL": os.getenv("REDIS_PUBLIC_URL"),
            "REDIS_URL": os.getenv("REDIS_URL"),
            "REDIS_PRIVATE_URL": os.getenv("REDIS_PRIVATE_URL")
        }
        
        print(f"Attempting to connect to Redis: {redis_url}")
        
        r = redis.from_url(redis_url)
        # Test basic operations
        r.set("test_key", "test_value", ex=10)  # Expire in 10 seconds
        value = r.get("test_key")
        
        return {
            "status": "success",
            "redis_url": redis_url,
            "test_value": value.decode() if value else None,
            "message": "Redis connection successful",
            "available_urls": all_redis_urls
        }
    except Exception as e:
        return {
            "error": f"Redis connection failed: {str(e)}", 
            "redis_url": redis_url,
            "available_urls": all_redis_urls
        }

# Image upload endpoint
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Upload to Supabase Storage
        file_content = await file.read()
        
        # Get Supabase client from ChatStore
        supabase_client = store.client
        
        # Upload to storage bucket 'templates'
        response = supabase_client.storage.from_('templates').upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Check for upload errors
        if hasattr(response, 'error') and response.error:
            raise HTTPException(status_code=500, detail=f"Upload failed: {response.error}")
        
        # Get public URL
        public_url = supabase_client.storage.from_('templates').get_public_url(unique_filename)
        
        return {
            "filename": unique_filename,
            "public_url": public_url,
            "message": "Image uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Telegram Bot Integration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Only start Telegram bot in production (not in local development)
if TELEGRAM_BOT_TOKEN and os.getenv("ENVIRONMENT") == "production":
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        welcome_text = """
🤖 **LinkedIn Content Generator Bot**

**Commands:**
/post - Generate a LinkedIn post

**Usage:**
Send /post followed by your YAML input:

```
/post
- url: https://read.readwise.io/new/read/...
- icp: target audience
- dream: desired outcome  
- category: attract|nurture|convert
- format: belief_shift|framework|how_to|etc
```

**Example:**
```
/post
- url: https://read.readwise.io/new/read/01k56vzpz8cz9zncnsj2drsqer
- icp: insurance leaders
- dream: real time losses updates
- category: nurture
- format: how to
```
        """
        bot.reply_to(message, welcome_text, parse_mode='Markdown')
    
    @bot.message_handler(commands=['post'])
    def handle_post_command(message):
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
                # Split long messages if needed
                output = result["final_output"]
                if len(output) > 4000:
                    # Split into chunks
                    chunks = [output[i:i+4000] for i in range(0, len(output), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            bot.edit_message_text(
                                f"✅ **Generated LinkedIn Post:**\n\n{chunk}",
                                chat_id=message.chat.id,
                                message_id=processing_msg.message_id,
                                parse_mode='Markdown'
                            )
                        else:
                            bot.send_message(message.chat.id, chunk)
                else:
                    bot.edit_message_text(
                        f"✅ **Generated LinkedIn Post:**\n\n{output}",
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id,
                        parse_mode='Markdown'
                    )
            else:
                bot.edit_message_text(
                    "❌ Failed to generate post. Please check your YAML format.",
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id
                )
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
    
    def start_telegram_bot():
        """Start the Telegram bot in a separate thread"""
        try:
            print("🤖 Starting Telegram bot...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Telegram bot error: {e}")
    
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    print("✅ Telegram bot started in background")

elif TELEGRAM_BOT_TOKEN:
    print("⚠️  Telegram bot disabled in local development (set ENVIRONMENT=production to enable)")
else:
    print("⚠️  TELEGRAM_BOT_TOKEN not found in environment variables")


