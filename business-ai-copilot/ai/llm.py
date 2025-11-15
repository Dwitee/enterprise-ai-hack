import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set in environment/.env")

genai.configure(api_key=api_key)

MODEL_NAME = "gemini-2.5-flash"

model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_INSTRUCTION = (
    "You are an analytics copilot over a SQL Server database. "
    "Generate safe, read-only SQL and explain insights clearly to analysts and managers."
)

def llm(prompt: str) -> str:
    """Unified wrapper so the rest of the system works unchanged."""
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\nUser request:\n{prompt}"
    response = model.generate_content(full_prompt)
    return response.text
