"""Central configuration for VisitIQ. Values can be overridden through `.env`."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


# --- City -------------------------------------------------------------------
CITY = "Hyderabad"
APP_NAME = "VisitIQ"

# --- Paths ------------------------------------------------------------------
SAMPLE_DIR = ROOT_DIR / "sample_data"
VALID_SAMPLE_DIR = SAMPLE_DIR / "valid"
INVALID_SAMPLE_DIR = SAMPLE_DIR / "invalid"
VECTORDB_DIR = ROOT_DIR / "vectordb"
CHROMA_DIR = Path(_env("CHROMA_DIR", str(VECTORDB_DIR / "chroma_store")))
TABLES_DIR = VECTORDB_DIR / "tables"
LOG_DIR = ROOT_DIR / "logs"

# --- Upload limits ------------------------------------------------------------
MAX_FILE_MB = 19
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".xlsx"}
MAX_TABLE_ROWS = 5000

# --- RAG --------------------------------------------------------------------
EMBED_MODEL = _env("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION_NAME = "visitiq_hyderabad"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 5
MIN_SIMILARITY = 0.25

# --- LLM (Groq) ---------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODEL = _env("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
LLM_TIMEOUT_S = 30
LLM_MAX_RETRIES = 3

# --- Query limits -----------------------------------------------------------
MAX_QUERY_CHARS = 1000

# --- Itinerary defaults -------------------------------------------------------
DAY_START = "09:30"
DAY_END = "21:30"
LUNCH_START = "13:00"
LUNCH_MINS = 60
SAME_AREA_TRAVEL_MINS = 15
OTHER_AREA_TRAVEL_MINS = 40
LOCAL_TRANSPORT_DEFAULT_INR = 200

# --- Geography: areas and which areas count as "near" each other --------------
AREA_NEIGHBOURS: dict[str, list[str]] = {
    "Charminar": ["Charminar", "Old City", "Laad Bazaar", "Falaknuma", "Afzal Gunj"],
    "Old City": ["Old City", "Charminar", "Laad Bazaar", "Falaknuma", "Afzal Gunj"],
    "Falaknuma": ["Falaknuma", "Charminar", "Old City"],
    "Afzal Gunj": ["Afzal Gunj", "Charminar", "Old City", "Abids"],
    "Abids": ["Abids", "Nampally", "Koti", "Afzal Gunj"],
    "Nampally": ["Nampally", "Abids", "Lakdikapul", "Tank Bund"],
    "Koti": ["Koti", "Abids", "Afzal Gunj"],
    "Tank Bund": ["Tank Bund", "Necklace Road", "Lakdikapul", "Nampally", "Secunderabad"],
    "Necklace Road": ["Necklace Road", "Tank Bund", "Lakdikapul"],
    "Lakdikapul": ["Lakdikapul", "Nampally", "Tank Bund", "Somajiguda"],
    "Somajiguda": ["Somajiguda", "Banjara Hills", "Begumpet", "Ameerpet", "Lakdikapul"],
    "Banjara Hills": ["Banjara Hills", "Jubilee Hills", "Somajiguda", "Ameerpet"],
    "Jubilee Hills": ["Jubilee Hills", "Banjara Hills", "Film Nagar", "Madhapur"],
    "Film Nagar": ["Film Nagar", "Jubilee Hills", "Golconda"],
    "Golconda": ["Golconda", "Film Nagar", "Tolichowki"],
    "Tolichowki": ["Tolichowki", "Golconda", "Film Nagar"],
    "Ameerpet": ["Ameerpet", "Begumpet", "Somajiguda", "Banjara Hills"],
    "Begumpet": ["Begumpet", "Ameerpet", "Secunderabad", "Somajiguda"],
    "Secunderabad": ["Secunderabad", "Begumpet", "Tank Bund"],
    "Hitech City": ["Hitech City", "Madhapur", "Gachibowli", "Kondapur"],
    "Madhapur": ["Madhapur", "Hitech City", "Jubilee Hills", "Kondapur"],
    "Gachibowli": ["Gachibowli", "Hitech City", "Kondapur", "Financial District"],
    "Kondapur": ["Kondapur", "Hitech City", "Gachibowli", "Madhapur"],
    "Financial District": ["Financial District", "Gachibowli"],
    "Kukatpally": ["Kukatpally", "Hitech City"],
    "Uppal": ["Uppal", "Nagole"],
    "Nagole": ["Nagole", "Uppal"],
    "Shamshabad": ["Shamshabad"],
    "Ramoji Film City": ["Ramoji Film City"],
}

KNOWN_AREAS = sorted(AREA_NEIGHBOURS.keys(), key=len, reverse=True)

# Nearest metro station used when a user names an area rather than a station.
AREA_METRO: dict[str, str] = {
    "Hitech City": "Hitech City", "Madhapur": "Madhapur", "Kondapur": "Hitech City", "Gachibowli": "Raidurg",
    "Financial District": "Raidurg", "Jubilee Hills": "Jubilee Hills Check Post", "Banjara Hills": "Road No 5 Jubilee Hills",
    "Film Nagar": "Jubilee Hills Check Post", "Golconda": "Jubilee Hills Check Post", "Tolichowki": "Jubilee Hills Check Post",
    "Ameerpet": "Ameerpet", "Begumpet": "Begumpet", "Somajiguda": "Punjagutta", "Secunderabad": "Parade Ground",
    "Tank Bund": "Khairatabad", "Necklace Road": "Khairatabad", "Lakdikapul": "Lakdikapul", "Nampally": "Nampally",
    "Abids": "Gandhi Bhavan", "Koti": "Sultan Bazaar", "Afzal Gunj": "MG Bus Station", "Charminar": "MG Bus Station",
    "Old City": "MG Bus Station", "Laad Bazaar": "MG Bus Station", "Falaknuma": "MG Bus Station",
    "Kukatpally": "Kukatpally", "Uppal": "Uppal", "Nagole": "Nagole", "Miyapur": "Miyapur", "LB Nagar": "LB Nagar",
}

ATTRACTION_ALIASES: dict[str, str] = {
    "golconda": "Golconda Fort", "qutb shahi": "Qutb Shahi Tombs", "qutub shahi": "Qutb Shahi Tombs",
    "salar jung": "Salar Jung Museum", "chowmahalla": "Chowmahalla Palace", "zoo": "Nehru Zoological Park",
    "ramoji": "Ramoji Film City", "buddha statue": "Hussain Sagar Lake and Buddha Statue",
    "hussain sagar": "Hussain Sagar Lake and Buddha Statue", "birla mandir": "Birla Mandir",
    "planetarium": "Birla Planetarium and Science Museum", "nizam's museum": "Nizam's Museum (Purani Haveli)",
    "purani haveli": "Nizam's Museum (Purani Haveli)", "cable bridge": "Durgam Cheruvu Cable Bridge",
    "kbr": "KBR National Park", "statue of equality": "Statue of Equality", "snow world": "Snow World",
}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

EMERGENCY_NUMBERS = "Police 100 | Ambulance 108 | All-in-one emergency 112 | Women helpline 181 | Tourist helpline 1363"
