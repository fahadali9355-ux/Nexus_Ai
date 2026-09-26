import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("=" * 60)
print("       LISTING ALL AVAILABLE MODELS FROM GEMINI API       ")
print("=" * 60)

try:
    for m in client.models.list():
        supported_actions = getattr(m, "supported_generation_methods", []) or getattr(m, "supported_actions", [])
        print(f"  Model: {m.name:45} | Display: {getattr(m, 'display_name', '')}")
except Exception as e:
    print(f"Error listing models: {e}")

candidates_v3 = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

print("\n" + "=" * 60)
print("       TESTING GENERATE_CONTENT ON V3 FLASH MODELS       ")
print("=" * 60)
for model in candidates_v3:
    try:
        resp = client.models.generate_content(
            model=model,
            contents="Say 'OK' in one word.",
        )
        print(f"  [AVAILABLE] {model:24} -> Text: {resp.text.strip()}")
    except Exception as e:
        print(f"  [ERROR]     {model:24} -> {e}")

print("=" * 60)
