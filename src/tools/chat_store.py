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

    def _is_satisfaction_response(self, response: str) -> bool:
        """Check if user response indicates satisfaction"""
        satisfaction_indicators = [
            "perfect", "great", "good", "looks good", "that works", 
            "i'm satisfied", "done", "complete", "thanks", "approve"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in satisfaction_indicators)

