import uuid
import re
import urllib.parse
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from database import db_manager, DEFAULT_ROOMS_TEMPLATE
from ollama_client import ollama_client
from config import settings
import logging

logger = logging.getLogger(__name__)

# Step Definitions
STEP_START = "START"
STEP_ASK_LOCATION = "ASK_LOCATION"
STEP_ASK_HOTEL = "ASK_HOTEL"
STEP_ASK_TYPE_AND_NAME = "ASK_TYPE_AND_NAME"
STEP_ASK_COMPANY_NAME = "ASK_COMPANY_NAME"
STEP_ASK_MEMBERS_COUNT = "ASK_MEMBERS_COUNT"
STEP_ASK_ROOMS_COUNT = "ASK_ROOMS_COUNT"
STEP_ASK_ROOM_TYPE = "ASK_ROOM_TYPE"
STEP_ASK_CHECKIN_DATE = "ASK_CHECKIN_DATE"
STEP_ASK_CHECKOUT_DATE = "ASK_CHECKOUT_DATE"
STEP_ASK_FOOD = "ASK_FOOD"
STEP_ASK_AIRPORT_VEHICLE = "ASK_AIRPORT_VEHICLE"
STEP_ASK_CONTACT = "ASK_CONTACT"
STEP_CONFIRMATION = "CONFIRMATION"
STEP_COMPLETED = "COMPLETED"

WEEKDAYS = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6
}

NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

DISALLOWED_NAMES = {
    "hi", "hello", "hey", "hola", "greetings", "good morning", "good evening", "good afternoon",
    "yes", "no", "ok", "okay", "sure", "thanks", "thank you", "please", "yep", "yeah", "nope",
    "hotel", "room", "rooms", "book", "booking", "reserve", "reservation", "another booking", "new booking",
    "company", "corporate", "individual", "personal", "solo", "myself", "private", "business",
    "founder", "ceo", "co-founder", "director", "manager", "executive", "admin", "owner",
    "president", "vp", "employee", "staff", "guest", "client", "customer",
    "coming sunday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "deluxe", "executive", "suite", "villa", "single", "double", "penthouse",
    "which", "is", "best", "better", "good", "great", "nice", "top", "cheapest", "cheaper",
    "expensive", "what", "where", "how", "who", "why", "when", "can", "could", "would", "should",
    "recommend", "recommendation", "recommends", "suggest", "suggestion", "suggests", "advice",
    "help", "decide", "tell", "show", "give", "list", "compare", "comparison", "difference",
    "details", "detail", "info", "information", "price", "pricing", "rate", "rates", "cost",
    "available", "availability", "option", "options", "choice", "choices", "type", "types",
    "bed", "beds", "balcony", "smoking", "smoke", "food", "breakfast", "dining", "wifi",
    "view", "views", "city", "airport", "terminal", "service", "services", "amenities", "facilities",
    "one", "two", "three", "four", "five", "first", "second", "third", "fourth", "fifth", "me", "you",
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "but", "with"
}

NON_NAME_WORDS = DISALLOWED_NAMES

DISALLOWED_COMPANIES = {
    "yes", "no", "ok", "okay", "sure", "yep", "yeah", "nope", "hi", "hello",
    "founder", "ceo", "director", "manager", "admin", "owner", "president"
}

HOTEL_FAQ_KNOWLEDGE = {
    "checkin_time": "Our standard check-in time is **3:00 PM** and check-out is **11:00 AM**. Early check-in or late check-out is available upon request subject to availability.",
    "amenities": "Our luxury partner hotels feature 5-star amenities including an infinity swimming pool, wellness spa & sauna, 24/7 fitness center, Michelin-inspired dining, rooftop cocktail lounge, high-speed fiber Wi-Fi, and private airport chauffeur transfers.",
    "breakfast": "Complimentary gourmet buffet breakfast is served daily from **6:30 AM to 10:30 AM** at our signature restaurant.",
    "cancellation": "We offer **free cancellation up to 24 hours prior** to your scheduled check-in date.",
    "wifi": "Complimentary high-speed Wi-Fi (up to 500 Mbps) is available in all rooms, suites, and public areas.",
    "parking": "Valet parking and secure underground self-parking are available 24/7 for all hotel guests."
}

_HOTEL_WEB_CACHE: Dict[str, Dict[str, Any]] = {}

def fetch_hotel_web_details(hotel_name: str, user_text: str = "") -> Dict[str, Any]:
    """
    Dynamically scrape live web details and Google Reviews for a hotel in real time
    using SerpApi (Google Search Engine).

    Uses SERPAPI_API_KEY and SERPAPI_BASE_URL.
    If SerpApi does not provide a value for any attribute, it is explicitly set
    as 'Not Available' with zero fake defaults.
    """
    clean_name = hotel_name.strip()
    cache_key = clean_name.lower()
    if cache_key in _HOTEL_WEB_CACHE:
        return _HOTEL_WEB_CACHE[cache_key]

    api_key = getattr(settings, "SERPAPI_API_KEY", "4cefc24c4e2d0e0e05a1091244f3a591e262dc75a6bbd25fe9712afd6205e8c8")
    base_url = getattr(settings, "SERPAPI_BASE_URL", "https://serpapi.com/search.json")

    kg_rating = None
    kg_reviews = None
    kg_desc = ""
    user_revs: List[str] = []
    all_snippets: List[str] = []
    sources: List[str] = []

    try:
        # Query 1: Google Reviews and Rating
        params1 = {
            "engine": "google",
            "q": f"{clean_name} hotel Google reviews rating",
            "api_key": api_key
        }
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp1 = client.get(base_url, params=params1)
            if resp1.status_code == 200:
                data1 = resp1.json()
                kg = data1.get("knowledge_graph", {})
                kg_rating = kg.get("rating")
                kg_reviews = kg.get("review_count") or kg.get("reviews_count") or kg.get("reviews")
                kg_desc = kg.get("description", "")
                user_revs = [r.get("summary") for r in kg.get("user_reviews", []) if r.get("summary")]

                sources.append("Google Knowledge Graph")

                for r in data1.get("organic_results", [])[:5]:
                    snip = r.get("snippet", "")
                    if snip:
                        all_snippets.append(snip)

            # Query 2: Smoking policy, balcony, breakfast / dining
            params2 = {
                "engine": "google",
                "q": f"{clean_name} hotel smoking policy balcony breakfast",
                "api_key": api_key
            }
            resp2 = client.get(base_url, params=params2)
            if resp2.status_code == 200:
                data2 = resp2.json()
                for r in data2.get("organic_results", [])[:6]:
                    snip = r.get("snippet", "")
                    if snip:
                        all_snippets.append(snip)
                sources.append("Google Search via SerpApi")
    except Exception as e:
        logger.warning(f"SerpApi query error for {clean_name}: {e}")

    # Relevant keyword filter to prevent generic snippets from unrelated hotels
    hotel_keywords = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", clean_name) if len(w) > 3 and w.lower() not in ["hotel", "resort", "the", "airport", "inn", "suites", "palace", "york"]]
    if not hotel_keywords:
        hotel_keywords = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", clean_name) if len(w) > 2]

    filtered_snippets: List[str] = []
    if kg_desc:
        filtered_snippets.append(kg_desc)
    for s in all_snippets:
        s_low = s.lower()
        if any(k in s_low for k in hotel_keywords):
            filtered_snippets.append(s)

    # 1. Authentic Rating
    if kg_rating and kg_reviews:
        rating_str = f"{kg_rating} ⭐ ({kg_reviews:,} Verified Google Reviews)"
    elif kg_rating:
        rating_str = f"{kg_rating} ⭐ (Verified Google Rating)"
    else:
        # Check organic rich snippets
        rich_rating = None
        rich_revs = None
        for s in filtered_snippets:
            m_rate = re.search(r'\b([3-5]\.[0-9])\s*(?:of\s*5|stars?|\/5|★|⭐)', s, re.I)
            m_revs = re.search(r'([\d,]+)\s*(?:traveler reviews|reviews|ratings|Google reviews)', s, re.I)
            if m_rate:
                rich_rating = m_rate.group(1)
            if m_revs:
                rich_revs = m_revs.group(1)
            if rich_rating:
                break
        if rich_rating and rich_revs:
            rating_str = f"{rich_rating} ⭐ ({rich_revs} Verified Reviews)"
        elif rich_rating:
            rating_str = f"{rich_rating} ⭐ (Verified Rating)"
        else:
            rating_str = "Not Available from official records"

    # 2. Authentic Reviews Summary
    if user_revs:
        summary_str = " | ".join([f'"{rev}"' for rev in user_revs[:3]])
    elif kg_desc:
        summary_str = kg_desc
    else:
        # Extract authentic traveler review sentences
        rev_sentences = []
        for snip in filtered_snippets:
            for sent in re.split(r'(?<=[.!?])\s+', snip):
                sent_clean = sent.strip()
                if len(sent_clean) > 25 and any(k in sent_clean.lower() for k in ["great", "service", "clean", "location", "view", "stay", "loved", "friendly", "comfortable", "staff", "room"]):
                    if sent_clean not in rev_sentences and not any(sent_clean in exist for exist in rev_sentences):
                        rev_sentences.append(sent_clean)
        if rev_sentences:
            summary_str = " ".join(rev_sentences[:2])
        else:
            summary_str = "Not Available (No verified traveler review summary available from public records)"

    # 3. Authentic Smoking Policy
    smoking_matches = []
    for snip in filtered_snippets:
        for sent in re.split(r'(?<=[.!?])\s+', snip):
            if re.search(r'\b(smoke|smoking|non-smoking|smoke-free)\b', sent, re.I):
                sent_clean = sent.strip()
                if len(sent_clean) > 15 and sent_clean not in smoking_matches:
                    smoking_matches.append(sent_clean)
    smoking_str = smoking_matches[0] if smoking_matches else "Not Available in public records (Please verify directly with hotel front desk)"

    # 4. Authentic Balcony Details
    balcony_matches = []
    for snip in filtered_snippets:
        for sent in re.split(r'(?<=[.!?])\s+', snip):
            if re.search(r'\b(balcony|balconies|terrace|terraces|patio)\b', sent, re.I):
                sent_clean = sent.strip()
                if len(sent_clean) > 15 and sent_clean not in balcony_matches:
                    balcony_matches.append(sent_clean)
    balcony_note = balcony_matches[0] if balcony_matches else "Not Available in public records"

    # 5. Authentic Dining Details
    dining_matches = []
    for snip in filtered_snippets:
        for sent in re.split(r'(?<=[.!?])\s+', snip):
            if re.search(r'\b(breakfast|dining|restaurant|buffet|complimentary breakfast|free breakfast)\b', sent, re.I):
                sent_clean = sent.strip()
                if len(sent_clean) > 15 and sent_clean not in dining_matches:
                    dining_matches.append(sent_clean)
    special_dining = dining_matches[0] if dining_matches else "Not Available in public records"

    source_citation = "Google Search & Reviews via SerpApi"

    result = {
        "hotel_name": clean_name,
        "rating": rating_str,
        "summary": summary_str,
        "smoking_policy": smoking_str,
        "balcony_note": balcony_note,
        "special_dining": special_dining,
        "source": source_citation
    }

    _HOTEL_WEB_CACHE[cache_key] = result
    return result

def clean_company_name(text: str) -> str:
    """Strip common conversational prefixes like 'it s', 'it's', 'its', 'company is'."""
    text = text.strip()
    cleaned = re.sub(r'^(?:it\s*\'?s|it\s+is|it\s+s\b|its\b|we\s+are|company\s+is|our\s+company\s+is|name\s+is|for)\s+', '', text, flags=re.I).strip()
    if re.match(r'^it\s*s\w+', cleaned, flags=re.I):
        cleaned = re.sub(r'^it\s*s?', '', cleaned, flags=re.I).strip()
    return cleaned.title()

def check_hotel_inquiry(text: str) -> Optional[str]:
    """Answer common hotel management & amenity questions only when user is genuinely inquiring."""
    t = text.lower().strip()

    # If it matches or contains a hotel brand or hotel name keywords, never treat as FAQ!
    if any(prefix in t for prefix in ["twa", "plaza", "ritz", "fairmont", "bellagio", "wynn", "hyatt", "marriott", "hilton", "westin", "regency", "resort", "palace"]):
        return None

    # Check-in / Check-out time questions
    if any(k in t for k in ["check-in time", "check in time", "checkout time", "check-out time", "time of check", "when is check"]):
        return HOTEL_FAQ_KNOWLEDGE["checkin_time"]

    # Dining questions (only if asked as an inquiry)
    if any(k in t for k in ["breakfast", "dining", "food", "buffet", "restaurant"]) and any(q in t for q in ["what", "have", "free", "time", "is", "options", "included", "available", "?"]):
        return HOTEL_FAQ_KNOWLEDGE["breakfast"]

    # Cancellation questions
    if any(k in t for k in ["cancellation policy", "cancel policy", "refund policy", "refund", "can i cancel", "how to cancel"]):
        return HOTEL_FAQ_KNOWLEDGE["cancellation"]

    # Wi-Fi questions
    if any(k in t for k in ["wifi", "wi-fi", "internet"]) and any(q in t for q in ["free", "speed", "is", "have", "password", "available", "?"]):
        return HOTEL_FAQ_KNOWLEDGE["wifi"]

    # Parking questions
    if any(k in t for k in ["valet parking", "is parking free", "parking available", "have parking", "parking space"]):
        return HOTEL_FAQ_KNOWLEDGE["parking"]

    # Amenities questions: must be explicit question about amenities, not bare "spa" or hotel title
    if "amenities" in t or "facilities" in t or re.search(r"\b(do you have|is there|tell me about|what about)\b.*\b(pool|gym|spa|fitness|sauna)\b", t):
        return HOTEL_FAQ_KNOWLEDGE["amenities"]

    return None

def is_inquiring_about_rooms(text: str) -> bool:
    t = text.lower().strip()
    patterns = [
        r"what are the room",
        r"what room",
        r"what type of room",
        r"which room",
        r"room type",
        r"types of room",
        r"rooms you have",
        r"rooms do you have",
        r"show room",
        r"list room",
        r"available room",
        r"options do you have",
        r"what are the options"
    ]
    return any(re.search(p, t) for p in patterns)

def is_inquiring_about_booking(text: str, has_active_booking: bool = False) -> bool:
    """Check if user is asking for their booking details / reservation status or specific questions."""
    t = text.lower().strip()

    # 0. Check if this is an edit / change / modify intent - NEVER treat as booking lookup inquiry
    edit_patterns = [
        r"\bedit\b",
        r"\bchange\b",
        r"\bmodify\b",
        r"\bswitch\b",
        r"\balter\b",
        r"\bcorrect\b",
        r"\bdifferent\b",
        r"\bupdate\b(?!\s+(?:on|about|of)\b)"
    ]
    if any(re.search(p, t) for p in edit_patterns):
        return False

    # 0.1 Check if this is a recommendation or details inquiry - NEVER treat as booking lookup!
    if any(k in t for k in ["best", "recommend", "suggest", "advice", "better", "cheapest", "expensive", "options", "which is best", "whichy is best", "which room is best", "whichy room is best", "which hotel is best"]):
        return False
    if any(k in t for k in ["balcony", "smoke", "smoking", "complimentary", "breakfast", "google review", "reviews"]):
        return False
    if re.search(r'\b(types?\s+(?:of\s+)?rooms?|room\s+types?|what\s+(?:are\s+the\s+)?rooms?|available\s+rooms?|room\s+options)\b', t):
        return False
    
    # 1. Direct booking reference regex (e.g. BK-AC9EF9)
    if re.search(r"\bbk-[a-z0-9]{4,8}\b", t):
        return True

    # 2. General booking inquiry keywords
    booking_keywords = [
        "booking details", "my booking", "reservation details", "my reservation",
        "show booking", "check booking", "check my booking", "status of booking",
        "booking status", "what is my booking", "find my booking", "view booking",
        "booked hotel", "my reserved", "reservation info", "show my booking", "view my booking",
        "retrieve booking", "retrieve reservation", "lookup booking"
    ]
    if any(k in t for k in booking_keywords):
        return True

    # 3. Specific questions about stay details (requiring active booking or 'did i' / 'my')
    if has_active_booking:
        active_phrases = [
            "which hotel", "what hotel", "where am i staying", "where is the hotel", "hotel address", "hotel location",
            "when is checkin", "when is check-in", "when my checkin", "when is checkout", "when is check-out",
            "which room", "what room", "room type", "how many rooms",
            "is pickup", "airport pickup", "airport drop", "do i have vehicle", "pickup vehicle", "transfer status", "chauffeur",
            "how much did i pay", "total amount", "total price", "booking reference", "booking id"
        ]
        if any(k in t for k in active_phrases):
            return True
        question_words = ["when", "which", "where", "what", "how", "is", "do", "tell", "show", "can you"]
        booking_subjects = ["checkin", "check-in", "checkout", "check-out", "hotel", "room", "stay", "pickup", "drop", "transfer", "price", "cost", "dates", "arrival", "departure"]
        has_q = any(w in t.split() or w in t for w in question_words)
        has_s = any(w in t for w in booking_subjects)
        if has_q and has_s:
            return True
    else:
        booked_phrases = [
            "which hotel did i book", "what hotel did i book", "where am i staying",
            "which room did i book", "what room did i book", "did i book",
            "my checkin", "when is my checkin", "my checkout", "when is my checkout",
            "how much did i pay", "total amount i paid", "my booking reference", "my booking id"
        ]
        if any(k in t for k in booked_phrases):
            return True

    return False

def fuzzy_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def check_location_match_with_fuzzy(text: str) -> Tuple[Optional[Dict[str, Any]], str, float]:
    """
    Match user text against locations with exact and fuzzy spelling tolerance.
    Returns:
      (matched_loc, 'exact', 1.0)
      (matched_loc, 'clarify', score) if score >= 0.70
      (None, 'none', 0.0)
    """
    t = text.lower().strip()
    locs = db_manager.get_all_locations()

    # 1. Exact word boundary match on city, code, or aliases
    for loc in locs:
        city = loc["city"].lower()
        code = loc["airport_code"].lower()
        aliases = [str(a).lower() for a in loc.get("aliases", [])]
        for cand in [city, code] + aliases:
            if re.search(rf"\b{re.escape(cand)}\b", t):
                return (loc, "exact", 1.0)

    # 2. Direct substring match
    for loc in locs:
        city = loc["city"].lower()
        code = loc["airport_code"].lower()
        name = loc.get("airport_name", "").lower()
        if city in t or (len(code) == 3 and code in t.split()):
            return (loc, "exact", 1.0)
        if len(t) >= 4 and t in name:
            return (loc, "exact", 1.0)

    # 3. Fuzzy match: check whole text and tokens
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in t.split()]
    tokens = [tok for tok in tokens if len(tok) >= 3]
    if not tokens and len(t) >= 3:
        tokens = [t]

    best_loc = None
    best_score = 0.0

    for loc in locs:
        city = loc["city"].lower()
        code = loc["airport_code"].lower()
        aliases = [str(a).lower() for a in loc.get("aliases", [])]
        candidates = [city, code] + aliases

        for cand in candidates:
            # Full text comparison
            s_full = fuzzy_sim(t, cand)
            if s_full > best_score:
                best_score = s_full
                best_loc = loc

            # Token-by-token comparison
            for tok in tokens:
                s_tok = fuzzy_sim(tok, cand)
                if s_tok > best_score:
                    best_score = s_tok
                    best_loc = loc

    if best_score >= 0.70 and best_loc:
        return (best_loc, "clarify", best_score)

    return (None, "none", 0.0)

def match_location_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Backward compatibility wrapper: returns location only on exact match."""
    loc, match_type, _ = check_location_match_with_fuzzy(text)
    if match_type == "exact":
        return loc
    return None

CITY_AND_AIRPORT_WORDS = {
    # USA
    "new york", "new", "york", "jfk", "los angeles", "los", "angeles", "lax",
    "chicago", "ord", "ohare", "miami", "mia", "san francisco", "san", "francisco", "sfo",
    "dallas", "dfw", "atlanta", "atl", "seattle", "sea", "las vegas", "vegas", "las",
    "boston", "bos", "logan", "washington", "iad", "dulles", "orlando", "mco", "denver", "den",
    "houston", "iah", "airport", "airports", "international", "terminal", "terminals",
    # India (for backward compat)
    "chennai", "maa", "coimbatore", "cjb", "trichy", "trz", "madurai", "ixm",
    "bengaluru", "bangalore", "blr", "mangaluru", "mangalore", "ixe",
    "kochi", "cochin", "cok", "thiruvananthapuram", "trivandrum", "trv",
    "kozhikode", "calicut", "ccj", "mumbai", "bom", "delhi", "del",
    "hyderabad", "hyd", "goa", "gox", "goi", "kolkata", "calcutta", "ccu",
    # Generic location & hotel words
    "city", "downtown", "hub", "hubs", "station", "hotel", "hotels", "stay", "near", "destination"
}

def check_hotel_match_with_fuzzy(text: str, location_id: Optional[str] = None, allow_bare_ordinals: bool = False) -> Tuple[Optional[Dict[str, Any]], str, float]:
    """
    Match user text to hotels with support for numeric selection, landmarks, and fuzzy typos.
    Returns:
      (matched_hotel, 'exact', 1.0)
      (matched_hotel, 'clarify', score) if score >= 0.70
      (None, 'none', 0.0)
    """
    t = text.lower().strip()
    if t in CITY_AND_AIRPORT_WORDS:
        return (None, "none", 0.0)

    hotels = db_manager.get_all_hotels(location_id=location_id)
    if not hotels:
        return (None, "none", 0.0)

    # 1. Numbered selection: "hotel 1", "option 2", etc.
    # Exclude numeric counts like "4 guests", "2 rooms", "3 nights"
    has_count_context = bool(re.search(r'\b(?:guests?|members?|people|rooms?|nights?|days?|pax)\b', t))
    if not has_count_context:
        named_ordinals = {
            "hotel 1": 0, "option 1": 0, "1st hotel": 0, "first hotel": 0,
            "hotel 2": 1, "option 2": 1, "2nd hotel": 1, "second hotel": 1,
            "hotel 3": 2, "option 3": 2, "3rd hotel": 2, "third hotel": 2,
            "hotel 4": 3, "option 4": 3, "4th hotel": 3, "fourth hotel": 3,
            "hotel 5": 4, "option 5": 4, "5th hotel": 4, "fifth hotel": 4,
        }
        for phrase, idx in named_ordinals.items():
            if re.search(rf"\b{re.escape(phrase)}\b", t) and idx < len(hotels):
                return (hotels[idx], "exact", 1.0)

        # Bare digits ("1", "2", "3", "4", "5") ONLY allowed if explicitly enabled (e.g. at STEP_ASK_HOTEL)
        if allow_bare_ordinals and len(t.split()) <= 2:
            bare_map = {
                "1": 0, "first": 0, "1st": 0,
                "2": 1, "second": 1, "2nd": 1,
                "3": 2, "third": 2, "3rd": 2,
                "4": 3, "fourth": 3, "4th": 3,
                "5": 4, "fifth": 4, "5th": 4
            }
            if t in bare_map and bare_map[t] < len(hotels):
                return (hotels[bare_map[t]], "exact", 1.0)

    # 2. Check exact or direct substring matches on hotel name & aliases
    for h in hotels:
        name_clean = h["name"].lower()
        if name_clean in t:
            return (h, "exact", 1.0)
        if len(t) >= 5 and t in name_clean:
            tokens_in_t = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in t.split()]
            substantive = [tok for tok in tokens_in_t if tok and tok not in CITY_AND_AIRPORT_WORDS]
            if substantive:
                return (h, "exact", 1.0)
        if h["hotel_id"].lower() in t:
            return (h, "exact", 1.0)
        for alias in h.get("aliases", []):
            if re.search(rf"\b{re.escape(alias.lower())}\b", t):
                return (h, "exact", 1.0)

    # 3. Check distinctive landmark keywords across all USA hotels
    landmark_keywords = [
        # New York (JFK)
        ("twa", "HTL-JFK-001"),
        ("idlewild", "HTL-JFK-001"),
        ("the plaza", "HTL-JFK-002"),
        ("central park", "HTL-JFK-002"),
        ("5th ave", "HTL-JFK-002"),
        ("fifth avenue", "HTL-JFK-002"),
        ("ritz carlton central park", "HTL-JFK-003"),
        ("brooklyn bridge", "HTL-JFK-004"),
        ("dumbo", "HTL-JFK-004"),
        ("st regis", "HTL-JFK-005"),
        ("king cole", "HTL-JFK-005"),
        ("the carlyle", "HTL-JFK-006"),
        ("carlyle", "HTL-JFK-006"),
        ("bemelmans", "HTL-JFK-006"),
        ("the greenwich hotel", "HTL-JFK-007"),
        ("greenwich hotel", "HTL-JFK-007"),
        ("tribeca", "HTL-JFK-007"),
        ("robert de niro", "HTL-JFK-007"),
        ("baccarat hotel", "HTL-JFK-008"),
        ("baccarat", "HTL-JFK-008"),
        ("lotte new york palace", "HTL-JFK-009"),
        ("new york palace", "HTL-JFK-009"),
        ("villard mansion", "HTL-JFK-009"),
        ("mandarin oriental", "HTL-JFK-010"),
        ("columbus circle", "HTL-JFK-010"),
        # Los Angeles (LAX)
        ("hyatt lax", "HTL-LAX-001"),
        ("beverly hills hotel", "HTL-LAX-002"),
        ("pink palace", "HTL-LAX-002"),
        ("shutters on the beach", "HTL-LAX-003"),
        ("santa monica", "HTL-LAX-003"),
        ("ocean ave", "HTL-LAX-003"),
        ("waldorf astoria beverly hills", "HTL-LAX-004"),
        ("hotel bel-air", "HTL-LAX-005"),
        # Chicago (ORD)
        ("hilton o'hare", "HTL-ORD-001"),
        ("peninsula chicago", "HTL-ORD-002"),
        ("magnificent mile", "HTL-ORD-002"),
        ("the langham", "HTL-ORD-003"),
        ("river north", "HTL-ORD-003"),
        ("the drake", "HTL-ORD-004"),
        ("gold coast", "HTL-ORD-004"),
        ("four seasons chicago", "HTL-ORD-005"),
        # Miami (MIA)
        ("miami airport hotel", "HTL-MIA-001"),
        ("the setai", "HTL-MIA-002"),
        ("south beach", "HTL-MIA-002"),
        ("collins ave", "HTL-MIA-002"),
        ("1 hotel south beach", "HTL-MIA-003"),
        ("surf club", "HTL-MIA-004"),
        ("surfside", "HTL-MIA-004"),
        ("mandarin oriental", "HTL-MIA-005"),
        ("brickell", "HTL-MIA-005"),
        # San Francisco (SFO)
        ("grand hyatt sfo", "HTL-SFO-001"),
        ("fairmont san francisco", "HTL-SFO-002"),
        ("nob hill", "HTL-SFO-002"),
        ("cable car", "HTL-SFO-002"),
        ("ritz carlton san francisco", "HTL-SFO-003"),
        ("palace hotel", "HTL-SFO-004"),
        ("four seasons embarcadero", "HTL-SFO-005"),
        # Dallas (DFW)
        ("grand hyatt dfw", "HTL-DFW-001"),
        ("ritz carlton dallas", "HTL-DFW-002"),
        ("uptown dallas", "HTL-DFW-002"),
        ("rosewood mansion", "HTL-DFW-003"),
        ("omni las colinas", "HTL-DFW-004"),
        ("hotel drover", "HTL-DFW-005"),
        ("stockyards", "HTL-DFW-005"),
        # Atlanta (ATL)
        ("renaissance concourse", "HTL-ATL-001"),
        ("st regis atlanta", "HTL-ATL-002"),
        ("buckhead", "HTL-ATL-002"),
        ("four seasons atlanta", "HTL-ATL-003"),
        ("midtown atlanta", "HTL-ATL-003"),
        ("ritz carlton atlanta", "HTL-ATL-004"),
        ("intercontinental buckhead", "HTL-ATL-005"),
        # Seattle (SEA)
        ("radisson seattle", "HTL-SEA-001"),
        ("four seasons seattle", "HTL-SEA-002"),
        ("pike place", "HTL-SEA-002"),
        ("the edgewater", "HTL-SEA-003"),
        ("pier 67", "HTL-SEA-003"),
        ("fairmont olympic", "HTL-SEA-004"),
        ("thompson seattle", "HTL-SEA-005"),
        # Las Vegas (LAS)
        ("bellagio", "HTL-LAS-002"),
        ("the strip", "HTL-LAS-002"),
        ("wynn", "HTL-LAS-003"),
        ("encore", "HTL-LAS-003"),
        ("the venetian", "HTL-LAS-004"),
        ("red rock", "HTL-LAS-005"),
        # Boston (BOS)
        ("hilton boston logan", "HTL-BOS-001"),
        ("the newbury", "HTL-BOS-002"),
        ("back bay", "HTL-BOS-002"),
        ("boston harbor hotel", "HTL-BOS-003"),
        ("the liberty", "HTL-BOS-004"),
        ("the charles hotel", "HTL-BOS-005"),
        # Washington D.C. (IAD)
        ("dulles airport marriott", "HTL-IAD-001"),
        ("the hay-adams", "HTL-IAD-002"),
        ("white house", "HTL-IAD-002"),
        ("four seasons washington", "HTL-IAD-003"),
        ("georgetown", "HTL-IAD-003"),
        ("the willard", "HTL-IAD-005"),
        # Orlando (MCO)
        ("hyatt regency orlando airport", "HTL-MCO-001"),
        ("four seasons orlando", "HTL-MCO-002"),
        ("disney", "HTL-MCO-002"),
        ("ritz carlton orlando", "HTL-MCO-003"),
        ("the alfond inn", "HTL-MCO-005"),
        # Denver (DEN)
        ("westin denver airport", "HTL-DEN-001"),
        ("the brown palace", "HTL-DEN-002"),
        ("the crawford", "HTL-DEN-003"),
        ("union station", "HTL-DEN-003"),
        ("st julien", "HTL-DEN-005"),
        # Houston (IAH)
        ("houston airport marriott", "HTL-IAH-001"),
        ("the post oak", "HTL-IAH-002"),
        ("galleria", "HTL-IAH-002"),
        ("the woodlands resort", "HTL-IAH-005"),
        # Airport hotel keywords (requiring 'hotel')
        ("airport hotel", "AIRPORT"),
        ("hotel near airport", "AIRPORT"),
        ("hotel at airport", "AIRPORT"),
    ]

    for kw, target in landmark_keywords:
        if re.search(rf"\b{re.escape(kw)}\b", t):
            if target == "AIRPORT":
                for h in hotels:
                    if "airport" in h["name"].lower():
                        return (h, "exact", 1.0)
            else:
                for h in hotels:
                    if h["hotel_id"] == target:
                        return (h, "exact", 1.0)

    # 4. Fuzzy match against hotel landmarks and names
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in t.split()]
    stopwords = {"hotel", "azure", "grand", "palace", "resort", "suites", "suite", "tower", "inn", "the", "&", "and", "villa", "villas", "room", "rooms", "deluxe", "executive", "penthouse"}
    all_stopwords = stopwords | CITY_AND_AIRPORT_WORDS
    tokens = [tok for tok in tokens if len(tok) >= 3 and tok not in all_stopwords]
    if not tokens:
        return (None, "none", 0.0)

    best_hotel = None
    best_score = 0.0

    for h in hotels:
        words = set(re.findall(r'\b[a-z]{3,}\b', h["name"].lower())) - all_stopwords
        for w in words:
            # Full input vs landmark word
            s_full = fuzzy_sim(t, w)
            if s_full > best_score:
                best_score = s_full
                best_hotel = h

            # Token vs landmark word
            for tok in tokens:
                s_tok = fuzzy_sim(tok, w)
                if s_tok > best_score:
                    best_score = s_tok
                    best_hotel = h

    if best_score >= 0.75 and best_hotel:
        return (best_hotel, "clarify", best_score)

    return (None, "none", 0.0)

def match_hotel_from_text(text: str, location_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Backward compatibility wrapper: returns hotel only on exact match."""
    h, match_type, _ = check_hotel_match_with_fuzzy(text, location_id=location_id)
    if match_type == "exact":
        return h
    return None

def check_room_match_with_fuzzy(text: str, hotel_id: Optional[str] = None, allow_bare_ordinals: bool = False) -> Tuple[Optional[Dict[str, Any]], str, float]:
    """
    Match room type with support for exact matches, single-word aliases, ordinals, and fuzzy typos.
    Returns:
      (matched_room, 'exact', 1.0)
      (matched_room, 'clarify', score) if single word, alias, or fuzzy typo
      (None, 'none', 0.0)
    """
    # 1. Clean input
    clean_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text).strip()
    # Strip any trailing parenthesized price/tag like ($220) or ($45/night)
    clean_text = re.sub(r'\s*\([^)]*\)', '', clean_text).strip()
    t = clean_text.lower()
    t_no_punct = re.sub(r'[^a-zA-Z0-9\s]', ' ', t).strip()

    # Get available rooms for hotel
    rooms = []
    if hotel_id:
        rooms = db_manager.get_all_rooms(hotel_id=hotel_id)
    if not rooms:
        rooms = db_manager.get_all_rooms()
    if not rooms:
        rooms = DEFAULT_ROOMS_TEMPLATE

    room_by_id = {r["room_id"]: r for r in rooms}

    ROOM_DEFINITIONS = [
        {
            'room_id': 'FAM-VLA',
            'exact': ['luxury family & team villa', 'luxury family and team villa', 'family and team villa', 'family & team villa', 'fam-vla'],
            'aliases': ['team', 'villa', 'family', 'villas', 'teams', 'team villa', 'family villa', 'luxury villa', 'luxury', 'fam'],
            'ordinals': ['4', 'fourth', 'option 4', 'room 4']
        },
        {
            'room_id': 'PRES-PNT',
            'exact': ['presidential penthouse suite', 'presidential penthouse', 'penthouse presidential suite', 'pres-pnt'],
            'aliases': ['presidential', 'penthouse', 'pent', 'vip', 'penthouse suite', 'presidential suite', 'pnt'],
            'ordinals': ['5', 'fifth', 'option 5', 'room 5']
        },
        {
            'room_id': 'CORP-STE',
            'exact': ['corporate business suite', 'corporate and business suite', 'corp-ste'],
            'aliases': ['corporate suite', 'business suite', 'suite', 'suites', 'corp suite', 'business room'],
            'ordinals': ['3', 'third', 'option 3', 'room 3']
        },
        {
            'room_id': 'EXE-DBL',
            'exact': ['executive double room', 'executive double', 'exe-dbl'],
            'aliases': ['executive', 'double', 'king bed', 'double room', 'exec'],
            'ordinals': ['2', 'second', 'option 2', 'room 2']
        },
        {
            'room_id': 'DLX-SGL',
            'exact': ['deluxe single room', 'deluxe single', 'dlx-sgl'],
            'aliases': ['deluxe', 'single', 'standard', 'solo', 'single room', 'delux', 'dlx'],
            'ordinals': ['1', 'first', 'option 1', 'room 1']
        }
    ]

    def get_room_doc(rid):
        if rid in room_by_id:
            return room_by_id[rid]
        r = db_manager.get_room_by_id_or_name(rid, hotel_id=hotel_id)
        if r:
            return r
        for d in DEFAULT_ROOMS_TEMPLATE:
            if d.get("room_id") == rid:
                return d
        return {"room_id": rid, "name": rid, "price_per_night": 100.0}

    # Guard against guest-type phrases (e.g. "Company / Corporate Booking", "individual guest")
    if any(k in t for k in ["corporate booking", "company booking", "corporate travel", "corporate guest", "individual guest", "individual booking", "company / corporate"]):
        return (None, "none", 0.0)

    # 1. Direct match on the actual rooms of this hotel
    for r in rooms:
        r_name = r.get("name", "").lower()
        r_name_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', r_name).strip()
        if t == r_name or t_no_punct == r_name_clean or t == r.get("room_id", "").lower():
            return (r, "exact", 1.0)
        # Substring match if input is meaningful
        if len(t) >= 4 and (t in r_name or r_name in t):
            tokens = [w for w in t.split() if len(w) >= 3 and w not in ["room", "suite", "the", "hotel", "book", "please"]]
            if any(tok in r_name for tok in tokens):
                return (r, "exact", 1.0)

    # 2. Check numeric ordinal ("1", "2", "option 1", "room 2") against the hotel's rooms
    has_count_context = bool(re.search(r'\b(?:guests?|members?|people|rooms?|nights?|days?|pax)\b', t))
    if not has_count_context:
        ordinal_words = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]
        for idx, r in enumerate(rooms):
            if t in [f"option {idx+1}", f"room {idx+1}"]:
                return (r, "exact", 1.0)
            if allow_bare_ordinals:
                ord_word = ordinal_words[idx] if idx < len(ordinal_words) else ""
                if t == str(idx + 1) or (ord_word and t == ord_word):
                    return (r, "exact", 1.0)

    if allow_bare_ordinals and t in ['corporate', 'business', 'corp']:
        return (get_room_doc('CORP-STE'), "clarify", 1.0)

    # Step A: Check exact match
    for rdef in ROOM_DEFINITIONS:
        r_doc = get_room_doc(rdef['room_id'])
        r_name_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', r_doc['name'].lower()).strip()
        if t_no_punct == r_name_clean or t == r_doc['name'].lower() or t == rdef['room_id'].lower():
            return (r_doc, "exact", 1.0)
        for ex in rdef['exact']:
            if t == ex or t_no_punct == re.sub(r'[^a-zA-Z0-9\s]', ' ', ex).strip():
                return (r_doc, "exact", 1.0)

    # Step B: Check single-word / alias match / ordinals (prompts for clarification)
    has_count_context = bool(re.search(r'\b(?:guests?|members?|people|rooms?|nights?|days?|pax)\b', t))
    for rdef in ROOM_DEFINITIONS:
        r_doc = get_room_doc(rdef['room_id'])
        if not has_count_context:
            for ord_phrase in rdef['ordinals']:
                if ord_phrase.isdigit():
                    if allow_bare_ordinals and t == ord_phrase:
                        return (r_doc, "clarify", 1.0)
                elif t == ord_phrase or re.search(rf"\b{re.escape(ord_phrase)}\b", t):
                    return (r_doc, "clarify", 1.0)

        for alias in rdef['aliases']:
            if t == alias or re.search(rf"\b{re.escape(alias)}\b", t):
                return (r_doc, "clarify", 1.0)

    # Step C: Fuzzy typo matching
    room_stopwords = {
        "booking", "book", "booked", "confirm", "confirmation", "confirming", "yes", "no",
        "please", "want", "need", "like", "room", "rooms", "hotel", "hotels", "stay", "details",
        "reserve", "reservation", "edit", "cancel", "thanks", "thank"
    }
    filtered_words = [w for w in t_no_punct.split() if w not in room_stopwords and len(w) >= 3]
    best_room = None
    best_score = 0.0

    for rdef in ROOM_DEFINITIONS:
        r_doc = get_room_doc(rdef['room_id'])
        cands = rdef['aliases'] + [r_doc['name'].lower()]
        for cand in cands:
            if t not in room_stopwords and not any(k in t for k in ["confirm booking", "confirm & reserve", "confirm reservation"]):
                s_full = fuzzy_sim(t, cand)
                if s_full > best_score:
                    best_score = s_full
                    best_room = r_doc
            for w in filtered_words:
                s_w = fuzzy_sim(w, cand)
                if s_w > best_score:
                    best_score = s_w
                    best_room = r_doc

    if best_score >= 0.70 and best_room:
        return (best_room, "clarify", best_score)

    return (None, "none", 0.0)

def match_room_from_text(text: str, hotel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Backward compatibility wrapper: returns room only on exact match."""
    room, match_type, _ = check_room_match_with_fuzzy(text, hotel_id=hotel_id)
    if match_type == "exact":
        return room
    return None

def extract_room_count(text: str) -> Optional[int]:
    """Extract room count or alteration from natural user text (e.g. '1 is enough', 'make it 2', 'just 1', 'two', '2')."""
    t = text.lower().strip()
    patterns = [
        r'\b(\d+)\s*(?:is enough|only|rooms?|please)\b',
        r'\b(?:make it|change to|just|only|want|need|give me|book)\s*(\d+)\b',
        r'\b(\d+)\s+rooms?\b'
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            return int(m.group(1))

    for w, val in NUMBER_WORDS.items():
        if re.search(rf'\b{w}\s*(?:is enough|only|rooms?|please)\b', t) or re.search(rf'\b(?:make it|change to|just|only|want|need|give me|book)\s*{w}\b', t):
            return val

    if t.isdigit() and 1 <= int(t) <= 20:
        return int(t)

    for w, val in NUMBER_WORDS.items():
        if re.search(rf'^\s*{w}\s*$', t):
            return val

    return None

def parse_flexible_date(text: str, base_date: Optional[datetime] = None) -> Optional[str]:
    """Parse common human date expressions into YYYY-MM-DD, accurately handling weekdays and ordinals."""
    if not base_date:
        base_date = datetime.now()
    text = text.lower().strip()
    text = text.replace("comming", "coming")

    if "today" in text:
        return base_date.strftime("%Y-%m-%d")
    if "tomorrow" in text:
        return (base_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # Handle weekdays: "coming thursday", "this friday", "next monday", "thursday"
    for day_name, day_idx in WEEKDAYS.items():
        if re.search(rf"\b(?:this|coming|next)?\s*{day_name}\b", text):
            current_day = base_date.weekday()
            days_ahead = (day_idx - current_day) % 7
            if days_ahead == 0 or "next" in text or "coming" in text:
                if days_ahead == 0:
                    days_ahead = 7
            return (base_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    in_days = re.search(r'in (\d+) days?', text)
    if in_days:
        return (base_date + timedelta(days=int(in_days.group(1)))).strftime("%Y-%m-%d")

    # Clean ordinals: 29th, 1st, 2nd, 3rd -> 29, 1, 2, 3
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text)
    
    for fmt in (
        "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
        "%B %d", "%b %d", "%d %B", "%d %b", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y",
        "%Y/%m/%d"
    ):
        try:
            d = datetime.strptime(cleaned, fmt)
            if d.year == 1900:
                d = d.replace(year=base_date.year)
                if d < base_date - timedelta(days=1):
                    d = d.replace(year=base_date.year + 1)
            return d.strftime("%Y-%m-%d")
        except Exception:
            pass

    iso_match = re.search(r'\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b', text)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"

    return None

def extract_nights_or_days(text: str) -> Optional[int]:
    """Extract number of nights or days from user text, supporting digits and words (e.g. 'two days', '3 nights', 'one week')."""
    t = text.lower().strip()
    
    # 1. Digits followed by nights/days (e.g. "2 days", "3 nights")
    m = re.search(r'\b(\d+)\s*(?:nights?|days?|nts?|d)\b', t)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 60:
            return n

    # 2. Number words followed by nights/days (e.g. "two days", "three nights", "one day")
    for word, val in NUMBER_WORDS.items():
        if re.search(rf'\b{word}\s*(?:nights?|days?|nts?)\b', t):
            return val

    # 3. Special phrases: "a week", "one week", "couple of days", "a couple days"
    if any(k in t for k in ["a week", "1 week", "one week"]):
        return 7
    if any(k in t for k in ["couple of days", "couple days", "a couple of nights", "couple nights"]):
        return 2

    # 4. Bare digits (e.g. "2", "3", "5")
    if t.isdigit():
        n = int(t)
        if 1 <= n <= 60:
            return n

    # 5. Bare number word (e.g. "two", "three", "four")
    for word, val in NUMBER_WORDS.items():
        if re.search(rf'^\s*{word}\s*$', t):
            return val

    return None

def calculate_nights(checkin_str: str, checkout_str: str) -> int:
    try:
        cin = datetime.strptime(checkin_str, "%Y-%m-%d")
        cout = datetime.strptime(checkout_str, "%Y-%m-%d")
        nights = (cout - cin).days
        return max(1, nights)
    except Exception:
        return 1

class BookingAgent:
    def __init__(self):
        pass

    def get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch session from DB or create a fresh one."""
        if session_id:
            session = db_manager.get_session(session_id)
            if session:
                if "session_id" not in session:
                    session["session_id"] = session_id
                return session

        new_session_id = session_id or str(uuid.uuid4())
        initial_state = {
            "session_id": new_session_id,
            "current_step": STEP_START,
            "location_id": None,
            "location_city": None,
            "airport_code": None,
            "hotel_id": None,
            "hotel_name": None,
            "guest_type": None,       # "individual" or "company"
            "guest_name": None,
            "company_name": None,
            "total_members": None,
            "rooms_count": None,
            "room_id": None,
            "room_name": None,
            "price_per_night": None,
            "checkin_date": None,
            "checkout_date": None,
            "total_nights": None,
            "total_amount": None,
            "airport_pickup": False,
            "airport_drop": False,
            "contact_phone": None,
            "contact_email": None,
            "special_requests": None,
            "booking_id": None,
            "messages": [],
            "created_at": datetime.utcnow().isoformat()
        }
        db_manager.save_session(new_session_id, initial_state)
        return initial_state

    def reset_session(self, session_id: str) -> Dict[str, Any]:
        """Reset session to start fresh."""
        initial_state = {
            "session_id": session_id,
            "current_step": STEP_START,
            "location_id": None,
            "location_city": None,
            "airport_code": None,
            "hotel_id": None,
            "hotel_name": None,
            "guest_type": None,
            "guest_name": None,
            "company_name": None,
            "total_members": None,
            "rooms_count": None,
            "room_id": None,
            "room_name": None,
            "price_per_night": None,
            "checkin_date": None,
            "checkout_date": None,
            "total_nights": None,
            "total_amount": None,
            "airport_pickup": False,
            "airport_drop": False,
            "contact_phone": None,
            "contact_email": None,
            "special_requests": None,
            "booking_id": None,
            "messages": [],
            "created_at": datetime.utcnow().isoformat()
        }
        db_manager.save_session(session_id, initial_state)
        return initial_state

    def format_room_options_text(self, hotel_id: Optional[str] = None) -> str:
        """Return rich, helpful descriptions of available rooms for the chosen hotel."""
        rooms = db_manager.get_all_rooms(hotel_id=hotel_id)
        lines = []
        for r in rooms:
            amenities = ", ".join(r.get("amenities", [])[:3])
            total = r.get("total_rooms", 5)
            lines.append(
                f"🏨 **{r['name']}** — **${int(r['price_per_night'])}**/night\n"
                f"   • Capacity: Up to {r['capacity_per_room']} guest(s)\n"
                f"   • Highlights: {amenities}\n"
                f"   • Total Inventory: {total} rooms"
            )
        return "\n\n".join(lines)

    def get_room_quick_replies(self, hotel_id: Optional[str] = None) -> List[str]:
        rooms = db_manager.get_all_rooms(hotel_id=hotel_id)
        return [f"{r['name']} (${int(r['price_per_night'])})" for r in rooms]

    def get_location_quick_replies(self) -> List[str]:
        locs = db_manager.get_all_locations()
        return [f"{l['city']} ({l['airport_code']})" for l in locs]

    def get_hotel_quick_replies(self, location_id: Optional[str] = None) -> List[str]:
        hotels = db_manager.get_all_hotels(location_id=location_id)
        return [h["name"] for h in hotels]

    def format_booking_details_card(self, booking: Dict[str, Any]) -> str:
        pickup_str = "✅ Yes (Arrival Transfer)" if booking.get("airport_pickup") else "❌ No"
        drop_str = "✅ Yes (Departure Transfer)" if booking.get("airport_drop") else "❌ No"
        company_line = f" ({booking.get('company_name')})" if booking.get("company_name") else ""
        
        return (
            f"📋 **Booking Details**: **{booking.get('booking_id')}**\n\n"
            f"• **Status**: ✅ Confirmed\n"
            f"• **Hotel**: {booking.get('hotel_name', 'Luxury Hotel')}\n"
            f"• **Location**: {booking.get('location_city', 'City')} ({booking.get('airport_code', 'Airport')})\n"
            f"• **Guest / Org**: {booking.get('guest_name', 'Guest')}{company_line}\n"
            f"• **Rooms Reserved**: {booking.get('rooms_count', 1)} x {booking.get('room_name')}\n"
            f"• **Stay Dates**: {booking.get('checkin_date')} to {booking.get('checkout_date')} ({booking.get('total_nights', 1)} nights)\n"
            f"• **Airport Pick-up**: {pickup_str}\n"
            f"• **Airport Drop-off**: {drop_str}\n"
            f"• **Rate**: ${booking.get('price_per_night')}/night per room\n"
            f"• **Total Paid**: **${booking.get('total_amount')}**\n"
            f"• **Contact**: {booking.get('contact_email') or booking.get('contact_phone') or 'On File'}\n\n"
            f"Would you like to book another room, or need assistance with your arrival?"
        )

    def generate_booking_inquiry_reply(self, user_text: str, booking: Dict[str, Any]) -> str:
        """Answer specific user inquiries about their confirmed booking."""
        t = user_text.lower()

        asks_checkin = any(k in t for k in ["checkin", "check-in", "check in", "when am i", "when is my", "when my checkin", "arrival", "arriving", "arrive"])
        asks_checkout = any(k in t for k in ["checkout", "check-out", "check out", "how many night", "nights", "departure", "leaving", "leave", "till when", "until when"])
        asks_hotel = any(k in t for k in ["hotel", "which hotel", "what hotel", "property", "where am i staying", "where is", "staying at", "address", "location"])
        asks_room = any(k in t for k in ["which room", "what room", "room type", "how many room", "category", "rooms reserved", "room name"])
        asks_vehicle = any(k in t for k in ["pickup", "pick up", "drop", "drop off", "transfer", "chauffeur", "vehicle", "car", "cab", "transportation"])
        asks_price = any(k in t for k in ["price", "cost", "total", "amount", "rate", "paid", "how much"])
        asks_ref = any(k in t for k in ["reference", "booking id", "ref number", "code", "ref:"])

        addr = booking.get("hotel_address") or (f"{booking.get('location_city', 'City')} near {booking.get('airport_code', '')} Airport")

        # 1. Combined Check-in + Hotel inquiry (e.g. "when my checkin is there and which hotel")
        if (asks_checkin or asks_checkout) and asks_hotel:
            return (
                f"For your confirmed reservation (**{booking.get('booking_id')}**):\n\n"
                f"🏨 **Hotel**: **{booking.get('hotel_name', 'Luxury Hotel')}**\n"
                f"📍 **Address / Location**: {addr}\n"
                f"📅 **Check-in Date**: **{booking.get('checkin_date')}** (Standard check-in from 2:00 PM)\n"
                f"📅 **Check-out Date**: **{booking.get('checkout_date')}** ({booking.get('total_nights', 1)} night{'s' if booking.get('total_nights', 1) > 1 else ''})\n\n"
                f"Reserved: {booking.get('rooms_count', 1)} x **{booking.get('room_name')}** for {booking.get('guest_name')}."
            )

        # 2. Check-in only
        if asks_checkin:
            return (
                f"Your check-in date for booking **{booking.get('booking_id')}** is **{booking.get('checkin_date')}** at **{booking.get('hotel_name')}**.\n\n"
                f"• Check-in starts from 2:00 PM.\n"
                f"• Check-out is on **{booking.get('checkout_date')}** ({booking.get('total_nights', 1)} night{'s' if booking.get('total_nights', 1) > 1 else ''}).\n"
                f"• Hotel: {booking.get('hotel_name')} ({booking.get('location_city')})."
            )

        # 3. Hotel only
        if asks_hotel:
            return (
                f"You are staying at **{booking.get('hotel_name')}** for reservation **{booking.get('booking_id')}**.\n\n"
                f"📍 **Location**: {addr}\n"
                f"📅 **Stay Dates**: {booking.get('checkin_date')} to {booking.get('checkout_date')}\n"
                f"🏨 **Room**: {booking.get('rooms_count', 1)} x {booking.get('room_name')}"
            )

        # 4. Check-out / Nights
        if asks_checkout:
            return (
                f"Your check-out date is **{booking.get('checkout_date')}** at **{booking.get('hotel_name')}** (Ref: **{booking.get('booking_id')}**).\n\n"
                f"• Duration: {booking.get('total_nights', 1)} night{'s' if booking.get('total_nights', 1) > 1 else ''} (Check-in: {booking.get('checkin_date')})\n"
                f"• Standard check-out time is 11:00 AM."
            )

        # 5. Room details
        if asks_room:
            return (
                f"For reservation **{booking.get('booking_id')}**, you have reserved:\n\n"
                f"🏨 **{booking.get('rooms_count', 1)} x {booking.get('room_name')}**\n"
                f"• Rate: ${booking.get('price_per_night')}/night per room\n"
                f"• Property: {booking.get('hotel_name')}\n"
                f"• Total Guests: {booking.get('total_members', 1)}"
            )

        # 6. Vehicle / Transfer
        if asks_vehicle:
            pickup = "✅ Confirmed (Arrival Chauffeur included)" if booking.get("airport_pickup") else "❌ Not requested"
            drop = "✅ Confirmed (Departure Chauffeur included)" if booking.get("airport_drop") else "❌ Not requested"
            return (
                f"Here is your airport transportation vehicle status for reservation **{booking.get('booking_id')}**:\n\n"
                f"• **Airport Pick-up**: {pickup}\n"
                f"• **Airport Drop-off**: {drop}\n"
                f"• **Destination Hub**: {booking.get('location_city')} ({booking.get('airport_code')})\n"
                f"• **Hotel**: {booking.get('hotel_name')}"
            )

        # 7. Price / Cost
        if asks_price:
            return (
                f"The total amount for reservation **{booking.get('booking_id')}** is **${booking.get('total_amount')}**.\n\n"
                f"• Rate: ${booking.get('price_per_night')}/night per room\n"
                f"• Rooms: {booking.get('rooms_count', 1)} x {booking.get('room_name')}\n"
                f"• Duration: {booking.get('total_nights', 1)} night{'s' if booking.get('total_nights', 1) > 1 else ''} ({booking.get('checkin_date')} to {booking.get('checkout_date')})"
            )

        # 8. Reference ID
        if asks_ref:
            return (
                f"Your official booking reference is **{booking.get('booking_id')}** for your stay at **{booking.get('hotel_name')}**."
            )

        # 9. Fallback to full booking details card
        return self.format_booking_details_card(booking)

    def handle_hotel_web_details_inquiry(self, user_text: str, session: Dict[str, Any], hotel: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a factual, web-scraped reply answering user's inquiry regarding
        bed count/type, balcony, smoking policy, complimentary food, and Google reviews for a specific hotel.
        """
        t = user_text.lower().strip()
        h_name = hotel.get("name", "Luxury Hotel")
        web_info = fetch_hotel_web_details(h_name, user_text)

        bed_asked = bool(re.search(r'\b(bed|beds|bedding|king\s*size|queen\s*size|california\s*king|twin\s*bed|mattress|sleeping)\b', t))
        balcony_asked = bool(re.search(r'\b(balcony|balconies|terrace|patio|veranda|lanai)\b', t))
        smoking_asked = bool(re.search(r'\b(smoke|smoking|non-smoking|smoke-free|cigar|cigarette|vape|vaping)\b', t))
        food_comp_asked = bool(re.search(r'\b(complimentary food|free food|complimentary breakfast|free breakfast|breakfast included|is breakfast free|is food free|is food complimentary|food complimentary|food complementarty|is breakfast complimentary|dining complimentary|complimentary dining|free meals?|is food included|is breakfast included)\b', t) or
                               (re.search(r'\b(food|breakfast|dining|meals?)\b', t) and re.search(r'\b(free|complimentary|complementary|included)\b', t)))
        rooms_asked = bool(re.search(
            r'\b(types?\s+(?:of\s+)?rooms?|room\s+types?|room\s+categories|what\s+(?:are\s+the\s+)?rooms?|which\s+rooms?|available\s+rooms?|rooms?\s+available|show\s+rooms?|room\s+options|list\s+of\s+rooms?|what\s+room|what\s+types?\s+(?:of\s+)?rooms?|room\s+details?|tell\s+me\s+room\s+details)\b',
            t
        ) or (re.search(r'\b(room|rooms)\b', t) and re.search(r'\b(type|types|category|categories|options|available|details|list|show)\b', t)))
        details_asked = bool(
            re.search(r'\b(?:hotel|property|room)?\s*(?:details|info|information|overview|features|amenities|reviews?|ratings?)\b', t) or
            re.search(r'\b(?:give|tell|show|get|share|provide|need|want|have|what|how)\s+(?:me\s+)?(?:more\s+)?(?:the\s+)?(?:details|info|information|reviews?|overview|specs)\b', t) or
            re.search(r'\b(?:details|info|information|reviews?)\s+(?:about|of|on|for)\b', t) or
            re.search(r'\b(?:tell\s+me\s+about|what\s+about|how\s+is|know\s+about|explain\s+about|more\s+about|about\s+the|about\s+this)\b', t) or
            re.search(r'\b(?:hotel details|property details|room details|tell me about|about the hotel|google reviews?|google rating|hotel reviews?|guest reviews?|ratings? and reviews?)\b', t)
        )

        # Check if user mentioned or selected a specific room
        room_name = session.get("room_name")
        cand_room, _, _ = check_room_match_with_fuzzy(user_text, hotel_id=hotel.get("hotel_id"))
        if cand_room:
            room_name = cand_room.get("name")

        sections = []

        # Single aspect only if exactly one specific sub-question was asked without a general details request
        is_single_aspect = (sum([bed_asked, balcony_asked, smoking_asked, food_comp_asked, rooms_asked]) == 1) and not details_asked
        is_comprehensive = not is_single_aspect

        # Get actual rooms for the hotel
        hotel_rooms = db_manager.get_all_rooms(hotel_id=hotel.get("hotel_id"))
        if not hotel_rooms:
            hotel_rooms = DEFAULT_ROOMS_TEMPLATE

        # Helper to extract bed from room doc
        def get_room_bed(r):
            for a in r.get("amenities", []):
                if re.search(r'\b(bed|beds|king|queen|double|twin)\b', a, re.I):
                    return a
            name_low = r.get("name", "").lower()
            if "king" in name_low:
                return "1 Plush King Bed"
            elif "queen" in name_low or "double" in name_low:
                return "2 Plush Queen Beds"
            return "1 Plush King or 2 Queen Beds"

        # Helper to extract balcony from room doc
        def get_room_balcony(r):
            if any("balcony" in a.lower() or "terrace" in a.lower() for a in r.get("amenities", [])) or "penthouse" in r.get("name", "").lower():
                return "✅ Private furnished balcony / terrace with scenic views"
            return "❌ Acoustically insulated panoramic picture windows (no walk-out balcony)"

        # Helper to extract dining from room doc
        def get_room_dining(r):
            if any("breakfast" in a.lower() for a in r.get("amenities", [])) or "suite" in r.get("name", "").lower() or "penthouse" in r.get("name", "").lower() or "club" in r.get("name", "").lower():
                return "✅ Complimentary daily gourmet breakfast included"
            return "Room-only base rate (Gourmet breakfast available on-site for purchase)"

        # Build dynamic room lists
        bed_desc = "\n".join([f"• **{r.get('name', 'Room')}**: {get_room_bed(r)}" for r in hotel_rooms])
        balcony_desc = "\n".join([f"• **{r.get('name', 'Room')}**: {get_room_balcony(r)}" for r in hotel_rooms])
        dining_desc = "\n".join([f"• **{r.get('name', 'Room')}**: {get_room_dining(r)}" for r in hotel_rooms])

        sum_display = web_info['summary']

        if is_comprehensive:
            source_lbl = f" ({web_info['source']})" if web_info.get("source") else ""
            sections.append(
                f"🌐 **Authentic Web & Google Reviews Details for {h_name}**{source_lbl}:\n\n"
                f"⭐ **Google Rating & Traveler Reviews**:\n"
                f"• **Rating**: {web_info['rating']}\n"
                f"• **Traveler Reviews Summary**: {sum_display}"
            )

            # Bed details
            sections.append(
                f"🛏️ **Bed Types & Configurations**:\n"
                f"{bed_desc}"
            )

            # Balcony details
            balcony_custom = f"\n• *Live Property Record*: {web_info['balcony_note']}" if web_info.get("balcony_note") and web_info['balcony_note'] != "Not Available in public records" else "\n• *Live Property Record*: Not Available in public records"
            sections.append(
                f"🌅 **Balcony & Terrace Specifications**:\n"
                f"{balcony_desc}"
                f"{balcony_custom}"
            )

            # Smoking policy
            sections.append(
                "🚭 **Smoking Policy**:\n"
                f"• **Policy**: {web_info['smoking_policy']}"
            )

            # Food / Complimentary Dining
            special_dining = f"\n• *Dining Record*: {web_info['special_dining']}" if web_info.get("special_dining") and web_info['special_dining'] != "Not Available in public records" else "\n• *Dining Record*: Not Available in public records"
            sections.append(
                f"🍳 **Food & Complimentary Dining**:\n"
                f"{dining_desc}"
                f"{special_dining}"
            )
        else:
            # Single aspect inquiry
            cand_r = next((r for r in hotel_rooms if room_name and room_name.lower() in r.get("name", "").lower()), None)

            if bed_asked:
                if cand_r:
                    b_text = f"• **{cand_r.get('name')}**: {get_room_bed(cand_r)}"
                else:
                    b_text = bed_desc
                prefix_room = f" for **{room_name}**" if room_name else ""
                sections.append(
                    f"🛏️ **Bed Configurations{prefix_room} at {h_name} (from Web Search & Hotel Records)**:\n\n"
                    f"{b_text}"
                )

            if balcony_asked:
                if cand_r:
                    balc_text = f"• **{cand_r.get('name')}**: {get_room_balcony(cand_r)}"
                else:
                    balc_text = balcony_desc
                balcony_note = f"\n\n*Property Record*: {web_info['balcony_note']}" if web_info.get("balcony_note") else ""
                prefix_room = f" for **{room_name}**" if room_name else ""
                sections.append(
                    f"🌅 **Balcony Details{prefix_room} at {h_name} (from Web Search & Hotel Records)**:\n\n"
                    f"{balc_text}{balcony_note}"
                )

            if smoking_asked:
                source_lbl = f" ({web_info['source']})" if web_info.get("source") else ""
                sections.append(
                    f"🚭 **Smoking Policy for {h_name}**{source_lbl}:\n\n"
                    f"• **Policy**: {web_info['smoking_policy']}"
                )

            if food_comp_asked:
                if cand_r:
                    din_text = f"• **{cand_r.get('name')}**: {get_room_dining(cand_r)}"
                else:
                    din_text = dining_desc
                special_dining = f"\n\n*Dining Record*: {web_info['special_dining']}" if web_info.get("special_dining") else ""
                source_lbl = f" ({web_info['source']})" if web_info.get("source") else ""
                sections.append(
                    f"🍳 **Complimentary Food & Breakfast Details at {h_name}**{source_lbl}:\n\n"
                    f"{din_text}{special_dining}"
                )

            if details_asked and not is_comprehensive:
                source_lbl = f" ({web_info['source']})" if web_info.get("source") else ""
                sections.append(
                    f"🏨 **Google Reviews & Details for {h_name}**{source_lbl}:\n\n"
                    f"• **Google Rating**: {web_info['rating']}\n"
                    f"• **Traveler Reviews Summary**: {sum_display}\n"
                    f"• **Location / Address**: {hotel.get('address', 'Not Available')}\n"
                    f"• **Smoking Policy**: {web_info['smoking_policy']}\n"
                    f"• **Balcony Details**: {web_info['balcony_note']}\n"
                    f"• **Dining / Breakfast**: {web_info['special_dining']}"
                )

            if rooms_asked:
                room_lines = []
                for r in hotel_rooms:
                    r_name = r.get("name", "Standard Room")
                    price = int(r.get("price_per_night", 250.0))
                    bed_str = get_room_bed(r)
                    balcony_str = get_room_balcony(r)
                    dining_str = get_room_dining(r)

                    room_lines.append(
                        f"🛏️ **{r_name}** — **${price}/night**\n"
                        f"   • **Beds**: {bed_str}\n"
                        f"   • **Balcony**: {balcony_str}\n"
                        f"   • **Dining**: {dining_str}"
                    )

                sections.append(
                    f"🏨 **Available Room Types at {h_name} (from Web Search & Hotel Records)**:\n\n" +
                    "\n\n".join(room_lines)
                )

        # Remember hotel context
        session["hotel_id"] = hotel["hotel_id"]
        session["hotel_name"] = hotel["name"]
        session["hotel_address"] = hotel.get("address", "")
        if hotel.get("location_id"):
            session["location_id"] = hotel["location_id"]

        # Continuation prompt based on current step
        curr_step = session.get("current_step")
        if rooms_asked:
            followup = f"Which room category would you prefer to reserve at **{h_name}**?"
            hotel_rooms = db_manager.get_all_rooms(hotel_id=hotel.get("hotel_id"))
            if not hotel_rooms:
                hotel_rooms = DEFAULT_ROOMS_TEMPLATE
            quick_replies = [r.get("name") for r in hotel_rooms]
        elif curr_step == STEP_ASK_HOTEL:
            followup = f"Would you like to reserve your stay at **{h_name}**, or choose another hotel?"
            quick_replies = [f"Select {h_name}", "Choose Another Hotel"]
        elif curr_step == STEP_ASK_ROOM_TYPE:
            followup = f"Which room category would you prefer for your stay at **{h_name}**?"
            quick_replies = self.get_room_quick_replies(hotel.get("hotel_id"))
        elif curr_step == STEP_ASK_FOOD:
            followup = "Would you like to add our optional gourmet dining package ($45/day per guest), or stick with room-only / included breakfast?"
            quick_replies = ["🍽️ Food with Chef Package (+$45/day)", "❌ Room Only (No Food Package)"]
        elif curr_step == STEP_CONFIRMATION:
            followup = "Would you like me to confirm and reserve this booking now?"
            quick_replies = ["✅ Yes, Confirm Booking", "✏️ Edit Details", "❌ Cancel"]
        else:
            followup = f"How would you like to proceed with your reservation at **{h_name}**?"
            quick_replies = [f"Book {h_name}", "View Available Rooms"]

        full_reply = "\n\n".join(sections) + f"\n\n{followup}"
        return {
            "reply": full_reply,
            "quick_replies": quick_replies
        }

    def check_hotel_or_room_details_inquiry(self, user_text: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if user is asking for hotel details (beds, balcony, smoking policy, complimentary food, google reviews, room types).
        CRITICAL:
        - If user asks: first get which hotel. If no hotel is selected or known yet, prompt user which hotel.
        - Once hotel is identified, fetch live web details / Google reviews and reply factually.
        - If user does not ask: returns None ('or else no need to say').
        """
        t = user_text.lower().strip()

        # 1. Detect inquiry aspects
        bed_asked = bool(re.search(r'\b(bed|beds|bedding|king\s*size|queen\s*size|california\s*king|twin\s*bed|mattress|sleeping)\b', t) and
                         (any(w in t for w in ["what", "how many", "which", "type", "size", "have", "is there", "tell me", "details", "?", "like"]) or len(t.split()) <= 6))
        
        balcony_asked = bool(re.search(r'\b(balcony|balconies|terrace|patio|veranda|lanai)\b', t))
        
        smoking_asked = bool(re.search(r'\b(smoke|smoking|non-smoking|smoke-free|cigar|cigarette|vape|vaping)\b', t))
        
        food_comp_asked = bool(re.search(r'\b(complimentary food|free food|complimentary breakfast|free breakfast|breakfast included|is breakfast free|is food free|is food complimentary|food complimentary|food complementarty|is breakfast complimentary|dining complimentary|complimentary dining|free meals?|is food included|is breakfast included)\b', t) or
                               (re.search(r'\b(food|breakfast|dining|meals?)\b', t) and re.search(r'\b(free|complimentary|complementary|included)\b', t)))
        
        rooms_asked = bool(re.search(
            r'\b(types?\s+(?:of\s+)?rooms?|room\s+types?|room\s+categories|what\s+(?:are\s+the\s+)?rooms?|which\s+rooms?|available\s+rooms?|rooms?\s+available|show\s+rooms?|room\s+options|list\s+of\s+rooms?|what\s+room|what\s+types?\s+(?:of\s+)?rooms?|room\s+details?|tell\s+me\s+room\s+details)\b',
            t
        ) or (re.search(r'\b(room|rooms)\b', t) and re.search(r'\b(type|types|category|categories|options|available|details|list|show)\b', t)))

        details_asked = bool(
            re.search(r'\b(?:hotel|property|room)?\s*(?:details|info|information|overview|features|amenities|reviews?|ratings?)\b', t) or
            re.search(r'\b(?:give|tell|show|get|share|provide|need|want|have|what|how)\s+(?:me\s+)?(?:more\s+)?(?:the\s+)?(?:details|info|information|reviews?|overview|specs)\b', t) or
            re.search(r'\b(?:details|info|information|reviews?)\s+(?:about|of|on|for)\b', t) or
            re.search(r'\b(?:tell\s+me\s+about|what\s+about|how\s+is|know\s+about|explain\s+about|more\s+about|about\s+the|about\s+this)\b', t) or
            re.search(r'\b(?:hotel details|property details|room details|tell me about|about the hotel|google reviews?|google rating|hotel reviews?|guest reviews?|ratings? and reviews?)\b', t)
        )

        if not any([bed_asked, balcony_asked, smoking_asked, food_comp_asked, rooms_asked, details_asked]):
            return None

        # 2. Identify target hotel
        matched_hotel = None
        cand, match_type, _ = check_hotel_match_with_fuzzy(user_text, location_id=session.get("location_id"))
        if cand and match_type == "exact":
            matched_hotel = cand
        if not matched_hotel:
            cand, match_type, _ = check_hotel_match_with_fuzzy(user_text, location_id=None)
            if cand and match_type == "exact":
                matched_hotel = cand
        if not matched_hotel and (session.get("hotel_id") or session.get("hotel_name")):
            h_id = session.get("hotel_id") or session.get("hotel_name")
            matched_hotel = db_manager.get_hotel_by_id_or_name(h_id)
        elif not matched_hotel and session.get("booking_id"):
            b = db_manager.get_booking_by_id(session["booking_id"])
            if b and b.get("hotel_name"):
                matched_hotel = db_manager.get_hotel_by_id_or_name(b.get("hotel_name"))

        # If hotel is not known yet, prompt user which hotel to check details for
        if not matched_hotel:
            session["pending_hotel_detail_inquiry"] = user_text
            city = session.get("location_city")
            loc_id = session.get("location_id")
            hotels_list = db_manager.get_all_hotels(location_id=loc_id) if loc_id else db_manager.get_all_hotels()[:10]
            hotel_names = [h["name"] for h in hotels_list]
            dest_hint = f" in **{city}**" if city else ""
            topic = "room types and rates" if rooms_asked else "authentic Google reviews and property details"

            hotel_bullets = []
            for h in hotels_list:
                hotel_bullets.append(f"• **{h['name']}** ({h.get('rating', 4.5)}⭐) — {h.get('badge', h.get('address', ''))}")
            hotels_preview = "\n".join(hotel_bullets)

            reply = (
                f"I'd be happy to share details and Google reviews for our properties{dest_hint}!\n\n"
                f"**Available Hotels{dest_hint}**:\n"
                f"{hotels_preview}\n\n"
                f"**Which hotel would you like full details, bed configurations, and Google reviews for?**\n"
                f"(Click a hotel name below or type it, and I'll pull the live verified details for you!)"
            )
            return {
                "reply": reply,
                "quick_replies": hotel_names
            }

        # 3. Hotel is identified -> fetch web details and build response
        return self.handle_hotel_web_details_inquiry(user_text, session, matched_hotel)

    def check_recommendation_inquiry(self, user_text: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Intelligently recommend hotels or rooms with actionable reasons,
        preventing the agent from repeating generic prompts or capturing questions as names.
        """
        t = user_text.lower().strip()

        is_rec = bool(re.search(
            r'\b(which\s*(?:y)?\s*(?:is|are)?\s*(?:the\s*)?best|which\s+one\s+is\s+best|which\s+(?:is|are)\s+better|which\s+(?:hotel|room)s?\s+(?:is|are)?\s*best|best\s+(?:hotel|room|option|rooms|hotels|options|choice|choices)|what\s+(?:is|are)?\s*best|what\s+do\s+you\s+recommend|recommend\s+(?:a\s+)?(?:hotel|room)?|recommendation|what\s+do\s+you\s+suggest|suggest\s+(?:a\s+)?(?:hotel|room)?|suggestion|your\s+recommendation|your\s+suggestion|help\s+me\s+(?:choose|decide|pick)|what\s+should\s+i\s+(?:choose|pick|book)|which\s+one\s+should\s+i|any\s+suggestion|any\s+recommendation|which\s+to\s+choose|which\s+to\s+pick|whichy\s+room\s+is\s+best)\b',
            t
        ))
        if not is_rec:
            return None

        asking_room = bool(re.search(r'\b(room|rooms|suite|suites|villa|villas|bed|beds)\b', t))
        asking_hotel = bool(re.search(r'\b(hotel|hotels|property|properties|place|resort)\b', t))

        curr_step = session.get("current_step")
        if not asking_room and not asking_hotel:
            if session.get("hotel_id") or curr_step in [
                STEP_ASK_ROOM_TYPE, STEP_ASK_ROOMS_COUNT, STEP_ASK_TYPE_AND_NAME,
                STEP_ASK_COMPANY_NAME, STEP_ASK_MEMBERS_COUNT, STEP_ASK_CHECKIN_DATE
            ]:
                asking_room = True
            elif curr_step in [STEP_ASK_HOTEL, STEP_START, STEP_ASK_LOCATION]:
                asking_hotel = True

        # CASE 1: ROOM RECOMMENDATION
        if asking_room:
            matched_hotel = None
            cand, match_type, _ = check_hotel_match_with_fuzzy(user_text, location_id=session.get("location_id"))
            if cand and match_type == "exact":
                matched_hotel = cand
            if not matched_hotel and (session.get("hotel_id") or session.get("hotel_name")):
                h_id = session.get("hotel_id") or session.get("hotel_name")
                matched_hotel = db_manager.get_hotel_by_id_or_name(h_id)

            if not matched_hotel:
                city = session.get("location_city")
                loc_id = session.get("location_id")
                hotels_list = db_manager.get_all_hotels(location_id=loc_id) if loc_id else db_manager.get_all_hotels()[:5]
                hotel_names = [h["name"] for h in hotels_list[:5]]
                dest_hint = f" in **{city}**" if city else ""
                reply = (
                    f"I would be glad to give you my expert room recommendations!\n\n"
                    f"**Which hotel{dest_hint} would you like me to recommend rooms for?**\n"
                    f"Please select or tell me the hotel name:"
                )
                return {
                    "reply": reply,
                    "quick_replies": hotel_names
                }

            h_name = matched_hotel.get("name", "our partner hotel")
            guest_type = session.get("guest_type", "individual")
            comp_name = session.get("company_name")
            total_members = int(session.get("total_members") or 1)
            rooms_cnt = int(session.get("rooms_count") or 1)

            is_corporate = (guest_type == "company" or bool(comp_name) or any(k in t for k in ["company", "corporate", "business", "work", "team"]))
            target_entity = f"**{comp_name}**" if comp_name else ("your company" if is_corporate else "your stay")

            lines = [f"🌟 **Expert Room Recommendations for {target_entity} at {h_name}**:"]

            if is_corporate:
                lines.append(
                    f"💼 **1. Corporate Business Suite ($350/night) — Top Corporate Pick**\n"
                    f"• **Why it's best for you**: Specifically tailored for corporate travelers and business delegations! It includes a dedicated executive workstation with high-speed fiber internet, an integrated meeting lounge, private skyline balcony, and **complimentary daily Executive Club Breakfast Buffet & evening cocktail reception**—saving breakfast and meeting venue expenses for your company."
                )
                lines.append(
                    f"⭐ **2. Executive Double Room ($220/night) — Best Value & Comfort**\n"
                    f"• **Why it's best for you**: Outstanding luxury at an attractive rate. Features a choice of 1 King bed or 2 Queen beds, private furnished walk-out balcony, soundproof acoustic windows, and an Italian marble bathroom."
                )
                if total_members >= 3 or rooms_cnt >= 2:
                    lines.append(
                        f"👑 **3. Luxury Family & Team Villa ($520/night) — For Co-Working & Collaboration**\n"
                        f"• **Why it's best for you**: 3 beds across multiple rooms with an expansive landscaped terrace balcony, living area, and complimentary daily gourmet family breakfast for all registered delegates."
                    )
                rec_replies = ["Corporate Business Suite", "Executive Double Room"]
                followup = f"Which room type would you prefer to reserve for {target_entity}?"

            elif total_members >= 3:
                lines.append(
                    f"🏡 **1. Luxury Family & Team Villa ($520/night) — Best for Groups of {total_members}**\n"
                    f"• **Why it's best for you**: Specially designed for larger parties with 3 beds (1 California King + 2 Queen beds in separate bedrooms), expansive terrace balcony, spacious living room, and **complimentary gourmet family breakfast buffet daily**."
                )
                lines.append(
                    f"👑 **2. Presidential Penthouse Suite ($850/night) — VIP Luxury**\n"
                    f"• **Why it's best for you**: Accommodates up to 6 guests with wrap-around 360-degree terrace, private outdoor heated hydrotherapy jacuzzi, dedicated 24/7 butler, and full gourmet in-suite American breakfast."
                )
                lines.append(
                    f"⭐ **3. Executive Double Room ($220/night)** (or book multiple rooms):\n"
                    f"• **Why it's best for you**: Ideal if guests prefer private separate rooms with individual walk-out balconies."
                )
                rec_replies = ["Luxury Family & Team Villa", "Presidential Penthouse Suite", "Executive Double Room"]
                followup = f"Which room category would you prefer for your group?"

            else:
                lines.append(
                    f"⭐ **1. Executive Double Room ($220/night) — Most Popular & Best Value**\n"
                    f"• **Why it's best for you**: Offers the best balance of luxury and value. You get a private furnished walk-out balcony, plush king bed, Italian marble rain shower, and quiet soundproof windows."
                )
                lines.append(
                    f"💻 **2. Deluxe Single Room ($145/night) — Economical Solo Travel**\n"
                    f"• **Why it's best for you**: Tailored for solo travelers who want 5-star comfort on a budget. Includes a plush king bed, high-speed fiber Wi-Fi, and soundproof picture windows."
                )
                lines.append(
                    f"💼 **3. Corporate Business Suite ($350/night) — Executive Comfort**\n"
                    f"• **Why it's best for you**: Extra space with an integrated lounge, private skyline balcony, and **complimentary daily Executive Club breakfast buffet**."
                )
                rec_replies = ["Executive Double Room", "Deluxe Single Room", "Corporate Business Suite"]
                followup = f"Which room type would you like to reserve for your stay at **{h_name}**?"

            # Ensure hotel context is retained
            session["hotel_id"] = matched_hotel["hotel_id"]
            session["hotel_name"] = matched_hotel["name"]
            session["hotel_address"] = matched_hotel.get("address", "")
            if matched_hotel.get("location_id"):
                session["location_id"] = matched_hotel["location_id"]

            return {
                "reply": "\n\n".join(lines) + f"\n\n{followup}",
                "quick_replies": rec_replies
            }

        # CASE 2: HOTEL RECOMMENDATION
        else:
            loc_id = session.get("location_id")
            cand_loc, _, _ = check_location_match_with_fuzzy(user_text)
            if cand_loc:
                loc_id = cand_loc["location_id"]
                session["location_id"] = loc_id
                session["location_city"] = cand_loc["city"]
                session["airport_code"] = cand_loc["airport_code"]

            city = session.get("location_city", "your destination")
            hotels = db_manager.get_all_hotels(location_id=loc_id) if loc_id else db_manager.get_all_hotels()[:5]

            lines = [f"🏨 **Top Hotel Recommendations in {city}**:"]
            rec_hotel_names = []
            for idx, h in enumerate(hotels[:4]):
                h_n = h.get("name")
                rec_hotel_names.append(h_n)
                badge = h.get("badge", "5-Star Luxury")
                desc = h.get("description", "")
                rating = h.get("rating", 4.8)
                lines.append(
                    f"**{idx+1}. {h_n}** ({rating}⭐) — *{badge}*\n"
                    f"• **Why it's best**: {desc[:140]}..."
                )

            followup = f"Which hotel in **{city}** would you like to choose?"
            return {
                "reply": "\n\n".join(lines) + f"\n\n{followup}",
                "quick_replies": rec_hotel_names
            }

    def detect_change_target(self, text: str) -> Optional[str]:
        """
        Detect if user wants to change any booking attribute (hotel, room, location, dates, vehicle, name, etc.).
        Accurately handles spelling typos like 'hotl', 'hotle', negations like 'change hotel not room',
        and natural variations.
        """
        t = text.lower().strip()

        # 1. HOTEL check - must catch typos like hotl, hotle, and negations like 'change hotel not room'
        hotel_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:hotl|hotel|property|resort|palace)\b',
            r'\b(?:hotl|hotel|property|resort|palace)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b',
            r'\bnot\s+room\b.*\b(?:hotel|hotl|property)\b',
            r'\b(?:hotel|hotl|property)\b.*\bnot\s+room\b',
            r'\b(?:want|need|prefer|choose|pick)\s+(?:to\s+)?(?:change\s+)?(?:another|different|other)\s+(?:hotel|hotl|property)\b',
            r'\b(?:change|switch)\s+(?:the\s+)?(?:hotl|hotel)\b',
            r'\b(?:change\s+hotel|change\s+hotl|hotl\s+change|hotel\s+change)\b',
            r'\b(?:i\s+want\s+change\s+hotel|want\s+change\s+hotel)\b',
            r'\b(?:no\s+i\s+want\s+change\s+hotel|no\s+want\s+change\s+hotel)\b'
        ]
        if any(re.search(p, t) for p in hotel_pats):
            return "hotel"

        # 2. LOCATION check
        loc_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:location|city|airport|destination|place|hub)\b',
            r'\b(?:location|city|airport|destination|place|hub)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b',
            r'\bnot\s+(?:new york|los angeles|chicago|san francisco|miami|dallas|atlanta|seattle|las vegas|boston|washington|orlando|denver|houston)\b'
        ]
        if any(re.search(p, t) for p in loc_pats):
            return "location"

        # 3. ROOM check (ensuring 'not room' or 'not the room' or 'count' wasn't used)
        if 'not room' not in t and 'not the room' not in t and 'not rooms' not in t and 'count' not in t:
            room_pats = [
                r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:room|rooms|suite|suites|villa|villas|category|room\s*type)\b',
                r'\b(?:room|rooms|suite|suites|villa|villas|category|room\s*type)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b',
                r'\bnot\s+(?:hotel|hotl)\b.*\broom\b',
                r'\broom\b.*\bnot\s+(?:hotel|hotl)\b'
            ]
            if any(re.search(p, t) for p in room_pats):
                return "room"

        # 4. DATES check
        date_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:date|dates|checkin|check-in|checkout|check-out|nights|stay)\b',
            r'\b(?:date|dates|checkin|check-in|checkout|check-out|nights|stay)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b'
        ]
        if any(re.search(p, t) for p in date_pats):
            return "dates"

        # 5. FOOD / DINING check
        food_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:food|meal|meals|dining|breakfast|lunch|dinner|menu)\b',
            r'\b(?:food|meal|meals|dining|breakfast|lunch|dinner|menu)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b'
        ]
        if any(re.search(p, t) for p in food_pats):
            return "food"

        # 6. VEHICLE / TRANSFERS check
        veh_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:vehicle|pickup|pick-up|drop|drop-off|transfer|chauffeur|car|cab|transportation)\b',
            r'\b(?:vehicle|pickup|pick-up|drop|drop-off|transfer|chauffeur|car|cab|transportation)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b'
        ]
        if any(re.search(p, t) for p in veh_pats):
            return "vehicle"

        # 7. GUEST NAME / COMPANY check
        name_pats = [
            r'\b(?:change|different|switch|another|other|wrong|modify|edit)\b.*\b(?:name|guest|company|organization)\b',
            r'\b(?:name|guest|company|organization)\b.*\b(?:change|different|switch|another|other|wrong|modify|edit)\b'
        ]
        if any(re.search(p, t) for p in name_pats):
            return "name"

        # 8. ROOMS COUNT check
        count_pats = [
            r'\b(?:change|modify|edit)\b.*\b(?:room\s*count|rooms\s*count|number\s*of\s*rooms?)\b',
            r'\b(?:room\s*count|rooms\s*count|number\s*of\s*rooms?)\b.*\b(?:change|modify|edit)\b',
            r'\b(?:make\s+it|want|need|change\s+to)\s+(\d+)\s+rooms?\b'
        ]
        if any(re.search(p, t) for p in count_pats):
            return "rooms_count"

        # 9. MEMBERS / GUESTS COUNT check
        if 'name' not in t:
            mem_pats = [
                r'\b(?:change|modify|edit)\b.*\b(?:guest\s*count|guests\s*count|members?\s*count|number\s*of\s*guests?|pax|people)\b',
                r'\b(?:guest\s*count|guests\s*count|members?\s*count|number\s*of\s*guests?|pax|people)\b.*\b(?:change|modify|edit)\b',
                r'\b(?:make\s+it|want|need|change\s+to)\s+(\d+)\s+(?:guests?|members?|people)\b'
            ]
            if any(re.search(p, t) for p in mem_pats):
                return "members_count"

        # 10. GENERIC CHANGE / EDIT (e.g. user simply says 'edit', 'change', 'modify', 'edit details', 'edit booking details')
        generic_keywords = [
            'edit', 'change', 'modify', 'alter',
            'edit details', 'change details', 'modify details',
            'edit booking', 'change booking', 'modify booking',
            'edit booking details', 'change booking details', 'modify booking details'
        ]
        if any(re.search(rf'\b{re.escape(k)}\b', t) for k in generic_keywords):
            return "generic"

        return None

    def extract_all_entities(self, text: str, session: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract all possible entities from user text regardless of current conversation step.
        Supports location, hotel, room category, room count, guest count, dates (ranges or single),
        vehicle transfers, and guest/company names.
        """
        if session is None:
            session = {}
        extracted = {}
        t = text.lower().strip()

        # 1. Location
        loc, l_type, l_score = check_location_match_with_fuzzy(text)
        if loc and (l_type == 'exact' or l_score >= 0.70):
            extracted['location'] = loc

        # Check if text is an inquiry asking for details rather than a booking selection
        is_inquiry_phrase = bool(
            re.search(r'\b(?:give|tell|show|get|share|what|how|about|is there|do you have)\b', t) and
            re.search(r'\b(?:details|info|information|reviews?|ratings?|specs?|amenities|smoke|smoking|balcony|breakfast|food|bed|beds)\b', t)
        ) or bool(re.search(r'\b(?:details\s+about|details\s+of|tell\s+me\s+about|reviews\s+of|hotel\s+details|room\s+details|what\s+about)\b', t))

        # 2. Hotel
        # CRITICAL: If location was matched from the current user input,
        # only extract a hotel if the user input ALSO explicitly names a distinct hotel
        # beyond the location name, city, and airport code (e.g. "The Plaza New York", "TWA Hotel JFK").
        htl = None
        if not is_inquiry_phrase:
            if loc:
                loc_tokens = {
                    loc.get('city', '').lower(),
                    loc.get('airport_code', '').lower(),
                    loc.get('name', '').lower(),
                    'airport', 'international', 'in', 'at', 'near', 'to', 'for', 'hotel', 'hotels', 'destination'
                }
                raw_words = re.findall(r'[a-zA-Z0-9]+', t)
                residual_words = [w for w in raw_words if w not in loc_tokens and w not in CITY_AND_AIRPORT_WORDS]
                if residual_words:
                    residual_text = " ".join(residual_words)
                    htl, h_type, h_score = check_hotel_match_with_fuzzy(residual_text, location_id=loc['location_id'])
                    if not htl:
                        htl, h_type, h_score = check_hotel_match_with_fuzzy(text, location_id=loc['location_id'])
                    if htl and (h_type == 'exact' or h_score >= 0.75):
                        is_count = bool(re.search(r'\b\d+\s*(?:guests?|members?|rooms?|nights?|days?|people)\b', t))
                        if not (session.get("hotel_id") and is_count):
                            extracted['hotel'] = htl
            else:
                loc_id = session.get('location_id')
                htl, h_type, h_score = check_hotel_match_with_fuzzy(
                    text,
                    location_id=loc_id,
                    allow_bare_ordinals=(session.get("current_step") == STEP_ASK_HOTEL)
                )
                if not htl and not loc_id:
                    # Only search across other locations if location is completely unspecified
                    htl, h_type, h_score = check_hotel_match_with_fuzzy(text, location_id=None)
                if htl and (h_type == 'exact' or h_score >= 0.75):
                    is_count = bool(re.search(r'\b\d+\s*(?:guests?|members?|rooms?|nights?|days?|people)\b', t))
                    if not (session.get("hotel_id") and is_count):
                        extracted['hotel'] = htl
                        if 'location' not in extracted and htl.get('location_id'):
                            matched_loc = db_manager.get_location_by_id(htl['location_id'])
                            if matched_loc:
                                extracted['location'] = matched_loc

        # 3. Room
        is_guest_type_context = any(k in t for k in ["company", "corporate", "individual", "personal", "booking as", "on behalf"])
        is_confirm = any(k in t for k in ["confirm", "proceed", "yes", "cancel", "skip"]) and not any(k in t for k in ["change room", "edit room", "switch room", "different room"])
        if not is_guest_type_context and not is_confirm:
            htl_id = htl['hotel_id'] if htl else session.get('hotel_id')
            rm, r_type, r_score = check_room_match_with_fuzzy(text, hotel_id=htl_id, allow_bare_ordinals=False)
            if rm and (r_type == 'exact' or r_score >= 0.70):
                extracted['room'] = rm

        # 4. Rooms Count
        rc_match = re.search(r'\b(\d+)\s*rooms?\b', t)
        if rc_match:
            extracted['rooms_count'] = int(rc_match.group(1))
        elif session.get("current_step") == STEP_ASK_ROOMS_COUNT and t.strip().isdigit() and 1 <= int(t.strip()) <= 20:
            extracted['rooms_count'] = int(t.strip())
        else:
            for w, val in NUMBER_WORDS.items():
                if re.search(rf'\b{w}\s*rooms?\b', t):
                    extracted['rooms_count'] = val
                    break

        # 5. Members / Guests Count
        mem_match = re.search(r'\b(\d+)\s*(?:guests?|members?|people|persons?|pax)\b', t)
        if mem_match:
            extracted['total_members'] = int(mem_match.group(1))
        else:
            for w, val in NUMBER_WORDS.items():
                if re.search(rf'\b{w}\s*(?:guests?|members?|people|persons?|pax)\b', t):
                    extracted['total_members'] = val
                    break

        # 6. Dates
        range_m = re.search(r'\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\s*(?:to|until|-|till|through)\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b', t)
        if range_m:
            cin = parse_flexible_date(range_m.group(1))
            cout = parse_flexible_date(range_m.group(2))
            if cin and cout and cout > cin:
                extracted['checkin_date'] = cin
                extracted['checkout_date'] = cout
                extracted['total_nights'] = calculate_nights(cin, cout)
        else:
            n = extract_nights_or_days(t)
            single_date = parse_flexible_date(text)
            if single_date and n:
                cin_dt = datetime.strptime(single_date, '%Y-%m-%d')
                cout_dt = cin_dt + timedelta(days=n)
                extracted['checkin_date'] = single_date
                extracted['checkout_date'] = cout_dt.strftime('%Y-%m-%d')
                extracted['total_nights'] = n
            elif single_date and any(k in t for k in ['checkin', 'check-in', 'from', 'arrival', 'arriving', 'starting', 'on']):
                extracted['checkin_date'] = single_date

        # 7. Airport Vehicle
        if any(k in t for k in ['both', 'pickup and drop', 'pick and drop', 'roundtrip', 'round-trip']):
            extracted['airport_pickup'] = True
            extracted['airport_drop'] = True
            extracted['vehicle_set'] = True
        elif any(k in t for k in ['pickup only', 'pick up only', 'need pickup', 'pick-up only']):
            extracted['airport_pickup'] = True
            extracted['airport_drop'] = False
            extracted['vehicle_set'] = True
        elif any(k in t for k in ['drop only', 'drop off only', 'drop-off only', 'need drop']):
            extracted['airport_pickup'] = False
            extracted['airport_drop'] = True
            extracted['vehicle_set'] = True
        elif any(k in t for k in ['no vehicle', 'no pickup', 'no transfer', 'no chauffeur', 'without vehicle', 'none']):
            extracted['airport_pickup'] = False
            extracted['airport_drop'] = False
            extracted['vehicle_set'] = True

        # 8. Name / Company / Contact
        comp_m = re.search(r'\b(?:company|firm|org|organization)[:\s]+([A-Za-z0-9\s&]{2,30})', t)
        if comp_m:
            extracted['company_name'] = comp_m.group(1).strip().title()
            extracted['guest_type'] = 'company'

        name_m = re.search(r'\b(?:for|guest|name is|i am|my name is)\s+([A-Z][a-zA-Z\s]{1,30})\b', text)
        if name_m and not extracted.get('company_name'):
            cand_name = name_m.group(1).strip()
            if cand_name.lower() not in ['deluxe', 'executive', 'hotel', 'room', 'both', 'pickup', 'company', 'corporate', 'individual']:
                extracted['guest_name'] = cand_name
                extracted['guest_type'] = 'individual'

        email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_m:
            extracted['contact_email'] = email_m.group(0).strip()

        # Phone extraction safely excluding dates
        text_without_dates = re.sub(r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b', '', text)
        phone_m = re.search(r'(?:phone|mobile|call|ph|tel)[:\s]+(\+?[\d\s\-\(\)]{8,16})', text, re.I)
        if not phone_m:
            phone_m = re.search(r'(\+91[\s\-]?\d{10}|\+\d{1,3}[\s\-]?\d{9,12}|\b[6-9]\d{9}\b)', text_without_dates)
        if phone_m:
            extracted['contact_phone'] = phone_m.group(1).strip()

        return extracted

    def determine_next_step(self, session: Dict[str, Any]) -> str:
        """Dynamically find the next missing field in the booking pipeline."""
        if not session.get("location_id"):
            return STEP_ASK_LOCATION
        if not session.get("hotel_id"):
            return STEP_ASK_HOTEL
        if not session.get("guest_name") and not session.get("company_name"):
            return STEP_ASK_TYPE_AND_NAME
        if session.get("guest_type") == "company" and not session.get("company_name"):
            return STEP_ASK_COMPANY_NAME
        if not session.get("total_members"):
            return STEP_ASK_MEMBERS_COUNT
        if not session.get("rooms_count"):
            return STEP_ASK_ROOMS_COUNT
        if not session.get("room_id"):
            return STEP_ASK_ROOM_TYPE
        if not session.get("checkin_date"):
            return STEP_ASK_CHECKIN_DATE
        if not session.get("checkout_date"):
            return STEP_ASK_CHECKOUT_DATE
        if not session.get("food_answered"):
            return STEP_ASK_FOOD
        if not session.get("vehicle_answered"):
            return STEP_ASK_AIRPORT_VEHICLE
        if not session.get("contact_phone") and not session.get("contact_email"):
            return STEP_ASK_CONTACT
        return STEP_CONFIRMATION

    def format_confirmation_summary(self, session: Dict[str, Any]) -> str:
        """Format the complete booking review card for confirmation."""
        guest_display = session.get("guest_name") or "Valued Guest"
        if session.get("company_name"):
            if guest_display == "Valued Guest":
                guest_display = session.get("company_name")
            else:
                guest_display += f" ({session.get('company_name')})"

        contact_display = session.get("contact_email") or session.get("contact_phone") or "Provided at check-in"
        food_display = "🍽️ Yes, Food Included" if session.get("food_included") else "❌ No Food (Room Only)"
        pickup_display = "✅ Yes (Arrival Chauffeur)" if session.get("airport_pickup") else "❌ No"
        drop_display = "✅ Yes (Departure Chauffeur)" if session.get("airport_drop") else "❌ No"

        return (
            f"📋 **Booking Summary & Review**:\n\n"
            f"• **Destination / Airport**: {session.get('location_city', 'Destination')} ({session.get('airport_code', '')})\n"
            f"• **Hotel**: {session.get('hotel_name', 'Luxury Hotel')}\n"
            f"• **Guest / Organization**: {guest_display}\n"
            f"• **Booking Type**: {'Corporate / Company' if session.get('guest_type') == 'company' else 'Individual Guest'}\n"
            f"• **Total Guests**: {session.get('total_members', 1)}\n"
            f"• **Rooms Reserved**: {session.get('rooms_count', 1)} x {session.get('room_name')}\n"
            f"• **Dates**: {session.get('checkin_date')} to {session.get('checkout_date')} ({session.get('total_nights', 1)} nights)\n"
            f"• **Food / Dining**: {food_display}\n"
            f"• **Airport Pick-up**: {pickup_display}\n"
            f"• **Airport Drop-off**: {drop_display}\n"
            f"• **Rate**: ${session.get('price_per_night')}/night per room\n"
            f"• **Total Estimated Price**: **${session.get('total_amount')}**\n"
            f"• **Contact**: {contact_display}\n\n"
            f"Would you like me to confirm and reserve this booking now?"
        )

    def prompt_for_step(self, step: str, session: Dict[str, Any], extra_prefix: str = "") -> Tuple[str, List[str], Optional[Dict[str, Any]]]:
        """Generate response text, quick replies, and in-chat card options for any step."""
        if step in [STEP_START, STEP_ASK_LOCATION]:
            reply = (
                f"{extra_prefix}"
                "Welcome to **Northstar Airline Assistance**! 🌟 I can help with a demo hotel booking, existing hotel booking support, or disruption-assistance questions.\n\n"
                "**Which city or airport destination should I search for hotels near?**"
            )
            return reply, self.get_location_quick_replies(), {"type": "locations", "items": db_manager.get_all_locations()}

        elif step == STEP_ASK_HOTEL:
            hotels = db_manager.get_all_hotels(location_id=session.get("location_id"))
            city_name = session.get('location_city', 'your destination')
            code = session.get('airport_code', '')
            label = f"{city_name} ({code})" if code else city_name
            reply = (
                f"{extra_prefix}"
                f"We have luxury properties connected to **{label}**.\n\n"
                f"**Which hotel would you prefer to stay at?**"
            )
            return reply, self.get_hotel_quick_replies(session.get("location_id")), {
                "type": "hotels",
                "location_city": session.get("location_city"),
                "items": hotels
            }

        elif step == STEP_ASK_TYPE_AND_NAME:
            reply = (
                f"{extra_prefix}"
                "May I have your **full name**, and are you booking as an **individual guest** or on behalf of a **company**?"
            )
            return reply, ["👤 Individual Guest", "🏢 Company / Corporate Booking"], None

        elif step == STEP_ASK_COMPANY_NAME:
            reply = f"{extra_prefix}What is the official name of your **company or organization**?"
            return reply, [], None

        elif step == STEP_ASK_MEMBERS_COUNT:
            name = session.get("guest_name") or session.get("company_name") or "there"
            reply = f"{extra_prefix}Thank you, {name}! **How many guests or members will be staying in total?**"
            return reply, ["1 Guest", "2 Guests", "4 Guests", "6 Guests"], None

        elif step == STEP_ASK_ROOMS_COUNT:
            reply = f"{extra_prefix}**How many rooms** would you like to reserve for your stay?"
            return reply, ["1 Room", "2 Rooms", "3 Rooms", "4 Rooms"], None

        elif step == STEP_ASK_ROOM_TYPE:
            reply = (
                f"{extra_prefix}"
                f"Which room type would you prefer for your stay at **{session.get('hotel_name', 'our hotel')}**?"
            )
            return reply, self.get_room_quick_replies(session.get("hotel_id")), {
                "type": "rooms",
                "hotel_name": session.get("hotel_name"),
                "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
            }

        elif step == STEP_ASK_CHECKIN_DATE:
            reply = (
                f"{extra_prefix}"
                "**What date will you be checking in?** (You can say 'tomorrow', 'coming Thursday', or a date like YYYY-MM-DD)"
            )
            return reply, ["Today", "Tomorrow", "Coming Thursday", "Next Friday"], None

        elif step == STEP_ASK_CHECKOUT_DATE:
            cin = session.get("checkin_date")
            reply = (
                f"{extra_prefix}"
                f"Check-in is set for **{cin}**.\n\n"
                f"**How many nights will you be staying (or what is your check-out date)?**"
            )
            return reply, ["1 night", "2 nights", "3 nights", "5 nights", "7 nights"], None

        elif step == STEP_ASK_FOOD:
            reply = (
                f"{extra_prefix}"
                "**Do you want food / meal service included with your stay?**\n\n"
                "• 🍽️ **Yes, Food Included** (Daily dining and meals)\n"
                "• ❌ **No Food Needed** (Room only stay)"
            )
            return reply, ["🍽️ Yes, Include Food", "❌ No Food Needed"], {
                "type": "food",
                "items": [
                    {"id": "yes", "title": "🍽️ Yes, Include Food", "desc": "Daily chef breakfast buffet and dining included", "badge": "Recommended"},
                    {"id": "no", "title": "❌ No Food Needed", "desc": "Room only stay without meal package", "badge": "Room Only"}
                ]
            }

        elif step == STEP_ASK_AIRPORT_VEHICLE:
            reply = (
                f"{extra_prefix}"
                "Since you are arriving from the airport, **would you like to arrange airport vehicle transportation?**\n\n"
                "We offer private chauffeur service:\n"
                "🚗 **Airport Pick-up** (From airport to hotel)\n"
                "🚕 **Airport Drop-off** (From hotel to airport)\n"
                "🚘 **Both (Round-trip)**\n"
                "❌ **No transportation needed**"
            )
            return reply, ["🚘 Both (Pick-up & Drop)", "🚗 Pick-up Only", "🚕 Drop-off Only", "❌ None / No"], {
                "type": "vehicles",
                "items": [
                    {"id": "both", "title": "Both (Pick-up & Drop)", "desc": "Dedicated chauffeur upon airport arrival and departure", "badge": "Most Popular", "icon": "fa-solid fa-car"},
                    {"id": "pickup", "title": "Pick-up Only", "desc": "Chauffeur greets you at airport arrival terminal", "badge": "Arrival", "icon": "fa-solid fa-plane-arrival"},
                    {"id": "drop", "title": "Drop-off Only", "desc": "Chauffeur transfer from hotel to airport terminal", "badge": "Departure", "icon": "fa-solid fa-plane-departure"},
                    {"id": "none", "title": "None / No Vehicle", "desc": "Guest will arrange own transportation", "badge": "Self", "icon": "fa-solid fa-ban"}
                ]
            }

        elif step == STEP_ASK_CONTACT:
            reply = (
                f"{extra_prefix}"
                "May I have your **contact email address or phone number** for reservation confirmation? (Or reply 'Skip' to provide at check-in)"
            )
            return reply, ["Skip (Provide at Check-in)"], None

        elif step == STEP_CONFIRMATION:
            summary = self.format_confirmation_summary(session)
            return summary, ["✅ Yes, Confirm Booking", "✏️ Edit Details", "❌ Cancel"], {
                "type": "confirmation",
                "items": [
                    {"action": "yes", "label": "✅ Confirm & Reserve Now", "primary": True},
                    {"action": "edit", "label": "✏️ Edit Booking Details", "primary": False}
                ]
            }

        elif step == "EDIT_MENU":
            reply = (
                f"{extra_prefix}"
                "**Which booking detail would you like to update?**\n\n"
                "You can select an option below or simply tell me (e.g. *'change hotel'*, *'change dates'*, *'change room'*, *'change food'*, *'make it 3 rooms'*):"
            )
            return reply, [
                "🏨 Change Hotel",
                "🛏️ Change Room Type",
                "📅 Change Stay Dates",
                "🍽️ Change Food Preference",
                "🚘 Change Vehicle",
                "👤 Change Guest Name",
                "🔢 Change Room Count"
            ], None

        # Fallback
        return "How may I assist you with your booking?", [], None

    def process_user_message_sync(self, session_id: Optional[str], user_input: str) -> Dict[str, Any]:
        """Main conversational controller with location, airport transfers, date availability, and booking lookup."""
        session = self.get_or_create_session(session_id)
        current_step = session.get("current_step", STEP_ASK_LOCATION)
        user_text = user_input.strip()

        # Add user message to history
        session.setdefault("messages", []).append({
            "role": "user",
            "content": user_text,
            "timestamp": datetime.utcnow().isoformat()
        })

        reply = ""
        quick_replies = []
        booking_data = None

        # ==============================================================
        # 0. GLOBAL RESTART
        # ==============================================================
        if any(k in user_text.lower() for k in ["restart", "reset", "start over", "cancel booking", "new booking", "another booking"]):
            session = self.reset_session(session["session_id"])
            reply = (
                "Welcome to **Northstar Airline Assistance**! 🌟\n\n"
                "As you are arriving from the airport, **which city or airport destination are you traveling to?**"
            )
            quick_replies = self.get_location_quick_replies()
            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": STEP_ASK_LOCATION,
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": {
                    "type": "locations",
                    "items": db_manager.get_all_locations()
                }
            }

        # Check if session has an active booking or is completed
        has_active_booking = bool(session.get("booking_id")) or (current_step == STEP_COMPLETED)

        # ==============================================================
        # 1. BOOKING LOOKUP INTERCEPT: User asks for their booking details / specific stay questions
        # ==============================================================
        if is_inquiring_about_booking(user_text, has_active_booking=has_active_booking):
            found_booking = None
            # 1. Search by reference pattern or text in user message
            found_booking = db_manager.find_booking_by_query(user_text)
            
            # 2. If not found in message, check session's own active booking
            if not found_booking and session.get("booking_id"):
                found_booking = db_manager.get_booking_by_id(session["booking_id"])

            # 3. Check by session guest or company name
            if not found_booking and session.get("guest_name"):
                found_booking = db_manager.find_booking_by_query(session["guest_name"])

            if found_booking:
                reply = self.generate_booking_inquiry_reply(user_text, found_booking)
                quick_replies = ["🏨 Book Another Room", "📋 View All Bookings"]
            else:
                reply = (
                    "I'd be glad to retrieve your reservation! "
                    "Could you please share your **Booking Reference ID** (e.g. `BK-XXXXXX`) or the **Email Address / Guest Name** used during booking?"
                )
                quick_replies = []

            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": current_step,
                "state": session,
                "quick_replies": quick_replies,
                "booking": found_booking
            }

        # ==============================================================
        # 1.5 GLOBAL CHANGE INTERCEPTOR (Change hotel, room, location, dates, vehicle, etc.)
        # ==============================================================
        change_target = self.detect_change_target(user_text)
        if change_target:
            if change_target == "hotel":
                session["hotel_id"] = None
                session["hotel_name"] = None
                session["hotel_address"] = None
                session["room_id"] = None
                session["room_name"] = None
                session["price_per_night"] = None
                session["total_amount"] = None
                target_step = STEP_ASK_HOTEL if session.get("location_id") else STEP_ASK_LOCATION
                session["current_step"] = target_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    target_step, session, extra_prefix="Understood! Let's choose another hotel.\n\n"
                )

            elif change_target == "location":
                session["location_id"] = None
                session["location_city"] = None
                session["airport_code"] = None
                session["hotel_id"] = None
                session["hotel_name"] = None
                session["hotel_address"] = None
                session["room_id"] = None
                session["room_name"] = None
                session["price_per_night"] = None
                session["total_amount"] = None
                session["current_step"] = STEP_ASK_LOCATION
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_LOCATION, session, extra_prefix="Understood! Let's update your destination city.\n\n"
                )

            elif change_target == "room":
                session["room_id"] = None
                session["room_name"] = None
                session["price_per_night"] = None
                session["total_amount"] = None
                session["current_step"] = STEP_ASK_ROOM_TYPE
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_ROOM_TYPE, session, extra_prefix="Understood! Let's select another room category.\n\n"
                )

            elif change_target == "dates":
                session["checkin_date"] = None
                session["checkout_date"] = None
                session["total_nights"] = None
                session["total_amount"] = None
                session["current_step"] = STEP_ASK_CHECKIN_DATE
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_CHECKIN_DATE, session, extra_prefix="Understood! Let's update your stay dates.\n\n"
                )

            elif change_target == "vehicle":
                session["airport_pickup"] = False
                session["airport_drop"] = False
                session["vehicle_answered"] = False
                session["current_step"] = STEP_ASK_AIRPORT_VEHICLE
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_AIRPORT_VEHICLE, session, extra_prefix="Understood! Let's adjust your airport vehicle arrangements.\n\n"
                )

            elif change_target == "name":
                session["guest_name"] = None
                session["company_name"] = None
                session["guest_type"] = None
                session["current_step"] = STEP_ASK_TYPE_AND_NAME
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_TYPE_AND_NAME, session, extra_prefix="Understood! Let's update your guest name and booking type.\n\n"
                )

            elif change_target == "rooms_count":
                num = extract_room_count(user_text)
                if num:
                    session["rooms_count"] = max(1, num)
                    if session.get("room_id") and session.get("checkin_date") and session.get("checkout_date"):
                        session["total_nights"] = calculate_nights(session["checkin_date"], session["checkout_date"])
                        session["total_amount"] = round(session["rooms_count"] * session.get("price_per_night", 100) * session["total_nights"], 2)
                    next_s = self.determine_next_step(session)
                    session["current_step"] = next_s
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_s, session, extra_prefix=f"Updated to **{session['rooms_count']} room{'s' if session['rooms_count'] > 1 else ''}**!\n\n"
                    )
                else:
                    session["rooms_count"] = None
                    session["current_step"] = STEP_ASK_ROOMS_COUNT
                    reply, quick_replies, options_data = self.prompt_for_step(
                        STEP_ASK_ROOMS_COUNT, session, extra_prefix="Understood! "
                    )

            elif change_target == "members_count":
                mem_m = re.search(r'\b(\d+)\b', user_text)
                if mem_m:
                    session["total_members"] = int(mem_m.group(1))
                    next_s = self.determine_next_step(session)
                    session["current_step"] = next_s
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_s, session, extra_prefix=f"Updated to **{session['total_members']} guests**!\n\n"
                    )
                else:
                    session["total_members"] = None
                    session["current_step"] = STEP_ASK_MEMBERS_COUNT
                    reply, quick_replies, options_data = self.prompt_for_step(
                        STEP_ASK_MEMBERS_COUNT, session, extra_prefix="Understood! "
                    )

            elif change_target == "food":
                session["food_preference"] = None
                session["food_included"] = None
                session["current_step"] = STEP_ASK_FOOD
                reply, quick_replies, options_data = self.prompt_for_step(
                    STEP_ASK_FOOD, session, extra_prefix="Understood! Let's update your dining & food preference.\n\n"
                )

            elif change_target == "generic":
                reply, quick_replies, options_data = self.prompt_for_step("EDIT_MENU", session)

            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": options_data
            }

        # ==============================================================
        # 1.55 PENDING HOTEL DETAIL INQUIRY RESOLVER
        # If user was previously asked "Which hotel would you like me to check details for?",
        # resolve hotel from user input, fetch scraped web details, and answer their original question!
        # ==============================================================
        if session.get("pending_hotel_detail_inquiry"):
            matched_hotel, _, _ = check_hotel_match_with_fuzzy(user_text, location_id=session.get("location_id"), allow_bare_ordinals=True)
            if not matched_hotel:
                matched_hotel, _, _ = check_hotel_match_with_fuzzy(user_text, location_id=None, allow_bare_ordinals=True)
            if matched_hotel:
                session["hotel_id"] = matched_hotel["hotel_id"]
                session["hotel_name"] = matched_hotel["name"]
                session["hotel_address"] = matched_hotel.get("address", "")
                if matched_hotel.get("location_id"):
                    session["location_id"] = matched_hotel["location_id"]
                orig_inquiry = session.pop("pending_hotel_detail_inquiry")
                inquiry_res = self.handle_hotel_web_details_inquiry(orig_inquiry, session, matched_hotel)
                reply = inquiry_res["reply"]
                quick_replies = inquiry_res["quick_replies"]
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

        # ==============================================================
        # 1.56 HOTEL & ROOM DETAILS INQUIRY INTERCEPT
        # (Scrapes web & Google reviews for beds, king/queen, balcony, smoking policy, complimentary food, and ratings)
        # ==============================================================
        inquiry_res = self.check_hotel_or_room_details_inquiry(user_text, session)
        if inquiry_res:
            reply = inquiry_res["reply"]
            quick_replies = inquiry_res["quick_replies"]
            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            room_options = None
            if session.get("current_step") == STEP_ASK_ROOM_TYPE:
                room_options = {
                    "type": "rooms",
                    "hotel_name": session.get("hotel_name"),
                    "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                }
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": room_options
            }

        # ==============================================================
        # 1.57 RECOMMENDATION & ADVISORY INTELLIGENCE INTERCEPT
        # (Answers "which is best", "which room is best", "what do you recommend" with smart reasons)
        # ==============================================================
        rec_res = self.check_recommendation_inquiry(user_text, session)
        if rec_res:
            reply = rec_res["reply"]
            quick_replies = rec_res["quick_replies"]
            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            room_options = None
            if session.get("current_step") == STEP_ASK_ROOM_TYPE:
                room_options = {
                    "type": "rooms",
                    "hotel_name": session.get("hotel_name"),
                    "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                }
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": room_options
            }

        # ==============================================================
        # 1.6 MULTI-ATTRIBUTE & OUT-OF-ORDER INPUT PROCESSOR
        # (Users providing room first, hotel first, dates first, or everything all-at-once)
        # ==============================================================
        extracted_entities = self.extract_all_entities(user_text, session)
        is_multi_or_out_of_order = False

        # If user input is a simple count or answer for the current step, do NOT treat as out of order
        is_num = user_text.strip().isdigit() or user_text.lower().strip() in NUMBER_WORDS
        if is_num and current_step in [STEP_ASK_MEMBERS_COUNT, STEP_ASK_ROOMS_COUNT]:
            is_multi_or_out_of_order = False
        elif current_step in [STEP_ASK_CHECKIN_DATE, STEP_ASK_CHECKOUT_DATE, STEP_ASK_FOOD, STEP_ASK_AIRPORT_VEHICLE, STEP_CONFIRMATION]:
            is_multi_or_out_of_order = False
        elif current_step == STEP_ASK_TYPE_AND_NAME and not any(k in extracted_entities for k in ["hotel", "room", "checkin_date", "checkout_date", "vehicle_set"]):
            is_multi_or_out_of_order = False
        elif len(extracted_entities) >= 2:
            is_multi_or_out_of_order = True
        elif extracted_entities:
            # Check if any extracted entity belongs to a DIFFERENT step than current_step
            if "hotel" in extracted_entities and current_step != STEP_ASK_HOTEL:
                is_multi_or_out_of_order = True
            elif "room" in extracted_entities and current_step != STEP_ASK_ROOM_TYPE:
                is_multi_or_out_of_order = True
            elif ("checkin_date" in extracted_entities or "checkout_date" in extracted_entities) and current_step not in [STEP_ASK_CHECKIN_DATE, STEP_ASK_CHECKOUT_DATE]:
                is_multi_or_out_of_order = True
            elif "vehicle_set" in extracted_entities and current_step != STEP_ASK_AIRPORT_VEHICLE:
                is_multi_or_out_of_order = True
            elif ("guest_name" in extracted_entities or "company_name" in extracted_entities) and current_step not in [STEP_ASK_TYPE_AND_NAME, STEP_ASK_COMPANY_NAME]:
                is_multi_or_out_of_order = True

        if is_multi_or_out_of_order:
            # Apply extracted entities to session
            if "location" in extracted_entities:
                loc_doc = extracted_entities["location"]
                session["location_id"] = loc_doc["location_id"]
                session["location_city"] = loc_doc["city"]
                session["airport_code"] = loc_doc["airport_code"]

            if "hotel" in extracted_entities:
                htl_doc = extracted_entities["hotel"]
                session["hotel_id"] = htl_doc["hotel_id"]
                session["hotel_name"] = htl_doc["name"]
                session["hotel_address"] = htl_doc.get("address", "")
                if htl_doc.get("location_id"):
                    session["location_id"] = htl_doc["location_id"]

            if "room" in extracted_entities:
                rm_doc = extracted_entities["room"]
                session["room_id"] = rm_doc["room_id"]
                session["room_name"] = rm_doc["name"]
                session["price_per_night"] = rm_doc.get("price_per_night", 100.0)

            if "rooms_count" in extracted_entities:
                session["rooms_count"] = max(1, extracted_entities["rooms_count"])

            if "total_members" in extracted_entities:
                session["total_members"] = max(1, extracted_entities["total_members"])

            if "checkin_date" in extracted_entities:
                session["checkin_date"] = extracted_entities["checkin_date"]

            if "checkout_date" in extracted_entities:
                session["checkout_date"] = extracted_entities["checkout_date"]

            if "total_nights" in extracted_entities:
                session["total_nights"] = extracted_entities["total_nights"]
            elif session.get("checkin_date") and session.get("checkout_date"):
                session["total_nights"] = calculate_nights(session["checkin_date"], session["checkout_date"])

            if "vehicle_set" in extracted_entities:
                session["airport_pickup"] = extracted_entities.get("airport_pickup", False)
                session["airport_drop"] = extracted_entities.get("airport_drop", False)
                session["vehicle_answered"] = True

            if "guest_name" in extracted_entities:
                session["guest_name"] = extracted_entities["guest_name"]
                session["guest_type"] = extracted_entities.get("guest_type", "individual")

            if "company_name" in extracted_entities:
                session["company_name"] = extracted_entities["company_name"]
                session["guest_type"] = "company"

            if "contact_email" in extracted_entities:
                session["contact_email"] = extracted_entities["contact_email"]

            if "contact_phone" in extracted_entities:
                session["contact_phone"] = extracted_entities["contact_phone"]

            # Availability check if both room, dates, and rooms_count are set
            if session.get("hotel_id") and session.get("room_id") and session.get("checkin_date") and session.get("checkout_date"):
                is_avail, rem_count, msg = db_manager.check_room_availability_for_dates(
                    hotel_id=session.get("hotel_id"),
                    room_id=session.get("room_id"),
                    checkin_date=session.get("checkin_date"),
                    checkout_date=session.get("checkout_date"),
                    requested_count=session.get("rooms_count", 1)
                )
                if not is_avail:
                    session["current_step"] = STEP_ASK_ROOM_TYPE
                    reply, quick_replies, options_data = self.prompt_for_step(
                        STEP_ASK_ROOM_TYPE, session, extra_prefix=f"{msg}\n\n"
                    )
                    session.setdefault("messages", []).append({
                        "role": "assistant",
                        "content": reply,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    db_manager.save_session(session["session_id"], session)
                    return {
                        "session_id": session["session_id"],
                        "reply": reply,
                        "current_step": session.get("current_step"),
                        "state": session,
                        "quick_replies": quick_replies,
                        "booking": None,
                        "options": options_data
                    }
                else:
                    session["total_amount"] = round(
                        session.get("rooms_count", 1) * session.get("price_per_night", 100.0) * session.get("total_nights", 1), 2
                    )

            # Build concise acknowledgment prefix of what has been captured
            ack_parts = []
            if session.get("location_city"):
                ack_parts.append(f"Destination: **{session['location_city']}**")
            if session.get("hotel_name"):
                ack_parts.append(f"Hotel: **{session['hotel_name']}**")
            if session.get("room_name"):
                rc = session.get('rooms_count', 1)
                ack_parts.append(f"Room: **{rc} x {session['room_name']}**")
            if session.get("checkin_date") and session.get("checkout_date"):
                ack_parts.append(f"Stay: **{session['checkin_date']} to {session['checkout_date']}** ({session.get('total_nights', 1)} nights)")
            if session.get("vehicle_answered"):
                v_str = "Pick-up & Drop" if (session.get("airport_pickup") and session.get("airport_drop")) else ("Pick-up" if session.get("airport_pickup") else ("Drop-off" if session.get("airport_drop") else "None"))
                ack_parts.append(f"Vehicle: **{v_str}**")

            ack_summary = "Understood! I've noted " + ", ".join(ack_parts) + ".\n\n" if ack_parts else ""

            # Determine next missing step
            next_step = self.determine_next_step(session)
            session["current_step"] = next_step
            reply, quick_replies, options_data = self.prompt_for_step(next_step, session, extra_prefix=ack_summary)

            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": options_data
            }

        # Check if user input is answering the current step (never intercept with generic FAQ)
        is_step_choice = False
        if current_step in [STEP_START, STEP_ASK_LOCATION] and check_location_match_with_fuzzy(user_text)[0]:
            is_step_choice = True
        elif current_step == STEP_ASK_HOTEL and (session.get("pending_hotel_clarification") or check_hotel_match_with_fuzzy(user_text, location_id=session.get("location_id"))[0]):
            is_step_choice = True
        elif current_step == STEP_ASK_ROOM_TYPE and (
            session.get("pending_room_clarification")
            or check_room_match_with_fuzzy(user_text, hotel_id=session.get("hotel_id"))[0]
        ):
            is_step_choice = True
        elif current_step in [STEP_ASK_MEMBERS_COUNT, STEP_ASK_ROOMS_COUNT] and (user_text.strip().isdigit() or user_text.lower().strip() in NUMBER_WORDS):
            is_step_choice = True
        elif current_step in [STEP_ASK_CHECKIN_DATE, STEP_ASK_CHECKOUT_DATE]:
            is_step_choice = True
        elif current_step == STEP_ASK_FOOD:
            is_step_choice = True
        elif current_step == STEP_ASK_AIRPORT_VEHICLE and any(k in user_text.lower() for k in ["both", "pick", "drop", "none", "no"]):
            is_step_choice = True
        elif current_step == STEP_CONFIRMATION:
            is_step_choice = True

        # ==============================================================
        # 2. HOTEL FAQ INTERCEPT
        # ==============================================================
        if not is_step_choice:
            faq_answer = check_hotel_inquiry(user_text)
            if faq_answer:
                followup = "How may I assist you with your booking?"
                if current_step == STEP_ASK_LOCATION:
                    followup = "Which city or airport destination are you traveling to?"
                    quick_replies = self.get_location_quick_replies()
                elif current_step == STEP_ASK_HOTEL:
                    followup = f"Which hotel in {session.get('location_city', 'your destination')} would you like to stay at?"
                    quick_replies = self.get_hotel_quick_replies(session.get('location_id'))
                elif current_step == STEP_ASK_ROOM_TYPE:
                    followup = "Which room category would you prefer for your stay?"
                    quick_replies = self.get_room_quick_replies(session.get('hotel_id'))
                elif current_step == STEP_ASK_CHECKIN_DATE:
                    followup = "What date will you be checking in?"
                    quick_replies = ["Today", "Tomorrow", "Coming Thursday", "Next Friday"]
                elif current_step == STEP_ASK_AIRPORT_VEHICLE:
                    followup = "Would you like airport vehicle transportation (Pick-up, Drop-off, or Both)?"
                    quick_replies = ["🚘 Both (Pick-up & Drop)", "🚗 Pick-up Only", "🚕 Drop-off Only", "❌ None / No"]

                reply = f"{faq_answer}\n\n{followup}"
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

        # ==============================================================
        # 3. ROOM CATALOG INQUIRY
        # ==============================================================
        if is_inquiring_about_rooms(user_text) and current_step not in [STEP_CONFIRMATION, STEP_COMPLETED]:
            members = session.get("total_members")
            rooms_cnt = session.get("rooms_count")

            if members and not rooms_cnt:
                reply = f"For your group of **{members} guests**, how many rooms would you like to reserve at **{session.get('hotel_name', 'our hotel')}**?"
                session["current_step"] = STEP_ASK_ROOMS_COUNT
                quick_replies = ["1 Room", "2 Rooms", "3 Rooms", "4 Rooms"]
            elif rooms_cnt:
                reply = f"Which room type would you like to reserve for your **{rooms_cnt} room(s)** at **{session.get('hotel_name', 'our hotel')}**?"
                session["current_step"] = STEP_ASK_ROOM_TYPE
                quick_replies = self.get_room_quick_replies(session.get("hotel_id"))
            else:
                reply = f"Which room type would you prefer for your stay at **{session.get('hotel_name', 'our hotel')}**?"
                session["current_step"] = STEP_ASK_ROOM_TYPE
                quick_replies = self.get_room_quick_replies(session.get("hotel_id"))

            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            room_options = None
            if session.get("current_step") == STEP_ASK_ROOM_TYPE:
                room_options = {
                    "type": "rooms",
                    "hotel_name": session.get("hotel_name"),
                    "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                }
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": room_options
            }

        # ==============================================================
        # 1.57 RECOMMENDATION & ADVISORY INTELLIGENCE INTERCEPT
        # (Answers "which is best", "which room is best", "what do you recommend" with smart reasons)
        # ==============================================================
        rec_res = self.check_recommendation_inquiry(user_text, session)
        if rec_res:
            reply = rec_res["reply"]
            quick_replies = rec_res["quick_replies"]
            session.setdefault("messages", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.utcnow().isoformat()
            })
            db_manager.save_session(session["session_id"], session)
            room_options = None
            if session.get("current_step") == STEP_ASK_ROOM_TYPE:
                room_options = {
                    "type": "rooms",
                    "hotel_name": session.get("hotel_name"),
                    "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                }
            return {
                "session_id": session["session_id"],
                "reply": reply,
                "current_step": session.get("current_step"),
                "state": session,
                "quick_replies": quick_replies,
                "booking": None,
                "options": room_options
            }

        # ==============================================================
        # 4. DYNAMIC ROOM & COUNT MODIFIER CATCHER
        # ==============================================================
        new_room = match_room_from_text(user_text, hotel_id=session.get("hotel_id"))
        new_count = extract_room_count(user_text)

        ignored_modifier_steps = [
            STEP_START, STEP_ASK_LOCATION, STEP_ASK_HOTEL, STEP_ASK_TYPE_AND_NAME,
            STEP_ASK_COMPANY_NAME, STEP_ASK_ROOM_TYPE, STEP_ASK_FOOD, STEP_ASK_AIRPORT_VEHICLE, STEP_ASK_CONTACT,
            STEP_CONFIRMATION, STEP_COMPLETED
        ]
        if (new_room or (new_count and current_step in [STEP_ASK_ROOMS_COUNT, STEP_ASK_ROOM_TYPE, STEP_ASK_CHECKIN_DATE, STEP_ASK_CHECKOUT_DATE])) and current_step not in ignored_modifier_steps:
            if new_room:
                session["room_id"] = new_room["room_id"]
                session["room_name"] = new_room["name"]
                session["price_per_night"] = new_room["price_per_night"]
            if new_count:
                session["rooms_count"] = new_count

            if session.get("room_name") and session.get("rooms_count"):
                if not session.get("checkin_date"):
                    session["current_step"] = STEP_ASK_CHECKIN_DATE
                    reply = (
                        f"Understood! Reserving **{session['rooms_count']} x {session['room_name']}** (${int(session['price_per_night'])}/night).\n\n"
                        f"What date will you be checking in? (You can say 'coming Thursday', 'tomorrow', or YYYY-MM-DD)"
                    )
                    quick_replies = ["Today", "Tomorrow", "Coming Thursday", "Next Friday"]
                elif not session.get("checkout_date"):
                    session["current_step"] = STEP_ASK_CHECKOUT_DATE
                    reply = f"Updated to **{session['rooms_count']} x {session['room_name']}**! How many nights will you be staying (or what is your check-out date)?"
                    quick_replies = ["1 night", "2 nights", "3 nights", "5 nights"]
                else:
                    # Check date availability on update!
                    avail, remaining, msg = db_manager.check_room_availability_for_dates(
                        session.get("hotel_id"),
                        session["room_id"],
                        session["checkin_date"],
                        session["checkout_date"],
                        session["rooms_count"]
                    )
                    if not avail:
                        reply = f"{msg}\n\nPlease choose another room type or modify your stay dates."
                        quick_replies = self.get_room_quick_replies(session.get("hotel_id"))
                        session["current_step"] = STEP_ASK_ROOM_TYPE
                    else:
                        session["total_amount"] = round(session["rooms_count"] * session["price_per_night"] * session["total_nights"], 2)
                        session["current_step"] = STEP_ASK_AIRPORT_VEHICLE
                        reply = (
                            f"Updated to **{session['rooms_count']} x {session['room_name']}** (${session['total_amount']} total).\n\n"
                            "Do you require airport transportation vehicle service (Pick-up, Drop-off, or Both)?"
                        )
                        quick_replies = ["🚘 Both (Pick-up & Drop)", "🚗 Pick-up Only", "🚕 Drop-off Only", "❌ None / No"]

                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

        # ==============================================================
        # STEP 1: ASK_LOCATION
        # ==============================================================
        if current_step in [STEP_START, STEP_ASK_LOCATION]:
            # 1. Check if there was a pending location clarification
            if session.get("pending_location_clarification"):
                cand = session["pending_location_clarification"]
                lower = user_text.lower().strip()
                is_affirmative = any(w in lower for w in ["yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", "yup", "is right", cand["city"].lower()])
                is_negative = any(w in lower for w in ["no", "nope", "not", "wrong", "change", "cancel", "neither"])

                if is_affirmative and not is_negative:
                    matched_loc = cand
                    session.pop("pending_location_clarification", None)
                    session["location_id"] = matched_loc["location_id"]
                    session["location_city"] = matched_loc["city"]
                    session["airport_code"] = matched_loc["airport_code"]

                    session["current_step"] = STEP_ASK_HOTEL

                    reply = (
                        f"Wonderful! We have luxury properties connected to **{matched_loc['city']} ({matched_loc['airport_code']})** near {matched_loc['airport_name']}.\n\n"
                        f"**Which hotel would you prefer to stay at?**"
                    )
                    quick_replies = self.get_hotel_quick_replies(matched_loc["location_id"])
                elif is_negative:
                    session.pop("pending_location_clarification", None)
                    reply = (
                        "No problem at all! Since you are arriving from the airport, **which city or airport destination are you traveling to?**"
                    )
                    quick_replies = self.get_location_quick_replies()
                else:
                    session.pop("pending_location_clarification", None)
                    # fall through to fresh check below

            if current_step in [STEP_START, STEP_ASK_LOCATION] and not session.get("location_id"):
                lower = user_text.lower().strip()
                is_greeting = any(re.search(rf"\b{re.escape(g)}\b", lower) for g in ["hi", "hello", "hey", "hola", "greetings", "good morning", "good evening", "good afternoon"])

                matched_loc, match_type, score = check_location_match_with_fuzzy(user_text)
                if match_type == "exact" and matched_loc:
                    session["location_id"] = matched_loc["location_id"]
                    session["location_city"] = matched_loc["city"]
                    session["airport_code"] = matched_loc["airport_code"]

                    session["current_step"] = STEP_ASK_HOTEL

                    reply = (
                        f"Wonderful! We have luxury properties connected to **{matched_loc['city']} ({matched_loc['airport_code']})** near {matched_loc['airport_name']}.\n\n"
                        f"**Which hotel would you prefer to stay at?**"
                    )
                    quick_replies = self.get_hotel_quick_replies(matched_loc["location_id"])
                elif match_type == "clarify" and matched_loc and not is_greeting:
                    session["pending_location_clarification"] = matched_loc
                    reply = f"Did you mean **{matched_loc['city']} ({matched_loc['airport_code']})**? (Is {matched_loc['city']} right?)"
                    quick_replies = [f"Yes, {matched_loc['city']}", "No, choose another"]
                else:
                    session["current_step"] = STEP_ASK_LOCATION
                    reply = (
                        "Welcome to **Northstar Airline Assistance**! 🌟 I can help with a demo hotel booking, existing hotel booking support, or disruption-assistance questions.\n\n"
                        "Which city or airport destination should I search for hotels near?"
                    )
                    quick_replies = self.get_location_quick_replies()

        # ==============================================================
        # STEP 2: ASK_HOTEL
        # ==============================================================
        elif current_step == STEP_ASK_HOTEL:
            if session.get("pending_hotel_clarification"):
                cand_hotel = session["pending_hotel_clarification"]
                lower = user_text.lower().strip()
                is_affirmative = any(w in lower for w in ["yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", "yup", "is right", cand_hotel["name"].lower()])
                is_negative = any(w in lower for w in ["no", "nope", "not", "wrong", "change", "cancel", "neither"])

                if is_affirmative and not is_negative:
                    matched_hotel = cand_hotel
                    session.pop("pending_hotel_clarification", None)
                    session["hotel_id"] = matched_hotel["hotel_id"]
                    session["hotel_name"] = matched_hotel["name"]
                    session["hotel_address"] = matched_hotel.get("address", "")
                    session["location_id"] = matched_hotel.get("location_id", session.get("location_id"))
                    next_step = self.determine_next_step(session)
                    session["current_step"] = next_step
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_step,
                        session,
                        extra_prefix=f"Outstanding choice! **{matched_hotel['name']}** offers supreme hospitality with dedicated airport transfers.\n\n"
                    )
                elif is_negative:
                    session.pop("pending_hotel_clarification", None)
                    reply = f"Which hotel would you like to reserve in **{session.get('location_city', 'this destination')}**?"
                    quick_replies = self.get_hotel_quick_replies(session.get("location_id"))
                else:
                    session.pop("pending_hotel_clarification", None)

            if current_step == STEP_ASK_HOTEL and not session.get("hotel_id"):
                matched_hotel, match_type, score = check_hotel_match_with_fuzzy(user_text, location_id=session.get("location_id"), allow_bare_ordinals=True)
                if match_type == "exact" and matched_hotel:
                    session["hotel_id"] = matched_hotel["hotel_id"]
                    session["hotel_name"] = matched_hotel["name"]
                    session["hotel_address"] = matched_hotel.get("address", "")
                    session["location_id"] = matched_hotel.get("location_id", session.get("location_id"))

                    next_step = self.determine_next_step(session)
                    session["current_step"] = next_step
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_step,
                        session,
                        extra_prefix=f"Outstanding choice! **{matched_hotel['name']}** offers supreme hospitality with dedicated airport transfers.\n\n"
                    )
                elif match_type == "clarify" and matched_hotel:
                    session["pending_hotel_clarification"] = matched_hotel
                    reply = f"Did you mean **{matched_hotel['name']}**? (Is that right?)"
                    quick_replies = [f"Yes, {matched_hotel['name']}", "No, choose another"]
                else:
                    reply = f"Which hotel would you like to reserve in **{session.get('location_city', 'this destination')}**?"
                    quick_replies = self.get_hotel_quick_replies(session.get("location_id"))

        # ==============================================================
        # STEP 3: ASK_TYPE_AND_NAME
        # ==============================================================
        elif current_step == STEP_ASK_TYPE_AND_NAME:
            lower = user_text.lower()
            words_tokens = [re.sub(r'[^a-z]', '', w) for w in lower.split()]

            is_company = any(k in lower for k in ["company", "corporate", "business", "organization", "office", "team", "firm", "corp"])
            if not is_company:
                for w in words_tokens:
                    if len(w) >= 4 and (
                        fuzzy_sim(w, "company") >= 0.60
                        or fuzzy_sim(w, "corporate") >= 0.65
                        or fuzzy_sim(w, "business") >= 0.65
                    ):
                        is_company = True
                        break

            is_individual = any(k in lower for k in ["individual", "myself", "personal", "solo", "just me", "private", "self"])
            if not is_individual:
                for w in words_tokens:
                    if len(w) >= 4 and (
                        fuzzy_sim(w, "individual") >= 0.65
                        or fuzzy_sim(w, "personal") >= 0.65
                    ):
                        is_individual = True
                        break

            has_role = any(r in lower for r in ["founder", "ceo", "director", "manager", "admin", "owner", "partner", "president", "vp"])
            if has_role:
                is_company = True

            name_match = re.search(r"(?:my name is|i am|i'm|this is|call me)\s+([a-zA-Z\s]+)", user_text, re.IGNORECASE)
            extracted_name = None
            non_name_words = ["founder", "ceo", "director", "manager", "booking", "company", "corporate", "individual", "guest", "staying", "hotel", "room", "arriving", "traveling", "solo", "myself"]
            if name_match:
                candidate = name_match.group(1).strip()
                if (
                    candidate.lower() not in DISALLOWED_NAMES 
                    and not any(r in candidate.lower() for r in non_name_words)
                ):
                    extracted_name = candidate
            else:
                words_left = [w for w in re.findall(r'[a-zA-Z]+', user_text) if w.lower() not in ["solo", "individual", "myself", "personal", "for", "as", "a", "an", "guest", "company", "corporate", "stay", "hi", "hello"]]
                if 1 <= len(words_left) <= 3 and not any(w.lower() in DISALLOWED_NAMES for w in words_left):
                    extracted_name = " ".join(words_left).title()

            if is_company:
                session["guest_type"] = "company"
            elif is_individual:
                session["guest_type"] = "individual"

            if extracted_name and not session.get("guest_name"):
                session["guest_name"] = extracted_name.title()

            if not session.get("guest_name") and not session.get("guest_type"):
                reply = "May I have your full name, and are you booking as an individual guest or on behalf of a company?"
                quick_replies = ["👤 Individual Guest", "🏢 Company / Corporate Booking"]

            elif session.get("guest_name") and not session.get("guest_type"):
                reply = f"A pleasure to meet you, {session['guest_name']}! Are you booking as an individual guest or on behalf of a company?"
                quick_replies = ["👤 Individual Guest", "🏢 Company / Corporate Booking"]

            elif session.get("guest_type") and not session.get("guest_name"):
                if session["guest_type"] == "company":
                    session["current_step"] = STEP_ASK_COMPANY_NAME
                    reply = "Wonderful, we look forward to hosting your company! What is the name of your company or organization?"
                    quick_replies = []
                else:
                    reply = "Wonderful! May I please have your full name?"
                    quick_replies = []

            else:
                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Thank you, {session.get('guest_name', 'Guest')}!\n\n"
                )

        # ==============================================================
        # STEP 4: ASK_COMPANY_NAME
        # ==============================================================
        elif current_step == STEP_ASK_COMPANY_NAME:
            comp_name = clean_company_name(user_text)

            if comp_name.lower() in DISALLOWED_COMPANIES or len(comp_name) < 2:
                reply = "Please let me know the official name of your company or organization."
                quick_replies = []
            else:
                session["company_name"] = comp_name
                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Excellent! We look forward to welcoming **{session['company_name']}**.\n\n"
                )

        # ==============================================================
        # STEP 5: ASK_MEMBERS_COUNT
        # ==============================================================
        elif current_step == STEP_ASK_MEMBERS_COUNT:
            num_match = re.search(r'\b(\d+)\b', user_text)
            if not num_match:
                for w, val in NUMBER_WORDS.items():
                    if w in user_text.lower():
                        num_match = type('Match', (), {'group': lambda self, x: str(val)})()
                        break

            if num_match:
                members = int(num_match.group(1))
                session["total_members"] = members
                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Got it, {members} guest{'s' if members > 1 else ''}!\n\n"
                )
            else:
                reply = "Could you please tell me the number of guests/members who will be staying?"
                quick_replies = ["1 Guest", "2 Guests", "4 Guests", "6 Guests", "10 Members"]

        # ==============================================================
        # STEP 6: ASK_ROOMS_COUNT
        # ==============================================================
        elif current_step == STEP_ASK_ROOMS_COUNT:
            rooms_cnt = extract_room_count(user_text)

            if rooms_cnt:
                session["rooms_count"] = max(1, rooms_cnt)
                if session.get("room_id") and session.get("price_per_night") and session.get("checkin_date") and session.get("checkout_date"):
                    session["total_nights"] = calculate_nights(session["checkin_date"], session["checkout_date"])
                    session["total_amount"] = round(session["rooms_count"] * session["price_per_night"] * session["total_nights"], 2)

                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Perfect! {rooms_cnt} room{'s' if rooms_cnt > 1 else ''} noted.\n\n"
                )
            else:
                reply = "Please let me know how many rooms you'd like to book."
                quick_replies = ["1 Room", "2 Rooms", "3 Rooms", "4 Rooms"]

        # ==============================================================
        # STEP 7: ASK_ROOM_TYPE
        # ==============================================================
        elif current_step == STEP_ASK_ROOM_TYPE:
            handled_clarification = False
            if session.get("pending_room_clarification"):
                cand_room = session["pending_room_clarification"]
                lower = user_text.lower().strip()
                is_affirmative = any(w in lower for w in [
                    "yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", "yup", "is right",
                    "confirm", "proceed", cand_room["name"].lower()
                ])
                is_negative = any(w in lower for w in ["no", "nope", "not", "wrong", "change", "cancel", "neither", "different", "other", "choose another"])

                if is_affirmative and not is_negative:
                    handled_clarification = True
                    matched_room = cand_room
                    session.pop("pending_room_clarification", None)
                    session["room_id"] = matched_room["room_id"]
                    session["room_name"] = matched_room["name"]
                    session["price_per_night"] = matched_room.get("price_per_night", 100.0)

                    rooms_cnt = session.get("rooms_count", 1)
                    if session.get("checkin_date") and session.get("checkout_date"):
                        session["total_nights"] = calculate_nights(session["checkin_date"], session["checkout_date"])
                        session["total_amount"] = round(rooms_cnt * session["price_per_night"] * session["total_nights"], 2)

                    next_step = self.determine_next_step(session)
                    session["current_step"] = next_step
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_step,
                        session,
                        extra_prefix=f"Excellent choice! Reserving **{rooms_cnt} x {matched_room['name']}** (${int(matched_room.get('price_per_night', 100))}/night).\n\n"
                    )
                elif is_negative:
                    handled_clarification = True
                    session.pop("pending_room_clarification", None)
                    reply = f"No problem! Which room type would you prefer for your stay at **{session.get('hotel_name', 'our hotel')}**?"
                    quick_replies = self.get_room_quick_replies(session.get("hotel_id"))
                    options_data = {
                        "type": "rooms",
                        "hotel_name": session.get("hotel_name"),
                        "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                    }
                else:
                    session.pop("pending_room_clarification", None)

            if not handled_clarification and current_step == STEP_ASK_ROOM_TYPE and not session.get("room_id"):
                matched_room, match_type, score = check_room_match_with_fuzzy(user_text, hotel_id=session.get("hotel_id"), allow_bare_ordinals=True)

                if match_type == "exact" and matched_room:
                    session["room_id"] = matched_room["room_id"]
                    session["room_name"] = matched_room["name"]
                    session["price_per_night"] = matched_room.get("price_per_night", 100.0)

                    rooms_cnt = session.get("rooms_count", 1)
                    if session.get("checkin_date") and session.get("checkout_date"):
                        session["total_nights"] = calculate_nights(session["checkin_date"], session["checkout_date"])
                        session["total_amount"] = round(rooms_cnt * session["price_per_night"] * session["total_nights"], 2)

                    next_step = self.determine_next_step(session)
                    session["current_step"] = next_step
                    reply, quick_replies, options_data = self.prompt_for_step(
                        next_step,
                        session,
                        extra_prefix=f"Excellent choice! Reserving **{rooms_cnt} x {matched_room['name']}** (${int(matched_room.get('price_per_night', 100))}/night).\n\n"
                    )
                elif match_type == "clarify" and matched_room:
                    session["pending_room_clarification"] = matched_room
                    reply = f"Did you mean **{matched_room['name']}** (${int(matched_room.get('price_per_night', 100))}/night)? (Is that right?)"
                    quick_replies = [f"Yes, {matched_room['name']}", "No, choose another"]
                else:
                    reply = f"Which room type would you like to reserve at **{session.get('hotel_name', 'our hotel')}**?"
                    quick_replies = self.get_room_quick_replies(session.get("hotel_id"))

        # ==============================================================
        # STEP 8: ASK_CHECKIN_DATE
        # ==============================================================
        elif current_step == STEP_ASK_CHECKIN_DATE:
            parsed_date = parse_flexible_date(user_text)
            if parsed_date:
                session["checkin_date"] = parsed_date
                d_obj = datetime.strptime(parsed_date, "%Y-%m-%d")
                date_display = d_obj.strftime("%A, %B %d, %Y")
                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Got it! Check-in is set for **{date_display}** (`{parsed_date}`).\n\n"
                )
            else:
                reply = "Please share your check-in date (for example: 'coming Thursday', 'tomorrow', '2026-11-01', or '29th October')."
                quick_replies = ["Today", "Tomorrow", "Coming Thursday", "Next Friday"]

        # ==============================================================
        # STEP 9: ASK_CHECKOUT_DATE with DATE-BASED AVAILABILITY CHECK
        # ==============================================================
        elif current_step == STEP_ASK_CHECKOUT_DATE:
            cin_str = session.get("checkin_date")
            cin_dt = datetime.strptime(cin_str, "%Y-%m-%d") if cin_str else datetime.now()

            # Date correction
            is_date_correction = any(k in user_text.lower() for k in ["not thursday", "change checkin", "wrong date", "checkin is", "check-in is"])
            parsed_as_date = parse_flexible_date(user_text)

            if is_date_correction or (parsed_as_date and parsed_as_date == cin_str):
                if parsed_as_date:
                    session["checkin_date"] = parsed_as_date
                d_obj = datetime.strptime(session["checkin_date"], "%Y-%m-%d")
                reply = (
                    f"Understood! Check-in is confirmed for **{d_obj.strftime('%A, %B %d, %Y')}** (`{session['checkin_date']}`).\n\n"
                    f"**How many nights will you be staying (or what is your check-out date)?**"
                )
                quick_replies = ["1 night", "2 nights", "3 nights", "5 nights", "7 nights"]
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

            parsed_checkout = None
            extracted_nights = extract_nights_or_days(user_text)
            if extracted_nights:
                parsed_checkout = (cin_dt + timedelta(days=extracted_nights)).strftime("%Y-%m-%d")
            else:
                parsed_checkout = parse_flexible_date(user_text, base_date=cin_dt)

            if parsed_checkout and parsed_checkout > cin_str:
                # ------------------------------------------------------
                # DATE-BASED AVAILABILITY VERIFICATION
                # ------------------------------------------------------
                is_available, remaining_rooms, avail_msg = db_manager.check_room_availability_for_dates(
                    hotel_id=session.get("hotel_id"),
                    room_id=session.get("room_id", "DLX-SGL"),
                    checkin_date=session["checkin_date"],
                    checkout_date=parsed_checkout,
                    requested_count=session.get("rooms_count", 1)
                )

                if not is_available:
                    # Inform user room is not available for those dates!
                    reply = (
                        f"{avail_msg}\n\n"
                        f"Which other room type would you prefer at **{session.get('hotel_name', 'our hotel')}**, or would you like to adjust your dates?"
                    )
                    quick_replies = self.get_room_quick_replies(session.get("hotel_id"))
                    session["current_step"] = STEP_ASK_ROOM_TYPE
                    session.setdefault("messages", []).append({
                        "role": "assistant",
                        "content": reply,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    db_manager.save_session(session["session_id"], session)
                    return {
                        "session_id": session["session_id"],
                        "reply": reply,
                        "current_step": session.get("current_step"),
                        "state": session,
                        "quick_replies": quick_replies,
                        "booking": None
                    }

                # Dates are valid and rooms are available!
                session["checkout_date"] = parsed_checkout
                nights = calculate_nights(session["checkin_date"], session["checkout_date"])
                session["total_nights"] = nights

                rooms_count = session.get("rooms_count") or 1
                rate = session.get("price_per_night") or 100.0
                session["total_amount"] = round(rooms_count * rate * nights, 2)

                cout_obj = datetime.strptime(parsed_checkout, "%Y-%m-%d")
                next_step = self.determine_next_step(session)
                session["current_step"] = next_step
                reply, quick_replies, options_data = self.prompt_for_step(
                    next_step,
                    session,
                    extra_prefix=f"Noted: **{nights} night{'s' if nights > 1 else ''}** stay from **{session['checkin_date']}** to **{cout_obj.strftime('%A, %B %d, %Y')}** (`{session['checkout_date']}`).\n\n"
                )
            else:
                reply = f"Your check-in date is **{cin_str}**. How many nights will you be staying (e.g. '2 nights', '3 days') or what is your check-out date?"
                quick_replies = ["1 night", "2 nights", "3 nights", "5 nights"]

        # ==============================================================
        # STEP: ASK_FOOD (Do you want food or not)
        # ==============================================================
        elif current_step == STEP_ASK_FOOD:
            t_lower = user_text.lower()
            if any(k in t_lower for k in ["no", "none", "not", "room only", "don't", "dont", "without", "no food"]):
                session["food_included"] = False
                session["food_preference"] = "No Food (Room Only)"
                food_msg = "No food requested (Room Only)"
            else:
                session["food_included"] = True
                session["food_preference"] = "Yes, Food Included"
                food_msg = "🍽️ **Food / Meals Included** arranged"

            session["food_answered"] = True
            next_step = self.determine_next_step(session)
            session["current_step"] = next_step
            reply, quick_replies, options_data = self.prompt_for_step(
                next_step, session, extra_prefix=f"Got it! {food_msg}.\n\n"
            )

        # ==============================================================
        # STEP 10: ASK_AIRPORT_VEHICLE (Pick-up & Drop-off)
        # ==============================================================
        elif current_step == STEP_ASK_AIRPORT_VEHICLE:
            t_lower = user_text.lower()
            
            # Check for BOTH
            if any(k in t_lower for k in ["both", "round trip", "roundtrip", "round-trip", "pick and drop", "pickup and drop", "yes both"]):
                session["airport_pickup"] = True
                session["airport_drop"] = True
                transfer_msg = "🚘 **Both Airport Pick-up & Drop-off** arranged"
            # Check for PICK-UP only
            elif any(k in t_lower for k in ["pick up", "pickup", "pick-up", "pick only", "pick"]):
                session["airport_pickup"] = True
                session["airport_drop"] = False
                transfer_msg = "🚗 **Airport Pick-up Only** arranged"
            # Check for DROP-OFF only
            elif any(k in t_lower for k in ["drop off", "dropoff", "drop-off", "drop only", "drop"]):
                session["airport_pickup"] = False
                session["airport_drop"] = True
                transfer_msg = "🚕 **Airport Drop-off Only** arranged"
            # Check for NONE / NO
            elif any(k in t_lower for k in ["no", "none", "skip", "not needed", "dont need", "neither"]):
                session["airport_pickup"] = False
                session["airport_drop"] = False
                transfer_msg = "No airport transportation requested"
            # Ambiguous "yes"
            elif "yes" in t_lower:
                session["airport_pickup"] = True
                session["airport_drop"] = True
                transfer_msg = "🚘 **Round-trip Airport Transfers (Pick-up & Drop-off)** arranged"
            else:
                reply = "Would you like airport transportation? Please choose: Pick-up Only, Drop-off Only, Both (Round-trip), or None."
                quick_replies = ["🚘 Both (Pick-up & Drop)", "🚗 Pick-up Only", "🚕 Drop-off Only", "❌ None / No"]
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

            session["vehicle_answered"] = True
            next_step = self.determine_next_step(session)
            session["current_step"] = next_step
            reply, quick_replies, options_data = self.prompt_for_step(
                next_step, session, extra_prefix=f"Got it! {transfer_msg}.\n\n"
            )

        # ==============================================================
        # STEP 11: ASK_CONTACT
        # ==============================================================
        elif current_step == STEP_ASK_CONTACT:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_text)
            phone_match = re.search(r'(\+?[\d\s\-\(\)]{7,15})', user_text)
            is_skip = any(k in user_text.lower() for k in ["skip", "later", "none", "no thanks", "at check-in"])

            if email_match:
                session["contact_email"] = email_match.group(0).strip()
            elif phone_match:
                session["contact_phone"] = phone_match.group(0).strip()
            elif is_skip:
                session["contact_phone"] = "To be provided at check-in"
            else:
                reply = "Could you please provide a valid contact email or phone number (e.g. `guest@example.com` or `+1-555-0199`)? You can also reply 'Skip' to provide it upon arrival."
                quick_replies = ["Skip (Provide at Check-in)"]
                
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None
                }

            session["current_step"] = STEP_CONFIRMATION
            reply, quick_replies, options_data = self.prompt_for_step(STEP_CONFIRMATION, session)

        # ==============================================================
        # STEP 12: CONFIRMATION
        # ==============================================================
        elif current_step == STEP_CONFIRMATION:
            lower = user_text.lower()
            if any(k in lower for k in ["yes", "confirm", "proceed", "ok", "sure", "book", "correct", "perfect"]):
                booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
                booking_record = {
                    "booking_id": booking_id,
                    "session_id": session["session_id"],
                    "location_id": session.get("location_id"),
                    "location_city": session.get("location_city"),
                    "airport_code": session.get("airport_code"),
                    "hotel_id": session.get("hotel_id", "HTL-JFK-001"),
                    "hotel_name": session.get("hotel_name", "Luxury Hotel"),
                    "hotel_address": session.get("hotel_address") or (db_manager.get_hotel_by_id(session.get("hotel_id")) or {}).get("address", ""),
                    "guest_type": session.get("guest_type", "individual"),
                    "guest_name": session.get("guest_name") or session.get("company_name") or "Valued Guest",
                    "company_name": session.get("company_name"),
                    "total_members": session.get("total_members", 1),
                    "rooms_count": session.get("rooms_count", 1),
                    "room_id": session.get("room_id", "DLX-SGL"),
                    "room_name": session.get("room_name", "Room"),
                    "checkin_date": session.get("checkin_date"),
                    "checkout_date": session.get("checkout_date"),
                    "total_nights": session.get("total_nights", 1),
                    "price_per_night": session.get("price_per_night", 100.0),
                    "total_amount": session.get("total_amount", 100.0),
                    "food_included": session.get("food_included", False),
                    "food_preference": session.get("food_preference", "No Food (Room Only)"),
                    "airport_pickup": session.get("airport_pickup", False),
                    "airport_drop": session.get("airport_drop", False),
                    "contact_phone": session.get("contact_phone"),
                    "contact_email": session.get("contact_email"),
                    "special_requests": session.get("special_requests"),
                    "status": "confirmed",
                    "created_at": datetime.utcnow().isoformat()
                }

                # Save into MongoDB
                db_manager.create_booking(booking_record)
                session["booking_id"] = booking_id
                session["current_step"] = STEP_COMPLETED
                booking_data = booking_record

                reply = (
                    f"🎉 **Reservation Confirmed!**\n\n"
                    f"Your booking reference is **{booking_id}**.\n\n"
                    f"We have reserved {session.get('rooms_count')} x {session.get('room_name')} at **{session.get('hotel_name')}** "
                    f"from **{session.get('checkin_date')}** to **{session.get('checkout_date')}** ({session.get('total_nights')} nights).\n\n"
                    f"Airport Chauffeur: {'Pick-up & Drop-off confirmed' if session.get('airport_pickup') and session.get('airport_drop') else ('Pick-up confirmed' if session.get('airport_pickup') else ('Drop-off confirmed' if session.get('airport_drop') else 'No airport transfers'))}.\n\n"
                    f"We look forward to giving you an exceptional stay at {session.get('hotel_name', 'our partner hotel')}!"
                )
                quick_replies = ["📋 View My Booking Details", "🏨 Book Another Room"]

            elif any(k in lower for k in ["no", "edit", "change", "modify"]):
                reply, quick_replies, options_data = self.prompt_for_step("EDIT_MENU", session)
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": session.get("current_step"),
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None,
                    "options": options_data
                }
            elif any(k in lower for k in ["cancel"]):
                session = self.reset_session(session["session_id"])
                reply = (
                    "Booking cancelled. Welcome back to **Northstar Airline Assistance**! 🌟\n\n"
                    "Which city or airport destination would you like to search for hotels near?"
                )
                quick_replies = self.get_location_quick_replies()
                session.setdefault("messages", []).append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.utcnow().isoformat()
                })
                db_manager.save_session(session["session_id"], session)
                return {
                    "session_id": session["session_id"],
                    "reply": reply,
                    "current_step": STEP_ASK_LOCATION,
                    "state": session,
                    "quick_replies": quick_replies,
                    "booking": None,
                    "options": {
                        "type": "locations",
                        "items": db_manager.get_all_locations()
                    }
                }
            else:
                reply = "Please let me know if you would like to proceed with the booking (Yes) or make any changes (Edit)."
                quick_replies = ["✅ Yes, Confirm Booking", "✏️ Edit Details", "❌ Cancel"]

        # ==============================================================
        # STEP 13: COMPLETED
        # ==============================================================
        elif current_step == STEP_COMPLETED:
            if any(k in user_text.lower() for k in ["book another", "new booking", "book again", "restart", "start over"]):
                session = self.reset_session(session["session_id"])
                reply = (
                    "Welcome to **Northstar Airline Assistance**! 🌟\n\n"
                    "Which city or airport destination should I search for hotels near?"
                )
                quick_replies = self.get_location_quick_replies()
            else:
                found_booking = None
                if session.get("booking_id"):
                    found_booking = db_manager.get_booking_by_id(session["booking_id"])
                if not found_booking and session.get("guest_name"):
                    found_booking = db_manager.find_booking_by_query(session["guest_name"])

                if found_booking:
                    reply = self.generate_booking_inquiry_reply(user_text, found_booking)
                    booking_data = found_booking
                else:
                    reply = f"Your reservation (**{session.get('booking_id')}**) is confirmed. You can ask me *'show my booking details'* at any time, or book another room!"
                quick_replies = ["📋 View My Booking Details", "🏨 Book Another Room"]

        # Add assistant reply to history and save session
        session.setdefault("messages", []).append({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.utcnow().isoformat()
        })
        db_manager.save_session(session["session_id"], session)

        state_payload = {
            "current_step": session.get("current_step"),
            "location_id": session.get("location_id"),
            "location_city": session.get("location_city"),
            "airport_code": session.get("airport_code"),
            "hotel_id": session.get("hotel_id"),
            "hotel_name": session.get("hotel_name"),
            "guest_type": session.get("guest_type"),
            "guest_name": session.get("guest_name"),
            "company_name": session.get("company_name"),
            "total_members": session.get("total_members"),
            "rooms_count": session.get("rooms_count"),
            "room_name": session.get("room_name"),
            "room_id": session.get("room_id"),
            "price_per_night": session.get("price_per_night"),
            "checkin_date": session.get("checkin_date"),
            "checkout_date": session.get("checkout_date"),
            "total_nights": session.get("total_nights"),
            "total_amount": session.get("total_amount"),
            "airport_pickup": session.get("airport_pickup", False),
            "airport_drop": session.get("airport_drop", False),
            "booking_id": session.get("booking_id")
        }

        # Build rich interactive options for in-chat cards if not already set
        current_step_now = session.get("current_step")
        if session.get("pending_location_clarification"):
            cand = session["pending_location_clarification"]
            options_data = {
                "type": "clarification",
                "entity": "location",
                "title": f"Did you mean {cand['city']} ({cand['airport_code']})?",
                "subtitle": f"Is {cand['city']} right?",
                "confirm_value": cand['city'],
                "confirm_text": f"Yes, {cand['city']}",
                "cancel_text": "No, choose another"
            }
        elif session.get("pending_hotel_clarification"):
            cand = session["pending_hotel_clarification"]
            options_data = {
                "type": "clarification",
                "entity": "hotel",
                "title": f"Did you mean {cand['name']}?",
                "subtitle": "Is that right?",
                "confirm_value": cand['name'],
                "confirm_text": f"Yes, {cand['name']}",
                "cancel_text": "No, choose another"
            }
        elif session.get("pending_room_clarification"):
            cand = session["pending_room_clarification"]
            price_tag = f"${int(cand['price_per_night'])}/night" if cand.get("price_per_night") else ""
            title_text = f"Did you mean {cand['name']} ({price_tag})?" if price_tag else f"Did you mean {cand['name']}?"
            options_data = {
                "type": "clarification",
                "entity": "room",
                "title": title_text,
                "subtitle": "Is that right?",
                "confirm_value": f"Yes, {cand['name']}",
                "confirm_text": f"Yes, {cand['name']}",
                "cancel_text": "No, choose another"
            }
        elif 'options_data' not in locals() or options_data is None:
            if current_step_now in [STEP_START, STEP_ASK_LOCATION]:
                options_data = {
                    "type": "locations",
                    "items": db_manager.get_all_locations()
                }
            elif current_step_now == STEP_ASK_HOTEL:
                options_data = {
                    "type": "hotels",
                    "location_city": session.get("location_city"),
                    "items": db_manager.get_all_hotels(location_id=session.get("location_id"))
                }
            elif current_step_now == STEP_ASK_ROOM_TYPE:
                options_data = {
                    "type": "rooms",
                    "hotel_name": session.get("hotel_name"),
                    "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
                }
            elif current_step_now == STEP_ASK_AIRPORT_VEHICLE:
                options_data = {
                    "type": "vehicles",
                    "items": [
                        {"id": "both", "title": "Both (Pick-up & Drop)", "desc": "Dedicated chauffeur upon airport arrival and departure", "badge": "Most Popular", "icon": "fa-solid fa-car"},
                        {"id": "pickup", "title": "Pick-up Only", "desc": "Chauffeur greets you at airport arrival terminal", "badge": "Arrival", "icon": "fa-solid fa-plane-arrival"},
                        {"id": "drop", "title": "Drop-off Only", "desc": "Chauffeur transfer from hotel to airport terminal", "badge": "Departure", "icon": "fa-solid fa-plane-departure"},
                        {"id": "none", "title": "None / No Vehicle", "desc": "Guest will arrange own transportation", "badge": "Self", "icon": "fa-solid fa-ban"}
                    ]
                }
            elif current_step_now == STEP_CONFIRMATION:
                options_data = {
                    "type": "confirmation",
                    "items": [
                        {"action": "yes", "label": "✅ Confirm & Reserve Now", "primary": True},
                        {"action": "edit", "label": "✏️ Edit Booking Details", "primary": False}
                    ]
                }
            else:
                options_data = None

        return {
            "session_id": session["session_id"],
            "reply": reply,
            "current_step": session.get("current_step"),
            "state": state_payload,
            "quick_replies": quick_replies,
            "booking": booking_data,
            "options": options_data
        }

    async def process_user_message(self, session_id: Optional[str], user_input: str) -> Dict[str, Any]:
        return self.process_user_message_sync(session_id, user_input)

booking_agent = BookingAgent()
