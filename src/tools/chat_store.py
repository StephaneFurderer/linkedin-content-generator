import os
import re
import requests
from typing import Dict, List, Optional
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client
from openai import OpenAI
from .readwise_client import ReadwiseClient, ReadwiseDocument

load_dotenv()


def _create_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/ANON_KEY env vars")
    return create_client(url, key)


class ChatStore:
    def __init__(self, client: Optional[Client] = None) -> None:
        self.client: Client = client or _create_client()
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Conversations
    def create_conversation(self, title: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        row = {"title": title, "user_id": user_id}
        res = self.client.table("conversations").insert(row).execute()
        return res.data[0]

    def archive_conversation(self, conversation_id: str) -> Dict[str, Any]:
        res = (
            self.client.table("conversations")
            .update({"status": "archived"})
            .eq("id", conversation_id)
            .execute()
        )
        return res.data[0] if res.data else {}

    def list_conversations(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        q = self.client.table("conversations").select("*").order("created_at", desc=True).limit(limit)
        if user_id:
            q = q.eq("user_id", user_id)
        res = q.execute()
        return res.data

    # Messages
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        row = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "user_id": user_id,
            "agent_name": agent_name,
            "metadata": metadata or {},
        }
        res = self.client.table("messages").insert(row).execute()
        return res.data[0]

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        before_iso: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = (
            self.client.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before_iso:
            q = q.lt("created_at", before_iso)
        res = q.execute()
        return list(reversed(res.data))

    # State management
    def get_conversation_state(self, conversation_id: str) -> Dict[str, Any]:
        """Get the current state of a conversation"""
        res = self.client.table("conversations").select("state").eq("id", conversation_id).single().execute()
        return res.data.get("state", {}) if res.data else {}

    def update_conversation_state(self, conversation_id: str, state_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update conversation state (merges with existing state)"""
        current_state = self.get_conversation_state(conversation_id)
        new_state = {**current_state, **state_updates}
        
        res = self.client.table("conversations").update({"state": new_state}).eq("id", conversation_id).execute()
        return res.data[0] if res.data else {}

    # Summary management
    def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        res = self.client.table("conversations").select("summary").eq("id", conversation_id).single().execute()
        return res.data.get("summary") if res.data else None

    def update_running_summary(self, conversation_id: str, recent_turns: int = 200) -> Optional[str]:
        """Summarize recent messages and store to conversations.summary"""
        messages = self.get_messages(conversation_id, limit=recent_turns)
        if not messages:
            return None

        transcript = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        prompt = [
            {"role": "system", "content": "Summarize key facts, decisions, and user preferences. Be concise."},
            {"role": "user", "content": transcript[:12000]}
        ]
        res = self.llm.chat.completions.create(model="gpt-5-mini", messages=prompt)
        summary = res.choices[0].message.content

        self.client.table("conversations").update({"summary": summary}).eq("id", conversation_id).execute()
        return summary

    # System prompts management
    def get_system_prompt(self, agent_name: str, version: Optional[str] = None) -> Optional[str]:
        """Get system prompt for agent. If version is None, gets current version."""
        if version:
            res = self.client.table("system_prompts").select("prompt").eq("agent_name", agent_name).eq("version", version).single().execute()
        else:
            res = self.client.table("system_prompts").select("prompt").eq("agent_name", agent_name).eq("is_current", True).single().execute()
        return res.data.get("prompt") if res.data else None

    def get_current_prompt_version(self, agent_name: str) -> Optional[str]:
        """Get the current version string for an agent's system prompt."""
        res = self.client.table("system_prompts").select("version").eq("agent_name", agent_name).eq("is_current", True).single().execute()
        return res.data.get("version") if res.data else None

    def set_system_prompt(self, agent_name: str, prompt: str, version: str, set_as_current: bool = True) -> Dict[str, Any]:
        """Set system prompt for agent. If set_as_current=True, marks as current and unmarks others."""
        # Insert new prompt
        res = self.client.table("system_prompts").insert({
            "agent_name": agent_name,
            "version": version,
            "prompt": prompt,
            "is_current": set_as_current
        }).execute()
        
        # If setting as current, unmark other versions
        if set_as_current:
            self.client.table("system_prompts").update({"is_current": False}).eq("agent_name", agent_name).neq("version", version).execute()
        
        return res.data[0] if res.data else {}

    # Context builder
    def build_context_for_agent(self, conversation_id: str, agent_name: str, recent_turns: int = 30) -> List[Dict[str, str]]:
        """Build context using stored system prompt for agent"""
        messages: List[Dict[str, str]] = []
        summary = self.get_conversation_summary(conversation_id)
        if summary:
            messages.append({"role": "system", "content": f"Conversation summary:\n{summary}"})
        
        # Get agent's system prompt from DB
        agent_prompt = self.get_system_prompt(agent_name)
        if agent_prompt:
            messages.append({"role": "system", "content": agent_prompt})
        
        recent = self.get_messages(conversation_id, limit=recent_turns)
        messages.extend({"role": m["role"], "content": m["content"]} for m in recent)
        return messages

    # Content Templates
    def create_template(
        self,
        title: str,
        content: str,
        category: str,
        format: str,
        author: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        screenshot_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new content template."""
        row = {
            "title": title,
            "content": content,
            "category": category,
            "format": format,
            "author": author,
            "linkedin_url": linkedin_url,
            "tags": tags or [],
            "screenshot_url": screenshot_url,
        }
        res = self.client.table("content_templates").insert(row).execute()
        return res.data[0]

    def get_templates(
        self,
        category: Optional[str] = None,
        format: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get templates with optional filtering."""
        q = self.client.table("content_templates").select("*").order("created_at", desc=True).limit(limit)
        if category:
            q = q.eq("category", category)
        if format:
            q = q.eq("format", format)
        res = q.execute()
        return res.data

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        res = self.client.table("content_templates").select("*").eq("id", template_id).single().execute()
        return res.data if res.data else None

    def get_latest_template_by_category_format(
        self,
        category: str,
        format: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent template for a category/format pair."""
        res = (
            self.client
            .table("content_templates")
            .select("*")
            .eq("category", category)
            .eq("format", format)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None

    def update_template(
        self,
        template_id: str,
        **updates: Any
    ) -> Optional[Dict[str, Any]]:
        """Update a template."""
        res = self.client.table("content_templates").update(updates).eq("id", template_id).execute()
        return res.data[0] if res.data else None

    def update_template_categorization(
        self,
        template_id: str,
        category: str,
        format: str,
        ai_tags: List[str],
        ai_categorized: bool = True,
        categorization_confidence: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """Update template categorization with AI analysis results."""
        updates = {
            "category": category,
            "format": format,
            "ai_tags": ai_tags[:3],  # Limit to 3 tags
            "ai_categorized": ai_categorized,
            "categorization_confidence": min(max(categorization_confidence, 0.0), 1.0),  # Clamp between 0 and 1
            "custom_category": category not in ['attract', 'nurture', 'convert'],
            "custom_format": format not in [
                # Attract
                'transformation', 'misconception', 'belief_shift', 'hidden_truth',
                # Nurture
                'step_by_step', 'faq_answer', 'process_breakdown', 'quick_win',
                # Convert
                'client_fix', 'case_study', 'objection_reframe', 'client_quote'
            ]
        }
        
        res = self.client.table("content_templates").update(updates).eq("id", template_id).execute()
        return res.data[0] if res.data else None

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        res = self.client.table("content_templates").delete().eq("id", template_id).execute()
        return len(res.data) > 0

    # Readwise Content Retrieval
    def extract_readwise_url(self, text: str) -> Optional[str]:
        """Extract Readwise URL from text if present."""
        # First try YAML format: - url: <url>
        yaml_url_pattern = r'-\s*url:\s*(https://read\.readwise\.io/[^\s\]]+)'
        match = re.search(yaml_url_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback to direct URL pattern
        readwise_pattern = r'https://read\.readwise\.io/[^\s\]]+'
        match = re.search(readwise_pattern, text)
        return match.group(0) if match else None

    def retrieve_readwise_content(self, url: str) -> Dict[str, Any]:
        """Retrieve content from Readwise URL using the proper Readwise API."""
        try:
            print(f"📖 Retrieving Readwise content from: {url}")
            
            # Extract document ID from Readwise URL
            # URL format: https://read.readwise.io/new/read/01k56vzpz8cz9zncnsj2drsqer
            doc_id_match = re.search(r'/read/([a-zA-Z0-9]+)', url)
            if not doc_id_match:
                raise ValueError(f"Could not extract document ID from URL: {url}")
            
            document_id = doc_id_match.group(1)
            print(f"📖 Extracted document ID: {document_id}")
            
            # Use the existing Readwise client
            client = ReadwiseClient()
            document = client.get_document_content(document_id, include_html=True)
            
            if not document:
                raise ValueError(f"Document {document_id} not found in Readwise")
            
            print(f"✅ Retrieved: {document.title} ({document.word_count} words)")
            print(f"Author: {document.author}")
            print(f"URL: {document.url}")
            
            # Use html_content if available, otherwise fall back to content
            content = document.html_content or document.content or ""
            
            # Clean the content for better processing
            if content:
                # Remove HTML tags and clean up whitespace
                clean_content = re.sub(r'<[^>]+>', ' ', content)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                
                # Limit content length for processing
                if len(clean_content) > 8000:
                    clean_content = clean_content[:8000] + "..."
            else:
                clean_content = "No content available"
            
            result = {
                "title": document.title,
                "content": clean_content,
                "html_content": document.html_content,
                "author": document.author,
                "url": document.url,
                "word_count": document.word_count,
                "document_id": document_id,
                "success": True,
                "content_length": len(clean_content)
            }
            
            print(f"✅ Retrieved Readwise content: {result['content_length']} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error retrieving Readwise content: {e}")
            return {
                "title": "Error",
                "content": f"Failed to retrieve content from {url}: {str(e)}",
                "url": url,
                "success": False,
                "error": str(e)
            }

    def parse_content_instruction(self, instruction: str) -> Dict[str, Optional[str]]:
        """Parse YAML-style instruction format:
        - url: <url>
        - icp: <target audience>
        - dream: <desired outcome>
        - category: <content category>
        - format: <content format>
        """
        result = {
            "icp": None,
            "dream": None,
            "category": None,
            "format": None,
            "instruction_text": instruction
        }
        
        # Pattern to match YAML-style key-value pairs
        yaml_pattern = r'-\s*(\w+):\s*(.+?)(?=\n\s*-\s*\w+:|$)'
        matches = re.findall(yaml_pattern, instruction, re.MULTILINE | re.DOTALL)
        
        for key, value in matches:
            key = key.strip().lower()
            value = value.strip()
            
            if key == "icp":
                result["icp"] = value
            elif key == "dream":
                result["dream"] = value
            elif key == "category":
                result["category"] = value
            elif key == "format":
                result["format"] = value
        
        return result


class Coordinator:
    """Orchestrates agent workflows with completion tracking"""
    
    def __init__(self, store: ChatStore, client: OpenAI):
        self.store = store
        self.client = client

    def process_request(self, user_request: str, conversation_id: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Process user request through agent workflow"""
        # Add user message
        self.store.add_message(conversation_id, "user", user_request)
        
        # Reset conversation state
        self.store.update_conversation_state(conversation_id, {
            "status": "in_progress",
            "writer_complete": False,
            "format_agent_complete": False,
            "waiting_for_user": False,
            "user_request": user_request,
            "category": category
        })
        
        # Step 1: Writer
        print("Starting Writer agent...")
        writer_result = self._call_writer(conversation_id, user_request, category)
        
        # Update state after writer
        self.store.update_conversation_state(conversation_id, {
            "writer_complete": True,
            "current_draft": writer_result,
            "needs_review": True
        })
        
        # Step 2: Format Agent
        print("Starting Format Agent...")
        format_result = self._call_format_agent(conversation_id, writer_result)
        
        # Update state after format agent
        self.store.update_conversation_state(conversation_id, {
            "format_agent_complete": True,
            "final_output": format_result,
            "waiting_for_user": True,
            "status": "waiting_for_approval"
        })
        
        print("Workflow complete - waiting for user approval")
        return {
            "status": "waiting_for_approval",
            "final_output": format_result,
            "conversation_id": conversation_id
        }
    
    def generate_ideas(self, readwise_url: str, conversation_id: str) -> Dict[str, Any]:
        """
        NEW: Generate 12 content ideas from a Readwise article
        
        Args:
            readwise_url: URL to Readwise article
            conversation_id: Conversation ID to track state
            
        Returns:
            Dict with ideas (ContentIdeaSet as dict) and metadata
        """
        from pydantic import BaseModel, Field
        from typing import List
        
        # Define Pydantic models for structured output
        class ContentIdea(BaseModel):
            pillar_category: str = Field(description="Attract/Growth, Nurture/Authority, or Convert/Lead Gen")
            pillar_type: str = Field(description="The numbered type (e.g., '1. Transformation')")
            content_idea: str = Field(description="The content idea/title for this piece")
            justification: str = Field(description="Why this angle works")
            core_source_concept: str = Field(description="The key concept from source")
        
        class ContentIdeaSet(BaseModel):
            source_title: str
            source_summary: str
            ideas: List[ContentIdea] = Field(min_length=12, max_length=12)
        
        print(f"🔍 Generating 12 ideas from: {readwise_url}")
        
        # Fetch Readwise content
        readwise_content = self.store.retrieve_readwise_content(readwise_url)
        if not readwise_content.get("success"):
            raise ValueError(f"Failed to fetch Readwise content: {readwise_content.get('error')}")
        
        # Add user message with URL
        self.store.add_message(conversation_id, "user", f"Generate content ideas from: {readwise_url}")
        
        # Update state
        self.store.update_conversation_state(conversation_id, {
            "status": "generating_ideas",
            "readwise_url": readwise_url,
            "readwise_content": {
                "title": readwise_content["title"],
                "url": readwise_content["url"],
                "content_length": readwise_content["content_length"]
            }
        })
        
        # Build prompt for Strategist
        strategist_prompt = self.store.get_system_prompt("Strategist")
        if not strategist_prompt:
            raise RuntimeError("Strategist agent not found in system_prompts")
        
        user_prompt = f"""
# SOURCE ARTICLE

**Title:** {readwise_content['title']}
**Author:** {readwise_content.get('author', 'Unknown')}
**URL:** {readwise_content['url']}

**Content:**
{readwise_content['content']}

---

Generate 12 distinct content ideas using the framework above. Each idea should be grounded in specific concepts from this article.
"""
        
        # Call Strategist with structured outputs
        print("🤖 Calling Strategist agent...")
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": strategist_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=ContentIdeaSet,
            temperature=0.8,
        )
        
        ideas = response.choices[0].message.parsed
        ideas_dict = ideas.model_dump()
        
        # Store as message
        self.store.add_message(
            conversation_id,
            "assistant",
            f"Generated 12 content ideas from: {ideas.source_title}",
            agent_name="Strategist",
            metadata={
                "model": "gpt-4o-mini",
                "system_prompt_version": self.store.get_current_prompt_version("Strategist"),
                "ideas": ideas_dict
            }
        )
        
        # Update state with ideas
        self.store.update_conversation_state(conversation_id, {
            "status": "ideas_generated",
            "ideas": ideas_dict,
            "awaiting_selection": True
        })
        
        print(f"✅ Generated {len(ideas.ideas)} content ideas")
        
        return {
            "status": "ideas_generated",
            "conversation_id": conversation_id,
            "ideas": ideas_dict
        }
    
    def generate_from_idea(
        self,
        conversation_id: str,
        selected_idea_index: int,
        template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEW: Generate full LinkedIn article from a selected idea
        
        Args:
            conversation_id: Conversation ID
            selected_idea_index: Index of selected idea (0-11)
            template_id: Optional template ID to guide formatting
            
        Returns:
            Dict with generated article and metadata
        """
        import time
        from typing import Dict, Any
        
        print(f"📝 Generating article from idea #{selected_idea_index + 1}")
        
        # Add timeout and retry tracking
        start_time = time.time()
        max_duration = 300  # 5 minutes max
        retry_count = 0
        max_retries = 3
        
        try:
            # Get state with validation
            state = self.store.get_conversation_state(conversation_id)
            if not state:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            if not state.get("ideas"):
                raise ValueError("No ideas found in conversation state. Please generate ideas first using /ideas command.")
            
            ideas_data = state["ideas"]
            if not isinstance(ideas_data, dict) or "ideas" not in ideas_data:
                raise ValueError("Invalid ideas data structure")
            
            ideas_list = ideas_data["ideas"]
            if not isinstance(ideas_list, list) or len(ideas_list) == 0:
                raise ValueError("No ideas available in conversation")
            
            # Validate idea index with better error message
            if selected_idea_index < 0:
                raise ValueError(f"Invalid idea index: {selected_idea_index}. Must be between 1 and {len(ideas_list)}")
            
            if selected_idea_index >= len(ideas_list):
                raise ValueError(f"Invalid idea index: {selected_idea_index}. Only {len(ideas_list)} ideas available (use 1-{len(ideas_list)})")
            
            selected_idea = ideas_list[selected_idea_index]
            if not isinstance(selected_idea, dict):
                raise ValueError("Selected idea data is corrupted")
            
            # Check for required fields in selected idea
            required_fields = ["content_idea", "pillar_category", "pillar_type"]
            for field in required_fields:
                if field not in selected_idea:
                    raise ValueError(f"Selected idea missing required field: {field}")
            
            readwise_content_meta = state.get("readwise_content", {})
            
            # Fetch full Readwise content with timeout protection
            readwise_url = state.get("readwise_url")
            readwise_content = {"content": "", "title": readwise_content_meta.get("title", "")}
            
            if readwise_url and time.time() - start_time < max_duration:
                try:
                    print(f"📖 Fetching Readwise content from: {readwise_url}")
                    readwise_content = self.store.retrieve_readwise_content(readwise_url)
                    if not readwise_content.get("success"):
                        print(f"⚠️ Warning: Failed to fetch Readwise content: {readwise_content.get('error')}")
                        # Continue with empty content rather than failing
                except Exception as e:
                    print(f"⚠️ Warning: Error fetching Readwise content: {e}")
                    # Continue with empty content rather than failing
            
            # Add user selection message
            self.store.add_message(
                conversation_id,
                "user",
                f"Generate article from idea #{selected_idea_index + 1}: {selected_idea['content_idea']}"
            )
            
            # Update state with timeout protection
            self.store.update_conversation_state(conversation_id, {
                "status": "generating_article",
                "selected_idea_index": selected_idea_index,
                "selected_idea": selected_idea,
                "generation_start_time": start_time,
                "retry_count": retry_count
            })
            
            # Determine category and format from selected idea
            pillar_category = selected_idea["pillar_category"]
            pillar_type = selected_idea["pillar_type"]
            
            # Map to category/format for template selection
            category = None
            if "Attract" in pillar_category:
                category = "attract"
            elif "Nurture" in pillar_category:
                category = "nurture"
            elif "Convert" in pillar_category:
                category = "convert"
            
            # Extract format from pillar_type (e.g., "1. Transformation" → "transformation")
            format_name = pillar_type.split(".", 1)[1].strip().lower().replace(" ", "_") if "." in pillar_type else None
            
            # Check timeout before making API call
            if time.time() - start_time > max_duration:
                raise TimeoutError("Generation timeout exceeded")
            
            # Call Format Agent to generate full article with retry logic
            print(f"🎨 Calling Format Agent with idea...")
            
            while retry_count < max_retries:
                try:
                    if time.time() - start_time > max_duration:
                        raise TimeoutError("Generation timeout exceeded")
                    
                    article = self._call_format_agent_from_idea(
                        conversation_id,
                        selected_idea,
                        readwise_content.get("content", ""),
                        template_id=template_id,
                        category=category,
                        format=format_name
                    )
                    
                    if article and len(article.strip()) > 50:  # Basic validation
                        break
                    else:
                        raise ValueError("Generated article is too short or empty")
                        
                except Exception as e:
                    retry_count += 1
                    print(f"⚠️ Format Agent attempt {retry_count} failed: {e}")
                    
                    if retry_count >= max_retries:
                        raise Exception(f"Failed to generate article after {max_retries} attempts. Last error: {e}")
                    
                    # Update retry count in state
                    self.store.update_conversation_state(conversation_id, {
                        "retry_count": retry_count,
                        "last_error": str(e)
                    })
                    
                    # Wait before retry (exponential backoff)
                    time.sleep(min(2 ** retry_count, 10))
            
            # Update state with success
            self.store.update_conversation_state(conversation_id, {
                "status": "waiting_for_approval",
                "final_output": article,
                "waiting_for_user": True,
                "generation_complete_time": time.time(),
                "total_generation_time": time.time() - start_time
            })
            
            print(f"✅ Article generated in {time.time() - start_time:.1f}s - waiting for user approval")
            
            return {
                "status": "waiting_for_approval",
                "conversation_id": conversation_id,
                "final_output": article,
                "selected_idea": selected_idea,
                "generation_time": time.time() - start_time
            }
            
        except Exception as e:
            # Update state with error
            self.store.update_conversation_state(conversation_id, {
                "status": "error",
                "error_message": str(e),
                "error_time": time.time(),
                "retry_count": retry_count
            })
            
            print(f"❌ Error generating article: {e}")
            raise

    def continue_after_user_input(self, conversation_id: str, user_response: str) -> Dict[str, Any]:
        """Continue conversation after user provides input"""
        state = self.store.get_conversation_state(conversation_id)
        
        if not state.get("waiting_for_user"):
            return {"error": "No conversation waiting for user input"}
        
        # Add user response
        self.store.add_message(conversation_id, "user", user_response)
        
        # Check if user wants to continue or is satisfied
        if self._is_satisfaction_response(user_response):
            # Mark as complete
            self.store.update_conversation_state(conversation_id, {
                "status": "completed",
                "waiting_for_user": False,
                "user_satisfied": True
            })
            return {
                "status": "completed",
                "message": "Conversation completed successfully"
            }
        else:
            # User wants changes - call Format Agent with feedback
            current_draft = state.get("current_draft", "")
            format_result = self._call_format_agent_with_feedback(conversation_id, current_draft, user_response)
            
            # Update state
            self.store.update_conversation_state(conversation_id, {
                "final_output": format_result,
                "waiting_for_user": True,
                "status": "waiting_for_approval"
            })
            
            return {
                "status": "waiting_for_approval",
                "final_output": format_result,
                "conversation_id": conversation_id
            }

    def is_conversation_complete(self, conversation_id: str) -> bool:
        """Check if conversation is complete"""
        state = self.store.get_conversation_state(conversation_id)
        return (
            state.get("status") == "completed" or
            (state.get("format_agent_complete") and state.get("user_satisfied"))
        )

    def _call_writer(self, conversation_id: str, user_request: str, category: Optional[str] = None) -> str:
        """Call Writer agent"""
        ctx = self.store.build_context_for_agent(conversation_id, "Writer", recent_turns=10)
        
        # Check for Readwise URL and retrieve content
        readwise_url = self.store.extract_readwise_url(user_request)
        readwise_content = None
        if readwise_url:
            readwise_content = self.store.retrieve_readwise_content(readwise_url)
            print(f"📖 Readwise content retrieved: {readwise_content['title']}")
        
        # Parse instruction format if present
        parsed_instruction = self.store.parse_content_instruction(user_request)
        print(f"🎯 Parsed instruction: ICP='{parsed_instruction['icp']}', Dream='{parsed_instruction['dream']}', Category='{parsed_instruction['category']}', Format='{parsed_instruction['format']}'")
        
        # Build enhanced prompt
        enhanced_prompt = user_request
        
        # Add Readwise content if available
        if readwise_content and readwise_content.get("success"):
            enhanced_prompt += f"\n\n--- READWISE ARTICLE TO SUMMARIZE ---\n"
            enhanced_prompt += f"Title: {readwise_content['title']}\n"
            enhanced_prompt += f"Author: {readwise_content.get('author', 'Unknown')}\n"
            enhanced_prompt += f"URL: {readwise_content['url']}\n"
            enhanced_prompt += f"Word Count: {readwise_content.get('word_count', 'Unknown')}\n"
            enhanced_prompt += f"Content: {readwise_content['content']}\n"
            enhanced_prompt += f"--- END READWISE ARTICLE ---\n"
            enhanced_prompt += f"\nTASK: Summarize this article and create LinkedIn content based on it.\n"
        
        # Add parsed instruction context
        if parsed_instruction["icp"] or parsed_instruction["dream"]:
            enhanced_prompt += f"\n\n--- CONTENT STRATEGY ---\n"
            if parsed_instruction["icp"]:
                enhanced_prompt += f"Target ICP: {parsed_instruction['icp']}\n"
            if parsed_instruction["dream"]:
                enhanced_prompt += f"Desired Outcome: {parsed_instruction['dream']}\n"
            if parsed_instruction["category"]:
                enhanced_prompt += f"Content Category: {parsed_instruction['category']}\n"
            if parsed_instruction["format"]:
                enhanced_prompt += f"Content Format: {parsed_instruction['format']}\n"
            enhanced_prompt += f"--- END CONTENT STRATEGY ---\n"
        
        # Add category context to user prompt if provided
        if category:
            category_context = f"\n\nContent Strategy Category: {category.upper()}\n"
            category_context += f"Focus on creating content that serves the {category} goal:\n"
            if category == "attract":
                category_context += "- Build awareness and trust\n- Get the right people to notice and remember you"
            elif category == "nurture":
                category_context += "- Show authority and create demand\n- Build trust and keep audience engaged"
            elif category == "convert":
                category_context += "- Qualify and filter buyers\n- Move them toward working with you"
            enhanced_prompt += category_context
        
        ctx.append({"role": "user", "content": enhanced_prompt})
        
        response = self.client.chat.completions.create(model="gpt-5-mini", messages=ctx)
        content = response.choices[0].message.content
        
        # Store message with version tracking and metadata
        metadata = {
            "model": "gpt-5-mini", 
            "system_prompt_version": self.store.get_current_prompt_version("Writer"), 
            "category": category,
            "readwise_url": readwise_url,
            "parsed_instruction": parsed_instruction
        }
        
        self.store.add_message(
            conversation_id, "assistant", content, 
            agent_name="Writer",
            metadata=metadata
        )
        
        return content

    def _call_format_agent(
        self,
        conversation_id: str,
        draft: str,
        template_id: Optional[str] = None,
        category: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """Call Format Agent"""
        print(f"🎯 Format Agent: Starting with {category}/{format}")
        
        # Always use the prompt marked as current in system_prompts (is_current = true)
        instructions = self.store.get_system_prompt("Format Agent") or ""
        print(f"📝 Format Agent: Got instructions ({len(instructions)} chars)")

        # Resolve template to guide formatting if provided
        template_text = None
        chosen_template: Optional[Dict[str, Any]] = None
        if template_id:
            chosen_template = self.store.get_template_by_id(template_id)
            print(f"📋 Format Agent: Using template by ID: {template_id}")
        elif category and format:
            chosen_template = self.store.get_latest_template_by_category_format(category, format)
            print(f"📋 Format Agent: Using template by category/format: {category}/{format}")
        
        if chosen_template and chosen_template.get("content"):
            template_text = chosen_template["content"]
            print(f"📋 Format Agent: Template loaded ({len(template_text)} chars)")
        else:
            print("📋 Format Agent: No template found")

        # Normalize category/format display names from human-friendly labels
        def _normalize_label(text: Optional[str]) -> Optional[str]:
            if not text:
                return text
            t = text.strip().lower()
            replacements = {
                "attract": "attract",
                "nurture": "nurture",
                "convert": "convert",
                # Attract
                "transformation": "transformation",
                "misconception": "misconception",
                "belief shift": "belief_shift",
                "belief_shift": "belief_shift",
                "hidden truth": "hidden_truth",
                "hidden_truth": "hidden_truth",
                # Nurture
                "step by step": "step_by_step",
                "step_by_step": "step_by_step",
                "faq answer": "faq_answer",
                "faq_answer": "faq_answer",
                "process breakdown": "process_breakdown",
                "process_breakdown": "process_breakdown",
                "quick win": "quick_win",
                "quick_win": "quick_win",
                # Convert
                "client fix": "client_fix",
                "client_fix": "client_fix",
                "case study": "case_study",
                "case_study": "case_study",
                "objection reframe": "objection_reframe",
                "objection_reframe": "objection_reframe",
                "client quote": "client_quote",
                "client_quote": "client_quote",
            }
            return replacements.get(t, t.replace(" ", "_"))

        category = _normalize_label(category)
        format = _normalize_label(format)

        # Prepare input
        input_text = (
            "Review and transform this draft into a LinkedIn-ready post following the required format.\n\n"
            + (f"Template to follow (style/structure):\n{template_text}\n\n" if template_text else "")
            + f"Draft:\n{draft}"
        )
        print(f"📤 Format Agent: Sending to gpt-5-mini ({len(input_text)} chars)")

        # Use gpt-5-mini with Responses API for better formatting quality
        response = self.client.responses.create(
            model="gpt-5-mini",
            instructions=instructions,
            input=input_text,
            reasoning={"effort": "medium"},
            text={"format": {"type": "text"}, "verbosity": "medium"},
        )
        
        print("📥 Format Agent: Got response from gpt-5-mini")

        content = getattr(response, "output_text", "") or ""
        if not content:
            # Fallback extraction if SDK structure changes
            for item in getattr(response, "output", []) or []:
                for block in getattr(item, "content", []) or []:
                    if getattr(block, "type", "") in ("output_text", "input_text"):
                        text_val = getattr(block, "text", "") or ""
                        if text_val:
                            content = text_val
                            break
                if content:
                    break

        # Store message with version tracking (persist the current version string)
        version_used = self.store.get_current_prompt_version("Format Agent") or None
        self.store.add_message(
            conversation_id,
            "assistant",
            content,
            agent_name="Format Agent",
            metadata={
                "model": "gpt-5-mini",
                "system_prompt_version": version_used,
                "template_id": (chosen_template or {}).get("id") if chosen_template else None,
                "template_category": (chosen_template or {}).get("category") if chosen_template else None,
                "template_format": (chosen_template or {}).get("format") if chosen_template else None,
            },
        )

        return content

    def _call_format_agent_with_feedback(
        self,
        conversation_id: str,
        draft: str,
        feedback: str,
        template_id: Optional[str] = None,
        category: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """Call Format Agent with user feedback"""
        # Always use the prompt marked as current in system_prompts (is_current = true)
        instructions = self.store.get_system_prompt("Format Agent") or ""

        # Normalize labels
        def _normalize_label(text: Optional[str]) -> Optional[str]:
            if not text:
                return text
            t = text.strip().lower()
            replacements = {
                "attract": "attract",
                "nurture": "nurture",
                "convert": "convert",
                # Attract
                "transformation": "transformation",
                "misconception": "misconception",
                "belief shift": "belief_shift",
                "belief_shift": "belief_shift",
                "hidden truth": "hidden_truth",
                "hidden_truth": "hidden_truth",
                # Nurture
                "step by step": "step_by_step",
                "step_by_step": "step_by_step",
                "faq answer": "faq_answer",
                "faq_answer": "faq_answer",
                "process breakdown": "process_breakdown",
                "process_breakdown": "process_breakdown",
                "quick win": "quick_win",
                "quick_win": "quick_win",
                # Convert
                "client fix": "client_fix",
                "client_fix": "client_fix",
                "case study": "case_study",
                "case_study": "case_study",
                "objection reframe": "objection_reframe",
                "objection_reframe": "objection_reframe",
                "client quote": "client_quote",
                "client_quote": "client_quote",
            }
            return replacements.get(t, t.replace(" ", "_"))

        category = _normalize_label(category)
        format = _normalize_label(format)

        # Resolve template
        template_text = None
        chosen_template: Optional[Dict[str, Any]] = None
        if template_id:
            chosen_template = self.store.get_template_by_id(template_id)
        elif category and format:
            chosen_template = self.store.get_latest_template_by_category_format(category, format)
        if chosen_template and chosen_template.get("content"):
            template_text = chosen_template["content"]

        response = self.client.responses.create(
            model="gpt-5-mini",
            instructions=instructions,
            input=(
                "Review and transform this draft into a LinkedIn-ready post following the required format.\n\n"
                + (f"Template to follow (style/structure):\n{template_text}\n\n" if template_text else "")
                + f"Draft:\n{draft}\n\nUser feedback to incorporate:\n{feedback}"
            ),
            reasoning={"effort": "medium"},
            text={"format": {"type": "text"}, "verbosity": "medium"},
        )

        content = getattr(response, "output_text", "") or ""
        if not content:
            for item in getattr(response, "output", []) or []:
                for block in getattr(item, "content", []) or []:
                    if getattr(block, "type", "") in ("output_text", "input_text"):
                        text_val = getattr(block, "text", "") or ""
                        if text_val:
                            content = text_val
                            break
                if content:
                    break

        version_used = self.store.get_current_prompt_version("Format Agent") or None
        self.store.add_message(
            conversation_id,
            "assistant",
            content,
            agent_name="Format Agent",
            metadata={
                "model": "gpt-5-mini",
                "system_prompt_version": version_used,
                "template_id": (chosen_template or {}).get("id") if chosen_template else None,
                "template_category": (chosen_template or {}).get("category") if chosen_template else None,
                "template_format": (chosen_template or {}).get("format") if chosen_template else None,
                "feedback": feedback,  # Store the user's feedback
            },
        )

        return content

    def _call_format_agent_from_idea(
        self,
        conversation_id: str,
        selected_idea: Dict[str, str],
        source_content: str,
        template_id: Optional[str] = None,
        category: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        NEW: Call Format Agent to generate full article from a selected idea
        
        Args:
            selected_idea: Dict with content_idea, justification, core_source_concept, etc.
            source_content: Full source article content
            template_id: Optional template ID
            category: Content category (attract/nurture/convert)
            format: Content format type
            
        Returns:
            Generated LinkedIn article
        """
        import time
        import signal
        
        print(f"🎯 Format Agent (from idea): {selected_idea['pillar_type']}")
        
        # Add timeout protection
        def timeout_handler(signum, frame):
            raise TimeoutError("Format Agent API call timed out")
        
        # Set timeout for API call (2 minutes)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)
        
        try:
            # Get Format Agent prompt
            instructions = self.store.get_system_prompt("Format Agent") or ""
            print(f"📝 Format Agent: Got instructions ({len(instructions)} chars)")
            
            # Resolve template
            template_text = None
            chosen_template: Optional[Dict[str, Any]] = None
            if template_id:
                chosen_template = self.store.get_template_by_id(template_id)
                print(f"📋 Format Agent: Using template by ID: {template_id}")
            elif category and format:
                chosen_template = self.store.get_latest_template_by_category_format(category, format)
                print(f"📋 Format Agent: Using template by category/format: {category}/{format}")
            
            if chosen_template and chosen_template.get("content"):
                template_text = chosen_template["content"]
                print(f"📋 Format Agent: Template loaded ({len(template_text)} chars)")
            else:
                print("📋 Format Agent: No template found")
            
            # Build rich input for Format Agent
            input_text = f"""
Create a complete, engaging LinkedIn post based on this content idea:

# SELECTED IDEA

**Category:** {selected_idea['pillar_category']}
**Type:** {selected_idea['pillar_type']}
**Content Idea:** {selected_idea['content_idea']}

**Why this angle works:**
{selected_idea['justification']}

**Core concept from source:**
{selected_idea['core_source_concept']}

# SOURCE MATERIAL

{source_content[:8000]}  # Limit to 8000 chars to avoid token limits

# TEMPLATE TO FOLLOW

{template_text if template_text else "Use standard LinkedIn format with proper spacing, short lines, and engaging structure."}

# YOUR TASK

Write a complete, engaging LinkedIn post that:
1. Brings this content idea to life
2. Stays grounded in the source material
3. Follows the template style/structure
4. Is ready to publish (no placeholders or TODOs)
5. Matches the {selected_idea['pillar_type']} format expectations
"""
            
            print(f"📤 Format Agent: Sending to gpt-5-mini ({len(input_text)} chars)")
            
            # Use gpt-5-mini with Responses API - higher effort for full article generation
            response = self.client.responses.create(
                model="gpt-5-mini",
                instructions=instructions,
                input=input_text,
                reasoning={"effort": "high"},  # Higher effort since creating full article
                text={"format": {"type": "text"}, "verbosity": "high"},
            )
            
            print("📥 Format Agent: Got response from gpt-5-mini")
            
            # Extract content
            content = getattr(response, "output_text", "") or ""
            if not content:
                for item in getattr(response, "output", []) or []:
                    for block in getattr(item, "content", []) or []:
                        if getattr(block, "type", "") in ("output_text", "input_text"):
                            text_val = getattr(block, "text", "") or ""
                            if text_val:
                                content = text_val
                                break
                    if content:
                        break
            
            # Validate content
            if not content or len(content.strip()) < 50:
                raise ValueError("Generated content is too short or empty")
            
            # Store message
            version_used = self.store.get_current_prompt_version("Format Agent") or None
            self.store.add_message(
                conversation_id,
                "assistant",
                content,
                agent_name="Format Agent",
                metadata={
                    "model": "gpt-5-mini",
                    "system_prompt_version": version_used,
                    "template_id": (chosen_template or {}).get("id") if chosen_template else None,
                    "template_category": category,
                    "template_format": format,
                    "selected_idea": selected_idea,
                    "generation_mode": "from_idea"  # Flag to indicate new workflow
                },
            )
            
            return content
            
        except TimeoutError as e:
            print(f"⏰ Format Agent timeout: {e}")
            raise
        except Exception as e:
            print(f"❌ Format Agent error: {e}")
            raise
        finally:
            # Always cancel the alarm
            signal.alarm(0)

    def _is_satisfaction_response(self, response: str) -> bool:
        """Check if user response indicates satisfaction"""
        satisfaction_indicators = [
            "perfect", "great", "good", "looks good", "that works", 
            "i'm satisfied", "done", "complete", "thanks", "approve"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in satisfaction_indicators)

