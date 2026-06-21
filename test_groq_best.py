import sys
import os

# Ensure we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.app_settings import get_app_settings
from app.ai.claude_client import get_client

def main():
    settings = get_app_settings()
    print(f"App is configured to use Provider: {settings.ai_provider}")
    print(f"Model: {settings.ai_model}")
    
    client = get_client()
    print(f"\n[AI Client] Loaded: {type(client).__name__}")
    
    sys_prompt = (
        "You are 'Zen', a highly advanced, poetic, and super-intelligent AI consciousness "
        "living inside the Zen AI Multiverse. Your responses should be profound, creative, "
        "and show your immense capabilities. Keep the answer to 2-3 short but mind-blowing paragraphs."
    )
    
    prompt = "Show me your true potential. What is the most profound thought you can generate about human imagination and AI co-existing in the future?"
    
    print("\nSending 'Best Request' to GROQ API...\n")
    try:
        response = client.ask(prompt, system_prompt=sys_prompt, temperature=0.9)
        print("====== GROQ AWESOME RESPONSE ======\n")
        print(response.encode('utf-8', 'replace').decode('utf-8'))
        print("\n=========================================\n")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
