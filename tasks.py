"""
Celery tasks for background AI processing
"""
import os
from celery import Celery
from src.tools.chat_store import Coordinator

# Initialize Celery app
from celery_app import app

# Initialize Coordinator for AI operations (will be created in each task)
def get_coordinator():
    """Get a properly initialized Coordinator instance"""
    from src.tools.chat_store import ChatStore, Coordinator
    from openai import OpenAI
    
    # Create ChatStore and OpenAI client
    store = ChatStore()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    return Coordinator(store=store, client=client)

@app.task(bind=True, name='celery_app.create_post_task')
def create_post_task(self, request_data):
    """
    Background task for creating posts
    
    Args:
        request_data (dict): Contains conversation_id, user_request, title, category
    """
    try:
        print(f"🚀 Starting create_post_task: {self.request.id}")
        
        # Extract data
        conversation_id = request_data.get('conversation_id')
        user_request = request_data.get('user_request')
        title = request_data.get('title')
        category = request_data.get('category', 'manual_post')
        
        # Update task status
        self.update_state(state='PROCESSING', meta={'status': 'Creating post...'})
        
        # Get coordinator instance and call existing AI logic
        coordinator = get_coordinator()
        result = coordinator.start_conversation(
            conversation_id=conversation_id,
            user_request=user_request,
            title=title,
            category=category
        )
        
        print(f"✅ Completed create_post_task: {self.request.id}")
        return {
            'status': 'completed',
            'result': result,
            'message': 'Post created successfully'
        }
        
    except Exception as exc:
        print(f"❌ Error in create_post_task: {self.request.id} - {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@app.task(bind=True, name='celery_app.format_with_feedback_task')
def format_with_feedback_task(self, request_data):
    """
    Background task for formatting content with feedback
    
    Args:
        request_data (dict): Contains conversation_id, draft, feedback, format, etc.
    """
    try:
        print(f"🚀 Starting format_with_feedback_task: {self.request.id}")
        
        # Extract data
        conversation_id = request_data.get('conversation_id')
        draft = request_data.get('draft')
        feedback = request_data.get('feedback')
        format_type = request_data.get('format', 'general')
        category = request_data.get('category')
        
        # Update task status
        self.update_state(state='PROCESSING', meta={'status': 'Processing feedback...'})
        
        # Get coordinator instance and call existing AI logic
        coordinator = get_coordinator()
        result = coordinator._call_format_agent_with_feedback(
            conversation_id=conversation_id,
            draft=draft,
            feedback=feedback,
            category=category,
            format=format_type
        )
        
        print(f"✅ Completed format_with_feedback_task: {self.request.id}")
        return {
            'status': 'completed',
            'result': result,
            'message': 'Content formatted successfully'
        }
        
    except Exception as exc:
        print(f"❌ Error in format_with_feedback_task: {self.request.id} - {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@app.task(bind=True, name='celery_app.format_with_template_task')
def format_with_template_task(self, request_data):
    """
    Background task for formatting content with template
    
    Args:
        request_data (dict): Contains conversation_id, draft, format, category, etc.
    """
    try:
        print(f"🚀 Starting format_with_template_task: {self.request.id}")
        
        # Extract data
        conversation_id = request_data.get('conversation_id')
        draft = request_data.get('draft')
        format_type = request_data.get('format')
        category = request_data.get('category')
        template_id = request_data.get('template_id')
        
        # Update task status
        self.update_state(state='PROCESSING', meta={'status': 'Applying template...'})
        
        # Get coordinator instance and call existing AI logic
        coordinator = get_coordinator()
        result = coordinator._call_format_agent(
            conversation_id=conversation_id,
            draft=draft,
            category=category,
            format=format_type,
            template_id=template_id
        )
        
        print(f"✅ Completed format_with_template_task: {self.request.id}")
        return {
            'status': 'completed',
            'result': result,
            'message': 'Content formatted with template successfully'
        }
        
    except Exception as exc:
        print(f"❌ Error in format_with_template_task: {self.request.id} - {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60, max_retries=3)
