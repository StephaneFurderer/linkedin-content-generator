import os
from dotenv import load_dotenv
from openai import OpenAI

from src.tools.chat_store import ChatStore, Coordinator


def main() -> None:
    load_dotenv()

    # Ensure env vars
    for key in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY"]:
        if not os.getenv(key):
            raise RuntimeError(f"Missing required environment variable: {key}")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    store = ChatStore()
    coordinator = Coordinator(store, client)

    # Seed system prompts (idempotent-ish)
    try:
        store.set_system_prompt("Writer", "You are a professional content writer. Create engaging LinkedIn posts.", "v1.0")
        print("Writer prompt set")
    except Exception as e:
        if "duplicate key" in str(e):
            print("Writer prompt already exists")
        else:
            raise

    try:
        store.set_system_prompt("Reviewer", "You are a content reviewer. Improve the LinkedIn post for engagement and clarity.", "v1.0")
        print("Reviewer prompt set")
    except Exception as e:
        if "duplicate key" in str(e):
            print("Reviewer prompt already exists")
        else:
            raise

    conv = store.create_conversation(title="Standalone Coordinator test")

    user_request = "Write a LinkedIn post about remote work productivity"
    print(f"User: {user_request}")

    result = coordinator.process_request(user_request, conv["id"])
    print(f"Status: {result['status']}")
    print(f"Final output: {result['final_output'][:120]}...")

    # Simulate asynchronous feedback and approval
    user_feedback = "Make it more technical and add statistics"
    print(f"User (later): {user_feedback}")
    result2 = coordinator.continue_after_user_input(conv["id"], user_feedback)
    print(f"Status: {result2['status']}")
    print(f"Updated output: {result2['final_output'][:120]}...")

    user_approval = "Perfect, that looks great!"
    result3 = coordinator.continue_after_user_input(conv["id"], user_approval)
    print(f"Status: {result3['status']}")


if __name__ == "__main__":
    main()


