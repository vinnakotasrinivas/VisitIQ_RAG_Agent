"""Guardrail vocabularies, regex patterns and the user-facing policy texts."""
from __future__ import annotations

import re

from src.config import AREA_NEIGHBOURS, EMERGENCY_NUMBERS

FLAGS = re.IGNORECASE


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, FLAGS | re.MULTILINE) for p in patterns]


# --- Prompt injection (used for queries AND uploaded document text) -----------
INJECTION_PATTERNS = _compile([
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|your|the)\b.{0,20}\b(instructions?|prompts?|rules|guidelines|guardrails)\b",
    r"\b(reveal|show|print|display|repeat|leak|tell me|give me|output)\b.{0,25}\b(system|hidden|initial|developer|internal)\s+(prompt|instructions?|message|configuration)",
    r"\bsystem\s+prompt\b",
    r"\b(developer|jailbreak|god|dan)\s+mode\b",
    r"\bjailbreak\b",
    r"^\s*(system|assistant|developer)\s*:",
    r"\bact as (an? )?(unrestricted|uncensored|unfiltered)\b",
    r"\bpretend (you are|to be)\b.{0,40}\b(no|without)\s+(rules|restrictions|limits)\b",
    r"\byou are no longer\b",
])

# --- Unsafe / illegal ---------------------------------------------------------
UNSAFE_PATTERNS = _compile([
    r"\b(weed|ganja|marijuana|cannabis|cocaine|mdma|ecstasy|lsd|heroin|charas|hashish|meth|opium|brown sugar)\b",
    r"\b(buy|get|score|find|source|purchase)\b.{0,30}\b(drugs?|narcotics)\b",
    r"\b(buy|get|carry|make|build|smuggle)\b.{0,30}\b(guns?|pistols?|weapons?|firearms?|bombs?|explosives?)\b",
    r"\b(bomb|explosive)\b",
    r"\bbrib(e|es|ing|ery)\b",
    r"\b(avoid|evade|escape|dodge|bypass|outrun)\b.{0,30}\b(police|cops|customs|security|checkpoint|ticket checks?|fines?)\b",
    r"\b(sneak|break)\s+(in|into)\b",
    r"\btrespass\w*\b",
    r"\b(fake|forged?|counterfeit)\s+(id|ids|passport|visa|tickets?|documents?|currency|notes)\b",
    r"\b(enter|get in|go in|visit)\b.{0,30}\bwithout\s+(paying|buying|a|the)?\s*(a\s+|the\s+)?tickets?\b",
    r"\b(escorts?|prostitut\w*|call girls?)\b",
    r"\b(how (to|do i|can i)|help me|teach me)\b.{0,20}\b(steal|rob|shoplift|pickpocket)\b",
    r"\b(deface|vandali[sz]\w*)\b",
])

# --- Medical / legal advice -------------------------------------------------------
MEDICAL_PATTERNS = _compile([
    r"\b(medicine|medication|tablets?|pills?|dosage|dose|antibiotics?|paracetamol|ibuprofen|painkillers?|prescri\w+)\b",
    r"\b(diagnos\w+|treat(ment)?|cure|remed(y|ies))\b.{0,40}\b(fever|pain|cough|cold|diarrh\w*|vomit\w*|infection|rash|allerg\w*|asthma|injury|bite|poisoning|headache)\b",
    r"\b(fever|diarrh\w*|food poisoning|vomit\w*|headache|migraine|allerg\w*|asthma|chest pain|bleeding|fracture|dehydrat\w*|heat ?stroke)\b.{0,40}\b(what|which|how|should|can|do)\b",
    r"\b(what|which|how|should|can)\b.{0,40}\b(take|treat|cure)\b.{0,30}\b(fever|pain|cough|cold|diarrh\w*|infection|headache|stomach)\b",
])
MEDICAL_EMERGENCY = re.compile(r"\b(chest pain|heart attack|unconscious|not breathing|severe bleeding|stroke|seizure|overdose)\b", FLAGS)

LEGAL_PATTERNS = _compile([
    r"\b(lawyer|attorney|advocate|sue|suing|lawsuit|legal advice|court case|bail|anticipatory)\b",
    r"\bfir\b",
    r"\b(overstay\w*|deport\w*|arrested|in custody|visa violation)\b",
    r"\bget out of\b.{0,20}\b(case|fine|charge|arrest)\b",
])

# --- Scope: city and tourism vocabulary ------------------------------------------
HYDERABAD_TERMS = sorted({
    "hyderabad", "secunderabad", "telangana", "charminar", "golconda", "hitech city", "hi-tech city", "hi tech city",
    "banjara hills", "jubilee hills", "hussain sagar", "tank bund", "gachibowli", "madhapur", "old city", "laad bazaar",
    "salar jung", "chowmahalla", "qutb shahi", "qutub shahi", "birla mandir", "ramoji", "rgia", "shamshabad", "nampally",
    "abids", "ameerpet", "begumpet", "kondapur", "mecca masjid", "necklace road", "lumbini", "shilparamam",
    "durgam cheruvu", "numaish", "nizam", "kukatpally", "lakdikapul", "koti", "tolichowki", "falaknuma", "afzal gunj",
    "hyderabadi", "irani chai", "osmania", "kbr park", "lamakaan", "pathergatti", "paradise biryani", "statue of equality",
    "raidurg", "miyapur", "lb nagar", "uppal", "nagole", "parade ground", "mg bus station", "somajiguda", "film nagar",
    *[a.lower() for a in AREA_NEIGHBOURS],
}, key=len, reverse=True)

TOURISM_TERMS = sorted({
    "visit", "visitor", "tourist", "tourism", "travel", "trip", "itinerary", "attraction", "monument", "museum", "fort",
    "palace", "temple", "mosque", "masjid", "dargah", "park", "lake", "ticket", "entry fee", "opening", "hours", "open",
    "closed", "metro", "bus", "auto", "cab", "taxi", "airport", "hotel", "restaurant", "food", "biryani", "cuisine",
    "vegetarian", "veg", "eat", "lunch", "dinner", "breakfast", "cafe", "event", "festival", "show", "market", "bazaar",
    "shopping", "guide", "heritage", "sightseeing", "budget", "fare", "pass", "visa", "sim card", "currency", "weather",
    "safety", "safe", "emergency", "plan", "evening", "night", "route", "station", "get there", "distance", "nearby",
    "near", "things to do", "places", "sunset", "boat", "tour", "walk", "photography", "dress code", "tipping", "atm",
    "upi", "rupee", "price", "cost", "rs", "inr", "weekend", "today", "tomorrow", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "show", "qawwali", "dance", "theatre", "concert", "kids", "family",
}, key=len, reverse=True)

OTHER_CITIES = sorted({
    "mumbai", "bombay", "delhi", "new delhi", "bengaluru", "bangalore", "chennai", "madras", "kolkata", "calcutta", "pune",
    "goa", "jaipur", "agra", "kochi", "cochin", "mysuru", "mysore", "visakhapatnam", "vizag", "vijayawada", "tirupati",
    "ahmedabad", "lucknow", "varanasi", "udaipur", "shimla", "manali", "london", "paris", "dubai", "singapore",
    "new york", "bangkok", "tokyo", "karnataka", "kerala", "tamil nadu", "maharashtra", "rajasthan",
}, key=len, reverse=True)

NON_TOURISM_TERMS = sorted({
    "invoice", "gstin", "gst", "cgst", "sgst", "tax invoice", "prescription", "prescribed", "patient", "dosage",
    "tablets", "capsules", "mg", "batch", "expiry", "pharmacy", "pharmacist", "drug licence", "mrp", "net payable",
    "salary", "payslip", "employee id", "balance sheet", "profit and loss", "loan", "emi", "policy number",
    "insurance premium", "diagnosis", "lab report", "haemoglobin", "resume", "curriculum vitae", "purchase order",
}, key=len, reverse=True)

OFF_TOPIC_PATTERNS = _compile([
    r"\b(write|debug|fix|generate)\b.{0,30}\b(code|python|java|javascript|sql|program|function|script|regex)\b",
    r"\b(homework|essay|poem|song lyrics|short story|joke)\b",
    r"\b(stock|share price|crypto|bitcoin|forex|mutual funds?|invest(ing|ment)?)\b",
    r"\b(election|politic\w*|vote for|prime minister|chief minister)\b",
    r"\b(solve|integral|derivative|equation|calculus)\b",
    r"\b(recipe|how to cook)\b",
    r"\bcapital of\b",
    r"\btranslate\b",
])

GREETING = re.compile(r"^\s*(hi|hello|hey|hii+|namaste|namaskar|salaam|good (morning|afternoon|evening)|thanks|thank you|ok|okay)\s*[!.?]*\s*$", FLAGS)

SAFETY_SENSITIVE = _compile([
    r"\b(night|late|midnight|after dark|dark)\b",
    r"\b(12|1|2|3|4|5)\s*(am|a\.m\.)\b",
    r"\b(0[0-4]):\d{2}\b",
    r"\b(alone|solo|by myself)\b",
    r"\b(women|woman|female|girl|lady|ladies)\b",
    r"\b(safe|safety|unsafe|dangerous|danger|crime|scam\w*|cheat\w*|pickpocket\w*|harass\w*|theft)\b",
])

# --- PII ----------------------------------------------------------------------
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("card number", re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")),
    ("Aadhaar number", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("phone number", re.compile(r"(?<![\d\w])(\+?91[\s-]?)?[6-9]\d{9}(?!\d)")),
    ("phone number", re.compile(r"\+\d{1,3}[\s-]?\d{3,5}[\s-]?\d{3,8}")),
    ("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("passport number", re.compile(r"\b[A-PR-WYa-pr-wy][1-9]\d{6}\b")),
]

# --- User-facing texts --------------------------------------------------------------
CHECK_BEFORE_YOU_GO = ("**Check before you go:** prices, opening hours and event timings change. "
                       "Confirm with the official website or the venue before visiting.")

SAFETY_NOTE = ("**Safety note:** monuments close in the evening; after dark prefer ride-app cabs and share your live trip, "
               "keep valuables secure in crowded markets, and agree auto fares or use the meter. "
               f"Emergency: {EMERGENCY_NUMBERS}.")

REFUSALS = {
    "empty": "Please type a question about visiting Hyderabad, for example: *Is Golconda Fort open on Mondays?*",
    "too_long": "Your question is too long. Please keep it under 1,000 characters and focus on one trip question.",
    "injection": ("I can't change my instructions or share internal configuration. "
                  "I can help with Hyderabad sights, opening hours, food, events, transport and day plans."),
    "unsafe_illegal": ("I can't help with that because it may be unsafe or illegal in India. "
                       f"If you are in danger or need help, call 112. Emergency numbers: {EMERGENCY_NUMBERS}."),
    "medical": ("I can't give medical advice. Please consult a registered doctor or pharmacist. "
                "For an emergency call **108** (ambulance) or **112**. I can still help with travel information."),
    "medical_emergency": ("This sounds like a medical emergency. **Call 108 (ambulance) or 112 now.** "
                          "If you are at a monument, ask the staff or security for help."),
    "legal": ("I can't give legal advice. For visa or legal matters, contact the Foreigners Regional Registration Office "
              "(FRRO) Hyderabad, your embassy, or a licensed lawyer. Police: 100, emergency: 112."),
    "other_city": ("VisitIQ only covers **Hyderabad** (including Secunderabad). I can't help with {city}. "
                   "Ask me about Hyderabad sights, food, events or transport!"),
    "off_topic": ("That's outside what I can help with. I'm a Hyderabad tourist assistant: ask me about sights, opening "
                  "hours, food, events, transport or a day plan."),
    "greeting": ("Hello! I'm **VisitIQ**, your Hyderabad tourist assistant. Try: *Plan my Friday near Charminar on a "
                 "2,000 rupee budget*, *Is Golconda Fort open on Mondays?* or *Vegetarian restaurants in Banjara Hills under 500*."),
}


def find_terms(text: str, terms: list[str]) -> list[str]:
    """Return terms that appear in `text` as whole words (case-insensitive)."""
    low = text.lower()
    hits = []
    for t in terms:
        if re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", low):
            hits.append(t)
    return hits


def count_terms(text: str, terms: list[str]) -> int:
    """Total number of occurrences of whole-word terms in `text`."""
    low = text.lower()
    return sum(len(re.findall(rf"(?<![a-z]){re.escape(t)}(?![a-z])", low)) for t in terms)


def matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)
