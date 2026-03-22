import os
from dotenv import load_dotenv

# Load .env from backend dir first, then fall back to project root
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Get one at https://aistudio.google.com/apikey")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_ANALYSIS_MODEL = os.getenv("GEMINI_ANALYSIS_MODEL", "gemini-2.5-flash")
GEMINI_LETTER_MODEL = os.getenv("GEMINI_LETTER_MODEL", GEMINI_MODEL)
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "db", "pricing.db"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
PORT = int(os.getenv("PORT", "8000"))
