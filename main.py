#!/usr/bin/env python3
"""
Main entry point for the LinkedIn Content Generator API
"""
import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )