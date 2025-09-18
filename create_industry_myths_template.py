#!/usr/bin/env python3
"""
Create the Industry Myths template in the database
"""

import os
from dotenv import load_dotenv
from src.tools.chat_store import ChatStore

load_dotenv()

def create_industry_myths_template():
    """Create the Industry Myths template"""
    
    store = ChatStore()
    
    # Based on the examples from your Google doc
    template_content = """Most people think AI agents are just chatbots with fancy names.

(because they only see the surface level)

I hear it all the time:

"AI agents are just glorified chatbots"
"They can't do anything real"
"It's all hype and no substance"

And I'll be honest: I used to think that too.

But here's what most people miss:

AI agents aren't just conversational interfaces. They're complete workflow systems that can:
- Integrate with external tools and APIs
- Maintain memory across interactions
- Make decisions based on structured data
- Handle errors and recovery gracefully
- Learn from human feedback

The difference between a chatbot and an AI agent is like the difference between a calculator and a computer.

One does simple calculations.
The other can run entire programs.

Here's the framework I use to build real AI agents:

1. Intelligence Layer: Strategic LLM calls where they add value
2. Memory: Persistent context across interactions
3. Tools: Integration with external systems
4. Validation: Structured outputs with error handling
5. Control: Deterministic routing and decision-making
6. Recovery: Robust error handling and fallbacks
7. Feedback: Human-in-the-loop for critical decisions

Most "AI agents" you see are actually just chatbots because they're missing these building blocks.

Real AI agents are production-ready systems that can:
- Process complex workflows
- Handle edge cases gracefully
- Scale reliably
- Learn and improve over time

If you're building AI systems, don't just add a chat interface and call it an agent.

Build the foundation first.

The conversation is just the tip of the iceberg."""

    try:
        template = store.create_template(
            title="Industry Myths: AI Agents vs Chatbots",
            content=template_content,
            category="nurture",
            format="industry_myths",
            author="Content Strategy Framework",
            linkedin_url="https://linkedin.com/in/example",
            tags=["ai", "agents", "myths", "framework", "production"]
        )
        
        print("✅ Industry Myths template created successfully!")
        print(f"   ID: {template['id']}")
        print(f"   Title: {template['title']}")
        print(f"   Category: {template['category']}")
        print(f"   Format: {template['format']}")
        print()
        
        return template
        
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return None

if __name__ == "__main__":
    print("🏗️  Creating Industry Myths Template")
    print("=" * 40)
    
    template = create_industry_myths_template()
    
    if template:
        print("🎉 Template ready for testing!")
        print("   Run: python3 test_nurture_industry_myths.py")
    else:
        print("❌ Failed to create template")
