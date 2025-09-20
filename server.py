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
from celery_app import app as celery_app
from tasks import create_post_task, format_with_feedback_task, format_with_template_task


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

class CreatePostJobRequest(BaseModel):
    conversation_id: Optional[str] = None
    draft: str
    title: Optional[str] = None
    category: Optional[str] = None

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

@app.post("/templates/analyze")
async def analyze_template_content(request: dict):
    """AI-powered template content analysis (without saving)"""
    try:
        title = request.get('title', '')
        content = request.get('content', '')
        author = request.get('author', '')
        
        if not title and not content:
            raise HTTPException(status_code=400, detail="Title or content is required for analysis")
        
        # Prepare content for AI analysis
        content_to_analyze = f"""
Title: {title}
Content: {content}
Author: {author}
        """.strip()
        
        # Use OpenAI to analyze and categorize
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert content creator and marketing strategist. Analyze LinkedIn post templates and categorize them for a content funnel.

Your task:
1. Determine the primary funnel stage: attract, nurture, or convert
2. Identify the template format from these options:
   - attract: belief_shift, origin_story, industry_myths
   - nurture: framework, step_by_step, how_i_how_to  
   - convert: objection_post, result_breakdown, client_success_story
3. Generate up to 3 content creator tags that describe the template's approach

Return your analysis as JSON:
{
  "category": "attract|nurture|convert",
  "format": "specific_format_name",
  "tags": ["tag1", "tag2", "tag3"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of your categorization"
}

Focus on content creator insights and funnel positioning."""
                },
                {
                    "role": "user", 
                    "content": content_to_analyze
                }
            ],
            temperature=0.3
        )
        
        # Parse AI response
        ai_response = response.choices[0].message.content
        try:
            import json
            categorization = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            categorization = {
                "category": "nurture",
                "format": "framework", 
                "tags": ["content-analysis"],
                "confidence": 0.5,
                "reasoning": "AI analysis failed, using default categorization"
            }
        
        return {
            "categorization": categorization
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze template: {str(e)}")

@app.post("/templates/{template_id}/categorize")
async def categorize_template(template_id: str):
    """AI-powered template categorization and tagging"""
    try:
        # Get the template first
        template = store.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Prepare content for AI analysis
        content_to_analyze = f"""
Title: {template['title']}
Content: {template['content']}
Author: {template.get('author', 'Unknown')}
        """.strip()
        
        # Use OpenAI to analyze and categorize
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert content creator and marketing strategist. Analyze LinkedIn post templates and categorize them for a content funnel.

Your task:
1. Determine the primary funnel stage: attract, nurture, or convert
2. Identify the template format from these options:
   - attract: belief_shift, origin_story, industry_myths
   - nurture: framework, step_by_step, how_i_how_to  
   - convert: objection_post, result_breakdown, client_success_story
3. Generate up to 3 content creator tags that describe the template's approach

Return your analysis as JSON:
{
  "category": "attract|nurture|convert",
  "format": "specific_format_name",
  "tags": ["tag1", "tag2", "tag3"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of your categorization"
}

Focus on content creator insights and funnel positioning."""
                },
                {
                    "role": "user", 
                    "content": content_to_analyze
                }
            ],
            temperature=0.3
        )
        
        # Parse AI response
        ai_response = response.choices[0].message.content
        try:
            import json
            categorization = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            categorization = {
                "category": "nurture",
                "format": "framework", 
                "tags": ["content-analysis"],
                "confidence": 0.5,
                "reasoning": "AI analysis failed, using default categorization"
            }
        
        # Update the template with AI categorization
        updated_template = store.update_template_categorization(
            template_id=template_id,
            category=categorization.get('category', 'nurture'),
            format=categorization.get('format', 'framework'),
            ai_tags=categorization.get('tags', []),
            ai_categorized=True,
            categorization_confidence=categorization.get('confidence', 0.5)
        )
        
        return {
            "template_id": template_id,
            "categorization": categorization,
            "updated_template": updated_template
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to categorize template: {str(e)}")

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

# Background job endpoints
@app.post("/jobs/create-post")
async def create_post_job(request: CreatePostJobRequest):
    """Submit post creation as background job"""
    try:
        # Create a new conversation first
        conv = store.create_conversation(title=request.title or "Background Job Post")
        
        # Submit to Celery queue
        task = create_post_task.delay({
            'conversation_id': conv['id'],
            'user_request': request.draft,
            'title': request.title or "Background Job Post",
            'category': request.category or 'manual_post'
        })
        
        return {
            "job_id": task.id,
            "conversation_id": conv['id'],
            "status": "queued",
            "message": "Post creation job submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@app.post("/jobs/format-with-feedback")
async def format_with_feedback_job(request: FormatAgentRequest):
    """Submit feedback formatting as background job"""
    try:
        # Submit to Celery queue
        task = format_with_feedback_task.delay({
            'conversation_id': request.conversation_id,
            'draft': request.draft,
            'feedback': request.feedback,
            'format': request.format,
            'category': request.category
        })
        
        return {
            "job_id": task.id,
            "status": "queued",
            "message": "Feedback formatting job submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@app.post("/jobs/format-with-template")
async def format_with_template_job(request: FormatAgentRequest):
    """Submit template formatting as background job"""
    try:
        # Submit to Celery queue
        task = format_with_template_task.delay({
            'conversation_id': request.conversation_id,
            'draft': request.draft,
            'format': request.format,
            'category': request.category,
            'template_id': request.template_id
        })
        
        return {
            "job_id": task.id,
            "status": "queued",
            "message": "Template formatting job submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get the status of a background job"""
    try:
        # Check job status in Celery
        task = celery_app.AsyncResult(job_id)
        
        return {
            "job_id": job_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
            "info": task.info if hasattr(task, 'info') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

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
/create_post - Generate a LinkedIn post (simplified)
/post - Generate a LinkedIn post (advanced YAML)

**Simple Usage (Recommended):**
Send /create_post followed by URL and your notes:

```
/create_post https://example.com/article
This is amazing! I learned that...
```

**Advanced Usage:**
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
/create_post https://read.readwise.io/new/read/01k56vzpz8cz9zncnsj2drsqer
This article shows how insurance leaders can get real-time loss updates. Key insight: automation reduces response time by 70%.
```
        """
        bot.reply_to(message, welcome_text, parse_mode='Markdown')
    
    @bot.message_handler(commands=['create_post'])
    def handle_create_post_command(message):
        """Simplified command: just URL + notes, AI picks template"""
        try:
            # Extract URL and notes from message
            text = message.text.replace('/create_post', '').strip()
            
            if not text:
                bot.reply_to(message, "❌ Please provide URL and your notes after /create_post command")
                return
            
            # Send processing message
            processing_msg = bot.reply_to(message, "🔄 Analyzing article and finding best template...")
            
            # Create conversation and process with simplified input
            conv = store.create_conversation(title="Telegram Generated Post")
            
            # Let AI determine category and format automatically
            simplified_input = f"""
- url: {text}
- notes: {text}
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
                    "❌ Failed to generate post. Please try again.",
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id
                )
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")

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


