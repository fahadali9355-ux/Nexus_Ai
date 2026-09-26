import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = (
    "You are Nexus, a smart and helpful voice assistant. "
    "Keep your spoken answers concise, direct, and conversational (typically 2 to 4 sentences), "
    "unless the user explicitly requests more detail, code, or an in-depth explanation. "
    "Avoid unnecessary introductory filler."
)

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    temperature=0.7,
)

test_queries = [
    "Who is Nikola Tesla?",
    "Explain quantum computing.",
    "What is photosynthesis?",
    "Why is the sky blue?",
]

print("=" * 65)
print("  TESTING CONCISE SYSTEM INSTRUCTION ON GEMINI-3.5-FLASH  ")
print("=" * 65)

for q in test_queries:
    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash"]
    resp = None
    used_model = None
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=q,
                config=config,
            )
            used_model = m
            break
        except Exception as e:
            continue

    if resp:
        um = resp.usage_metadata
        print(f"\nQuery: '{q}' (Model: {used_model})")
        print(f"  Prompt Tokens: {um.prompt_token_count} | Output Tokens: {um.candidates_token_count} (Total: {um.total_token_count})")
        print(f"  Response: \"{resp.text.strip()}\"")
    else:
        print(f"\nQuery: '{q}' -> All models failed.")

print("\n" + "=" * 65)
