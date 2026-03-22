"""Quick sanity check that the Gemini API key works."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=["Say 'Apollo is ready!' in exactly those words."],
)

print(f"Gemini response: {response.text}")
print("API key is working!")
