import os
import requests
from typing import Dict, List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

# Ensure environment variables are loaded from the nearest .env if present
load_dotenv(find_dotenv(usecwd=True), override=False)

# Readwise integration classes
class ReadwiseDocument(BaseModel):
    id: str = ""
    url: str = ""
    title: str = ""
    author: str = ""
    source: str = ""
    category: str = ""
    location: str = ""
    tags: List[str] = []
    site_name: str = ""
    word_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    summary: str = ""
    image_url: str = ""
    content: str = ""
    html_content: str = ""
    reading_progress: float = 0.0
    first_opened_at: Optional[str] = None
    last_opened_at: Optional[str] = None
    saved_at: str = ""
    last_moved_at: str = ""

class ReadwiseClient:
    def __init__(self, api_token: Optional[str] = None):
        """Initialize Readwise API client."""
        # Try to get token from parameter, environment, or settings
        if api_token:
            self.api_token = api_token
        else:
            # Try common env var names
            for key in (
                "READWISE_TOKEN",
                "READWISE_API_TOKEN",
                "READWISE",
                "READWISEKEY",
                "readwise_token",
            ):
                value = os.getenv(key)
                if value:
                    self.api_token = value
                    break
            else:
                self.api_token = None

        if not self.api_token:
            try:
                from config.settings import settings
                self.api_token = settings.readwise_token
            except Exception:
                pass
        if not self.api_token:
            raise ValueError("READWISE token not found. Set READWISE_TOKEN (or readwise_token) in .env")

        self.base_url = "https://readwise.io/api/v3"
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Readwise API."""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Readwise API request failed: {e}")
            return {}

    def get_document_content(self, document_id: str, include_html: bool = False) -> Optional[ReadwiseDocument]:
        """Get full content of a specific document."""
        endpoint = "list/"
        params = {"id": document_id}
        if include_html:
            params["withHtmlContent"] = True

        data = self._make_request(endpoint, params)

        if not data or "results" not in data or not data["results"]:
            return None

        doc_data = data["results"][0]

        # Handle tags: convert dict to list or use empty list
        tags_raw = doc_data.get("tags", [])
        if isinstance(tags_raw, dict):
            tags = list(tags_raw.keys()) if tags_raw else []
        elif isinstance(tags_raw, list):
            tags = tags_raw
        else:
            tags = []

        # Handle content: ensure it's a string
        content_raw = doc_data.get("content")
        content = content_raw if content_raw is not None else ""

        return ReadwiseDocument(
            id=doc_data.get("id") or "",
            url=doc_data.get("url") or "",
            title=doc_data.get("title") or "",
            author=doc_data.get("author") or "",
            source=doc_data.get("source") or "",
            category=doc_data.get("category") or "",
            location=doc_data.get("location") or "",
            tags=tags,
            site_name=doc_data.get("site_name") or "",
            word_count=doc_data.get("word_count") or 0,
            created_at=doc_data.get("created_at") or "",
            updated_at=doc_data.get("updated_at") or "",
            notes=doc_data.get("notes") or "",
            summary=doc_data.get("summary") or "",
            image_url=doc_data.get("image_url") or "",
            content=content,
            html_content=doc_data.get("html_content") or "",
            reading_progress=doc_data.get("reading_progress") or 0.0,
            first_opened_at=doc_data.get("first_opened_at"),
            last_opened_at=doc_data.get("last_opened_at"),
            saved_at=doc_data.get("saved_at") or "",
            last_moved_at=doc_data.get("last_moved_at") or ""
        )

if __name__ == "__main__":
    client = ReadwiseClient()
    document = client.get_document_content("01k56vzpz8cz9zncnsj2drsqer", include_html=True)
    print(document)