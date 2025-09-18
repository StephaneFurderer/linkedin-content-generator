#!/usr/bin/env python3
"""
Test the Nurture: Industry Myths template pipeline
This tests the Reviewer agent's ability to transform Writer content into strategic LinkedIn posts
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from src.tools.chat_store import ChatStore

load_dotenv()

def test_nurture_industry_myths_pipeline():
    """Test the complete pipeline for Nurture: Industry Myths content"""
    
    # Initialize components
    store = ChatStore()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("🧪 Testing Nurture: Industry Myths Pipeline")
    print("=" * 60)
    
    # Get the Industry Myths template from database
    print("📋 Step 1: Retrieving Industry Myths template...")
    templates = store.get_templates(category="nurture", format="industry_myths")
    
    if not templates:
        print("❌ No Industry Myths template found in database!")
        print("   Please add a template first using the UI or create one manually.")
        return
    
    template = templates[0]  # Use the first one
    print(f"✅ Found template: '{template['title']}'")
    print(f"   Author: {template.get('author', 'Unknown')}")
    print()
    
    # Writer's content (your research output)
    writer_content = """Question: What are the AI Agent Building Blocks?
The 7 Ai Agent Building Blocks - the foundations first approach.
Checkout his github repo: https://github.com/daveebbelaar/ai-cookbook/tree/main/agents/building-blocks

Why it matters: Being able to look at any problem, break it down, know the patterns and the essential building blocks to solve it.

Mindset shift: Dave Ebbelaar: unique angle is to how to make it to production. Stop building AI agent workflow from your bedroom, learn how to make it to production.

Cut 99% of the noise

I recently read Dave Ebbelaar's practical breakdown in How to Build Reliable AI Agents in 2025. If you're building AI-powered systems, this is a clear, production-focused framework that cuts through the hype.

Key takeaways you can apply now:
- 1) Intelligence Layer: The LLM call is essential, but the real work sits around it. Your code, prompts, and architecture matter just as much as the model.
- 2) Memory: LLMs are stateless. Persist and pass conversation context to maintain meaningful interactions.
- 3) Tools: External systems integration through tool calls. Use them when necessary, but avoid over-reliance on LLMs to "do everything."
- 4) Validation: Enforce structured JSON outputs with a defined schema. Validation reduces ambiguity and boosts reliability.
- 5) Control: Favor deterministic code for routing and decision-making. Use LLMs for reasoning where it adds real value, not as the sole decision-maker.
- 6) Recovery: Build robust error handling, retries, and fallbacks. Back-off strategies and clear recovery paths are essential in production.
- 7) Feedback: Human-in-the-loop for high-stakes or tricky decisions. Approval steps help prevent costly mistakes and improve learning.

A useful framing from the piece: treat AI agents as seven-block workflows (or DAGs), where most steps are standard code and only select parts leverage LLMs. This improves debuggability, maintainability, and resilience in real-world systems.

If you're shipping AI in production, this "foundations first" approach is worth your time. Which block feels most challenging in your current project, and why? Happy to share thoughts or experiences.

Quote: Most successful AI applications I've seen are built with custom building blocks, not frameworks. This is because most effective "AI agents" aren't actually that agentic at all. They're mostly deterministic software with strategic LLM calls placed exactly where they add value"""
    
    print("📝 Step 2: Writer's Content Analysis")
    print("-" * 40)
    print("Content length:", len(writer_content), "characters")
    print("Key topics identified:")
    print("  • AI Agent Building Blocks")
    print("  • Production vs. Prototype mindset")
    print("  • 7 essential components for reliable AI systems")
    print("  • Practical framework for shipping AI")
    print()
    
    print("preview of template:")
    print(template['content'])
    print()
    
    # Create the Reviewer agent system prompt
    print("🤖 Step 3: Creating Reviewer Agent for Industry Myths")
    print("-" * 50)
    
    review_user_prompt = f"""
    Research content:
    {writer_content}

    Template:
    {template['content']}
    """
    print("preview of review user prompt:")
    print(review_user_prompt)
    print()
    
    reviewer_system_prompt = f"""
    # ROLE
    Your job is to format the research content into well formatted LinkedIn posts.

    # INSTRUCTIONS
    Follow the Template from user.

    # FORMAT YOU MUST RESPECT

    1. Keep it simple!
    2. Stay consistent
    3. Don't use emojis
    4. Add some rhythm
    5. Add lots of spacing
    6. Create a logical flow
    7. 45 characters per line
    8. Use numbered listicles
    9. Cut unnecessary words
    10. Place your CTA at the end
    11. Adapt for mobile readers
    12. Write hooks as one-liners
    13. Use AI, but not exclusively
    14. Arrange your lists by length
    15. Avoid jargon and buzzwords
    16. Use frameworks (PAS / AIDA)
    17. Present info using bullet points
    18. don't use equations. Use plain text. 
    - example don't say: "Industry myth: AI agents = only LLMs." Instead say: "Most AI agents are not that agentic at all."

    # FINAL THOUGHTS
    Take a deep breath and work on this step-by-step.
    Focus on the hook (first line) the cliffhanger (subtitle) and bold yet authentic conclusion
    Engaging hook and strong close

    """


    print("✅ Reviewer system prompt created")
    print(f"   Prompt length: {len(reviewer_system_prompt)} characters")
    print()
    
    # Test the Reviewer agent
    print("🎯 Step 4: Running Reviewer Agent")
    print("-" * 40)
    
    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=reviewer_system_prompt,
            input=f"Transform this research content into an Industry Myths LinkedIn post:\n\n{writer_content}",
            reasoning={"effort": "medium"},
            text={"format": {"type": "text"}, "verbosity": "medium"},
        )
        
        reviewer_output = response.output_text
        
        print("✅ Reviewer agent completed successfully!")
        print()
        print("📱 FINAL LINKEDIN POST:")
        print("=" * 80)
        if reviewer_output:
            # Clean up the output formatting
            formatted_output = reviewer_output.strip()
            # Ensure proper paragraph breaks
            formatted_output = formatted_output.replace('\n\n\n', '\n\n')
            print(formatted_output)
            print()
            print("=" * 80)
            print(f"📊 Post Stats: {len(formatted_output)} characters | ~{len(formatted_output.split())} words")
        else:
            print("[EMPTY RESPONSE]")
            print("=" * 80)
        print()
        
        # Analyze the output
        print("📊 Step 5: Content Analysis")
        print("-" * 30)
        print(f"Post length: {len(reviewer_output)} characters")
        print(f"Word count: ~{len(reviewer_output.split())} words")
        print(f"Paragraphs: {len(reviewer_output.split('\\n\\n'))}")
        print()
        
        # Check for key elements
        elements_check = {
            "Hook": "starts with bold statement" in reviewer_output.lower() or "myth" in reviewer_output.lower()[:100],
            "Evidence": any(word in reviewer_output.lower() for word in ["7", "building blocks", "production", "framework"]),
            "CTA": "?" in reviewer_output[-100:] or "thoughts" in reviewer_output.lower()[-100:],
            "Structure": "\\n\\n" in reviewer_output and len(reviewer_output.split("\\n")) > 3
        }
        
        print("✅ Content Quality Check:")
        for element, present in elements_check.items():
            status = "✅" if present else "❌"
            print(f"   {status} {element}")
        
        print()
        print("🎉 Pipeline test completed successfully!")
        
        return reviewer_output
        
    except Exception as e:
        print(f"❌ Error running Reviewer agent: {e}")
        return None

def test_template_structure():
    """Test that we have the right template structure"""
    print("🔍 Testing Template Structure")
    print("-" * 30)
    
    store = ChatStore()
    
    # Check for Industry Myths template
    templates = store.get_templates(category="nurture", format="industry_myths")
    
    if templates:
        template = templates[0]
        print(f"✅ Found Industry Myths template: '{template['title']}'")
        print(f"   Content preview: {template['content'][:100]}...")
        print(f"   Author: {template.get('author', 'Unknown')}")
        print(f"   Tags: {template.get('tags', [])}")
    else:
        print("❌ No Industry Myths template found!")
        print("   Available nurture templates:")
        nurture_templates = store.get_templates(category="nurture")
        for t in nurture_templates:
            print(f"     - {t['format']}: {t['title']}")
    
    print()

if __name__ == "__main__":
    print("🚀 AI Content Pipeline Test: Nurture - Industry Myths")
    print("=" * 60)
    print()
    
    # Test template structure first
    test_template_structure()
    
    # Run the main pipeline test
    result = test_nurture_industry_myths_pipeline()
    
    if result:
        print("\\n💡 Next Steps:")
        print("1. Review the generated post for quality and alignment")
        print("2. Test with different research content")
        print("3. Integrate this into the main Coordinator workflow")
        print("4. Add template selection logic to the UI")
    else:
        print("\\n❌ Pipeline test failed. Check the error messages above.")
