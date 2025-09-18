import os
from dotenv import load_dotenv
from src.tools.chat_store import ChatStore


def main() -> None:
    load_dotenv()
    store = ChatStore()

    format_agent_prompt = """
        # ROLE
        Your job is to format the research content into well formatted LinkedIn post following the template.

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
    
    try:
        # Insert as v1.0 and set as current
        store.set_system_prompt(
            agent_name="Format Agent",
            prompt=format_agent_prompt,
            version="v1.0",
            set_as_current=True,
        )
        print("Saved Format Agent v1.0 system prompt and set as current.")
    except Exception as e:
        print(f"Failed to save Format Agent v1.0 prompt: {e}")


if __name__ == "__main__":
    main()

