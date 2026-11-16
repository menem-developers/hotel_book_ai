import re
import unicodedata
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("language_service")

def normalize_devanagari(text: str) -> str:
    """Normalize Devanagari text by removing nuktas (U+093C) and normalizing to NFC."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = text.replace('\u093c', '')
    return unicodedata.normalize('NFC', text)

# Supported Languages definition
SUPPORTED_LANGUAGES = {
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "flag": "🇬🇧",
        "voice": "en-US-AriaNeural",
        "whisper_lang": "en",
        "whisper_prompt": "Hotel booking reservation, rooms, guests, dates, check-in, check-out, Mumbai, Delhi, Bangalore, Goa, New York.",
        "browser_lang": "en-US",
        "greeting": (
            "Welcome to **Northstar Airline Assistance**! 🌟 I can help with a demo hotel booking, "
            "existing hotel booking support, or disruption-assistance questions.\n\n"
            "**Which city or airport destination should I search for hotels near?**"
        ),
        "placeholder": "Reply to the assistant (Type or click mic)...",
        "channel_tag": "Voice & Text",
        "disclaimer": "AI responses can be inaccurate. Confirm bookings and policy with an authorized agent."
    },
    "hi": {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "flag": "🇮🇳",
        "voice": "hi-IN-SwaraNeural",
        "whisper_lang": "hi",
        "whisper_prompt": "होटल बुकिंग आरक्षण, कमरे, अतिथि, तारीखें, चेक-इन, चेक-आउट, मुंबई, दिल्ली, बेंगलुरु, गोवा।",
        "browser_lang": "hi-IN",
        "greeting": (
            "**नॉर्थस्टार एयरलाइन सहायता** में आपका स्वागत है! 🌟 मैं होटल बुकिंग, "
            "मौजूदा आरक्षण पूछताछ और यात्रा सहायता में आपकी मदद कर सकता हूँ।\n\n"
            "**आप किस शहर या हवाई अड्डे के पास होटल खोजना चाहते हैं?**"
        ),
        "placeholder": "सहायक को उत्तर दें (टाइप करें या माइक दबाएं)...",
        "channel_tag": "वॉयस और टेक्स्ट",
        "disclaimer": "एआई प्रतिक्रियाएं सांकेतिक हो सकती हैं। कृपया अपनी बुकिंग की पुष्टि करें।"
    },
    "es": {
        "code": "es",
        "name": "Spanish",
        "native_name": "Español",
        "flag": "🇪🇸",
        "voice": "es-ES-ElviraNeural",
        "whisper_lang": "es",
        "whisper_prompt": "Reserva de hotel, habitaciones, huéspedes, fechas, check-in, check-out, Madrid, Barcelona, Mumbai, Delhi, Nueva York.",
        "browser_lang": "es-ES",
        "greeting": (
            "¡Bienvenido a la **Asistencia de Northstar Airlines**! 🌟 Puedo ayudarle con reservas de hotel, "
            "consultas de reservas existentes y asistencia en viaje.\n\n"
            "**¿Cerca de qué ciudad o aeropuerto desea buscar hoteles?**"
        ),
        "placeholder": "Responda al asistente (Escriba o use el micrófono)...",
        "channel_tag": "Voz y Texto",
        "disclaimer": "Las respuestas de IA pueden ser aproximadas. Confirme sus reservas con un agente autorizado."
    }
}

DEFAULT_LANGUAGE = "en"

def get_supported_languages() -> List[Dict[str, Any]]:
    """Return a list of available languages for frontend display."""
    return list(SUPPORTED_LANGUAGES.values())

def get_language_info(lang_code: Optional[str]) -> Dict[str, Any]:
    """Get metadata for a language code, falling back to English."""
    if not lang_code:
        return SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]
    code = lang_code.lower().strip()
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])

# ==============================================================
# MULTILINGUAL INPUT NORMALIZATION (HINDI & SPANISH -> AGENT INTENT)
# ==============================================================

# Hindi Number Words and Numerals (Devanagari & Phonetic)
HINDI_NUMBERS = {
    '१': 1, '२': 2, '३': 3, '४': 4, '५': 5, '६': 6, '७': 7, '८': 8, '९': 9, '१०': 10,
    'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पांच': 5, 'पाँच': 5,
    'छह': 6, 'छः': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
    'ek': 1, 'do': 2, 'teen': 3, 'tin': 3, 'char': 4, 'chaar': 4, 'panch': 5, 'paanch': 5,
    'chhe': 6, 'che': 6, 'saat': 7, 'sat': 7, 'aath': 8, 'ath': 8, 'nau': 9, 'das': 10
}

# Spanish Number Words
SPANISH_NUMBERS = {
    'un': 1, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
    'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10
}

# City Name Mappings
CITY_MAP = {
    # Hindi
    'मुंबई': 'Mumbai', 'मुम्बई': 'Mumbai', 'बंबई': 'Mumbai',
    'दिल्ली': 'Delhi', 'नई दिल्ली': 'Delhi', 'नई-दिल्ली': 'Delhi',
    'बेंगलुरु': 'Bangalore', 'बैंगलोर': 'Bangalore', 'बंगलौर': 'Bangalore',
    'गोवा': 'Goa',
    'न्यूयॉर्क': 'New York', 'न्यू यॉर्क': 'New York',
    'लॉस एंजिल्स': 'Los Angeles', 'लॉस एंजेलिस': 'Los Angeles',
    'सैन फ्रांसिस्को': 'San Francisco',
    'शिकागो': 'Chicago',
    'मियामी': 'Miami',
    'डलास': 'Dallas',
    'अटलांटा': 'Atlanta',
    'ह्यूस्टन': 'Houston',
    # Spanish
    'nueva york': 'New York',
    'los ángeles': 'Los Angeles', 'los angeles': 'Los Angeles',
    'san francisco': 'San Francisco',
    'madrid': 'Madrid',
    'barcelona': 'Barcelona'
}

# Hotel Name Mappings (Hindi, Spanish, Romanized -> English Hotel Entities)
HOTEL_MAP = {
    # New York (JFK)
    'द प्लाज़ा': 'The Plaza New York', 'प्लाज़ा': 'The Plaza New York', 'थे प्लाज़ा': 'The Plaza New York', 'दी प्लाज़ा': 'The Plaza New York',
    'द प्लाजा': 'The Plaza New York', 'प्लाजा': 'The Plaza New York', 'थे प्लाजा': 'The Plaza New York', 'दी प्लाजा': 'The Plaza New York',
    'the plaza': 'The Plaza New York', 'plaza': 'The Plaza New York', 'el plaza': 'The Plaza New York', 'la plaza': 'The Plaza New York',
    'टीडब्ल्यूए': 'TWA Hotel at JFK Airport', 'टी डब्ल्यू ए': 'TWA Hotel at JFK Airport', 'twa hotel': 'TWA Hotel at JFK Airport', 'twa': 'TWA Hotel at JFK Airport',
    'रिट्ज कार्लटन सेंट्रल पार्क': 'The Ritz-Carlton New York, Central Park', 'रिट्ज कार्लटन': 'The Ritz-Carlton', 'रिट्ज़ कार्लटन': 'The Ritz-Carlton',
    'रिट्ज-कार्लटन': 'The Ritz-Carlton', 'रिट्ज़-कार्लटन': 'The Ritz-Carlton', 'रिट्ज़': 'The Ritz-Carlton', 'ritz-carlton': 'The Ritz-Carlton', 'ritz carlton': 'The Ritz-Carlton', 'el ritz carlton': 'The Ritz-Carlton',
    '1 होटल ब्रुकलिन': '1 Hotel Brooklyn Bridge', 'ब्रुकलिन ब्रिज': '1 Hotel Brooklyn Bridge', 'होटल ब्रुकलिन ब्रिज': '1 Hotel Brooklyn Bridge',
    'सेंट रेजिस': 'The St. Regis New York', 'सेंट रेज़िस': 'The St. Regis New York', 'सेंट रेगिस': 'The St. Regis New York', 'सेंट-रेजिस': 'The St. Regis New York',
    'st regis': 'The St. Regis New York', 'st. regis': 'The St. Regis New York',
    'द कार्लाइल': 'The Carlyle, A Rosewood Hotel', 'कार्लाइल': 'The Carlyle, A Rosewood Hotel', 'carlyle': 'The Carlyle, A Rosewood Hotel',
    'द ग्रीनविच': 'The Greenwich Hotel', 'ग्रीनविच': 'The Greenwich Hotel', 'ग्रीनविच होटल': 'The Greenwich Hotel', 'greenwich': 'The Greenwich Hotel',
    'बक्कारा': 'Baccarat Hotel New York', 'बैकारेट': 'Baccarat Hotel New York', 'बकारात': 'Baccarat Hotel New York', 'baccarat': 'Baccarat Hotel New York',
    'लोट्टे': 'Lotte New York Palace', 'लोटे': 'Lotte New York Palace', 'न्यू यॉर्क पैलेस': 'Lotte New York Palace', 'न्यूयॉर्क पैलेस': 'Lotte New York Palace',
    'मंदारिन ओरिएंटल': 'Mandarin Oriental', 'मैंडरिन ओरिएंटल': 'Mandarin Oriental', 'मंदारिन': 'Mandarin Oriental', 'मैंडरिन': 'Mandarin Oriental',
    
    # Los Angeles (LAX)
    'हयात रीजेंसी एलएएक्स': 'Hyatt Regency Los Angeles International Airport', 'हयात एलएएक्स': 'Hyatt Regency Los Angeles International Airport',
    'बेवर्ली हिल्स होटल': 'The Beverly Hills Hotel', 'बेवर्ली हिल्स': 'The Beverly Hills Hotel', 'beverly hills': 'The Beverly Hills Hotel',
    'शटर्स ऑन द बीच': 'Shutters on the Beach', 'शटर्स': 'Shutters on the Beach',
    'वाल्डोर्फ एस्टोरिया': 'Waldorf Astoria Beverly Hills', 'वाल्डोर्फ': 'Waldorf Astoria',
    'होटल बेल-एयर': 'Hotel Bel-Air', 'होटल बेल एयर': 'Hotel Bel-Air', 'बेल-एयर': 'Hotel Bel-Air', 'बेल एयर': 'Hotel Bel-Air',
    
    # Chicago (ORD)
    'हिल्टन शिकागो': "Hilton Chicago O'Hare Airport", 'हिल्टन ओ-हेयर': "Hilton Chicago O'Hare Airport",
    'द पेनिंसुला': 'The Peninsula Chicago', 'पेनिंसुला': 'The Peninsula Chicago', 'पेनिनसुला': 'The Peninsula Chicago',
    'द लैंघम': 'The Langham, Chicago', 'लैंघम': 'The Langham, Chicago',
    'द ड्रेक': 'The Drake Hotel', 'ड्रेक होटल': 'The Drake Hotel', 'ड्रेक': 'The Drake Hotel',
    'फोर सीजन्स शिकागो': 'Four Seasons Hotel Chicago', 'फोर सीजन्स': 'Four Seasons', 'फोर सीजन': 'Four Seasons', 'चार मौसम': 'Four Seasons',
    
    # Miami (MIA)
    'मियामी एयरपोर्ट होटल': 'Miami International Airport Hotel',
    'द सेताई': 'The Setai, Miami Beach', 'सेताई': 'The Setai, Miami Beach',
    '1 होटल साउथ बीच': '1 Hotel South Beach',
    'सर्फ क्लब': 'Four Seasons Hotel at The Surf Club',
    
    # San Francisco (SFO)
    'ग्रैंड हयात एसएफओ': 'Grand Hyatt at SFO', 'ग्रैंड हयात': 'Grand Hyatt at SFO',
    'द फेयरमोंट': 'The Fairmont San Francisco', 'फेयरमोंट': 'The Fairmont San Francisco',
    'पैलेस होटल': 'Palace Hotel', 'पैलेस': 'Palace Hotel',
    
    # Other Key Brands & Resorts
    'हयात': 'Hyatt', 'हिल्टन': 'Hilton', 'मैरियट': 'Marriott', 'वेस्टिन': 'The Westin',
    'रेनेसां': 'Renaissance', 'रेनेसांस': 'Renaissance', 'इंटरकॉन्टिनेंटल': 'InterContinental',
    'रैडिसन': 'Radisson', 'रेडिसन': 'Radisson', 'थॉम्पसन': 'Thompson', 'एडजवाटर': 'The Edgewater',
    'बेलाजियो': 'Bellagio', 'विन': 'Wynn', 'वेनिसियन': 'The Venetian', 'रेड रॉक': 'Red Rock',
    'न्यूबरी': 'The Newbury', 'बोस्टन हार्बर': 'Boston Harbor', 'लिबर्टी': 'The Liberty',
    'द चार्ल्स': 'The Charles', 'हे-एडम्स': 'The Hay-Adams', 'विलार्ड': 'The Willard',
    'ब्राउन पैलेस': 'The Brown Palace', 'क्रॉफर्ड': 'The Crawford', 'सेंट जूलियन': 'St Julien',
    'पोस्ट ओक': 'The Post Oak', 'वुड्सलैंड्स': 'The Woodlands', 'ओमनी': 'Omni', 'ड्रोवर': 'Hotel Drover'
}

# Days of week & relative dates
DATE_MAP = {
    # Hindi
    'आज': 'today',
    'कल': 'tomorrow',
    'परसों': 'day after tomorrow',
    'सोमवार': 'Monday',
    'मंगलवार': 'Tuesday',
    'बुधवार': 'Wednesday',
    'गुरुवार': 'Thursday', 'बृहस्पतिवार': 'Thursday',
    'शुक्रवार': 'Friday',
    'शनिवार': 'Saturday',
    'रविवार': 'Sunday', 'इतवार': 'Sunday',
    'रात': 'night', 'रातें': 'nights', 'दिन': 'days',
    # Spanish
    'hoy': 'today',
    'mañana': 'tomorrow',
    'pasado mañana': 'day after tomorrow',
    'lunes': 'Monday',
    'martes': 'Tuesday',
    'miércoles': 'Wednesday', 'miercoles': 'Wednesday',
    'jueves': 'Thursday',
    'viernes': 'Friday',
    'sábado': 'Saturday', 'sabado': 'Saturday',
    'domingo': 'Sunday',
    'noche': 'night', 'noches': 'nights', 'días': 'days', 'dias': 'days'
}

def preprocess_user_input(text: str, lang: str = "en") -> str:
    """
    Preprocess and enrich user input by interpreting Hindi and Spanish expressions,
    city names, numbers, booking types, and confirmation phrases so the underlying
    booking agent can process the exact intent accurately.
    """
    if not text:
        return ""

    raw = text.strip()
    norm_raw = normalize_devanagari(raw)
    lower = norm_raw.lower()
    injections = []

    # 1. Hotel recognition (Hindi & Spanish hotel names / landmarks)
    matched_hotel = None
    for h_key, eng_hotel in HOTEL_MAP.items():
        h_key_norm = normalize_devanagari(h_key).lower()
        if h_key_norm in lower or h_key.lower() in raw.lower():
            injections.append(eng_hotel)
            matched_hotel = eng_hotel
            break

    # 1.5 City recognition
    for city_key, eng_city in CITY_MAP.items():
        city_key_norm = normalize_devanagari(city_key).lower()
        if city_key_norm in lower or city_key.lower() in raw.lower():
            if not matched_hotel or eng_city.lower() not in matched_hotel.lower():
                injections.append(eng_city)
            break

    # 2. Number normalization (Devanagari numerals or words)
    for h_digit, val in HINDI_NUMBERS.items():
        if re.search(r'(?:\b|\s|^)' + re.escape(h_digit) + r'(?:\b|\s|$|[^\w])', raw):
            injections.append(str(val))
            break

    for s_word, val in SPANISH_NUMBERS.items():
        if re.search(r'\b' + re.escape(s_word) + r'\b', lower):
            injections.append(str(val))
            break

    # 3. Guest / Booking Type
    # Hindi
    if any(k in lower for k in ['व्यक्तिगत', 'पर्सनल', 'खुद के लिए', 'अकेले']):
        injections.append("individual")
    elif any(k in lower for k in ['कंपनी', 'कॉर्पोरेट', 'कारपोरेट', 'व्यापार', 'संस्था']):
        injections.append("company")
    # Spanish
    if any(k in lower for k in ['individual', 'personal', 'solo para mi', 'privado']):
        injections.append("individual")
    elif any(k in lower for k in ['empresa', 'corporativo', 'compañia', 'compañía', 'negocios']):
        injections.append("company")

    # 4. Room Types & Hotel Room Names
    if any(k in lower for k in ['प्लाजा किंग', 'प्लाज़ा किंग', 'प्लाज़ा टिन', 'प्लाजा टिन', 'किंग रूम', 'king room', 'cama king']):
        injections.append("Plaza King Room")
    elif any(k in lower for k in ['एडवर्डियन', 'edwardian']):
        injections.append("Edwardian Park View Suite")
    elif any(k in lower for k in ['रॉयल प्लाजा', 'रॉयल', 'royal plaza']):
        injections.append("Royal Plaza Suite")
    elif any(k in lower for k in ['दो क्वीन', 'डबल क्वीन', 'क्वीन रूम', 'two queen', 'double queen', 'dos queen']):
        injections.append("Deluxe Two Queen Room")
    elif any(k in lower for k in ['डीलक्स', 'deluxe']):
        injections.append("Deluxe")
    elif any(k in lower for k in ['एग्जीक्यूटिव', 'executive', 'ejecutivo', 'ejecutiva']):
        injections.append("Executive")
    elif any(k in lower for k in ['सुइट', 'suite']):
        injections.append("Suite")
    elif any(k in lower for k in ['विला', 'villa']):
        injections.append("Villa")
    elif any(k in lower for k in ['प्रेसिडेंशियल', 'presidential', 'presidencial']):
        injections.append("Presidential")

    # 4.5 Room Ordinals
    if any(k in lower for k in ['पहला कमरा', 'पहला विकल्प', '1 नंबर कमरा', 'कमरा 1', 'पहला वाला', 'primer cuarto', 'primera habitación']):
        injections.append("Option 1")
    elif any(k in lower for k in ['दूसरा कमरा', 'दूसरा विकल्प', '2 नंबर कमरा', 'कमरा 2', 'दूसरा वाला', 'segundo cuarto', 'segunda habitación']):
        injections.append("Option 2")
    elif any(k in lower for k in ['तीसरा कमरा', 'तीसरा विकल्प', '3 नंबर कमरा', 'कमरा 3', 'तीसरा वाला', 'tercer cuarto', 'tercera habitación']):
        injections.append("Option 3")
    elif any(k in lower for k in ['चौथा कमरा', 'चौथा विकल्प', '4 नंबर कमरा', 'कमरा 4', 'चौथा वाला', 'cuarto cuarto', 'cuarta habitación']):
        injections.append("Option 4")

    # 5. Food / Dining Preference
    if any(k in lower for k in ['हाँ, खाना', 'खाना चाहिए', 'भोजन शामिल', 'नाश्ता चाहिए', 'खाना सहित', 'भोजन']):
        injections.append("Yes, include food")
    elif any(k in lower for k in ['नहीं, खाना', 'सिर्फ कमरा', 'कमरा ही चाहिए', 'खाना नहीं', 'बिना खाना']):
        injections.append("No food needed")
    elif any(k in lower for k in ['sí, con comida', 'incluir comida', 'con desayuno', 'si con comida', 'si comida']):
        injections.append("Yes, include food")
    elif any(k in lower for k in ['sin comida', 'solo habitación', 'solo habitacion', 'no comida', 'no necesito comida']):
        injections.append("No food needed")

    # 6. Airport Transportation
    if any(k in lower for k in ['दोनों', 'पिकअप और ड्रॉप', 'आना और जाना दोनों']):
        injections.append("Both pick-up and drop")
    elif any(k in lower for k in ['सिर्फ पिकअप', 'केवल पिकअप', 'हवाई अड्डे से']):
        injections.append("Pick-up only")
    elif any(k in lower for k in ['सिर्फ ड्रॉप', 'केवल ड्रॉप', 'हवाई अड्डे को']):
        injections.append("Drop-off only")
    elif any(k in lower for k in ['कोई वाहन नहीं', 'नहीं चाहिए', 'गाड़ी नहीं चाहिए', 'ट्रांसफर नहीं']):
        injections.append("No airport vehicle")
    elif any(k in lower for k in ['ambos', 'ida y vuelta', 'recogida y traslado']):
        injections.append("Both pick-up and drop")
    elif any(k in lower for k in ['solo recogida', 'solamente recogida']):
        injections.append("Pick-up only")
    elif any(k in lower for k in ['solo traslado', 'solo vuelta', 'solo drop']):
        injections.append("Drop-off only")
    elif any(k in lower for k in ['ninguno', 'sin transporte', 'sin traslado', 'no necesito transporte']):
        injections.append("No airport vehicle")

    # 7. Dates and Relative Days
    for k, v in DATE_MAP.items():
        is_ascii = all(ord(c) < 128 for c in k)
        if is_ascii:
            if re.search(r'\b' + re.escape(k) + r'\b', lower):
                injections.append(v)
        else:
            if k in lower:
                injections.append(v)

    # 8. Confirmation & Cancellation
    if any(k in lower for k in ['हाँ', 'पुष्टि करें', 'कन्फर्म', 'कन्फर्म करें', 'बुक करें', 'सही है', 'सब सही है', 'haan', 'ha ji', 'theek hai', 'tik hai', 'kardo']):
        injections.append("Yes, confirm booking")
    elif any(k in lower for k in ['बदलें', 'विवरण बदलें', 'एडिट', 'सुधारें', 'badlo', 'change']):
        injections.append("Edit details")
    elif any(k in lower for k in ['रद्द', 'रद्द करें', 'कैंसिल', 'कैंसल', 'radd', 'cancel']):
        injections.append("Cancel")
    elif any(k in lower for k in ['sí', 'si', 'confirmar', 'reservar', 'confirmar reserva', 'correcto']):
        injections.append("Yes, confirm booking")
    elif any(k in lower for k in ['modificar', 'editar', 'cambiar']):
        injections.append("Edit details")
    elif any(k in lower for k in ['cancelar', 'anular']):
        injections.append("Cancel")

    # 9. Global Restart
    if any(k in lower for k in ['शुरू से', 'रीसेट', 'दोबारा शुरू', 'नया बुकिंग', 'reiniciar', 'empezar de nuevo', 'nueva reserva']):
        injections.append("restart")

    # Combine enriched tokens if found to assist rule-matching
    if injections:
        combined = f"{raw} ({' '.join(injections)})"
        logger.debug(f"[preprocess_user_input] lang={lang}: '{raw}' -> '{combined}'")
        return combined

    return raw

# ==============================================================
# LOCALIZED DIALOGUES & RESPONSES
# ==============================================================

STEP_PROMPTS_LOCALIZED = {
    "hi": {
        "START": (
            "**नॉर्थस्टार एयरलाइन सहायता** में आपका स्वागत है! 🌟 मैं होटल बुकिंग, "
            "मौजूदा आरक्षण पूछताछ और उड़ान-सहायता में आपकी मदद कर सकता हूँ।\n\n"
            "**आप किस शहर या हवाई अड्डे के पास होटल खोजना चाहते हैं?**"
        ),
        "ASK_LOCATION": (
            "**आप किस शहर या हवाई अड्डे के पास होटल खोजना चाहते हैं?**"
        ),
        "ASK_HOTEL": (
            "हमारे पास **{location_label}** में उत्कृष्ट लक्ज़री संपत्तियां उपलब्ध हैं।\n\n"
            "**आप किस होटल में ठहरना पसंद करेंगे?**"
        ),
        "ASK_TYPE_AND_NAME": (
            "कृपया अपना **पूरा नाम** बताएं, और क्या आप एक **व्यक्तिगत अतिथि** के रूप में बुकिंग कर रहे हैं या किसी **कंपनी** की ओर से?"
        ),
        "ASK_COMPANY_NAME": (
            "आपकी **कंपनी या संस्था** का आधिकारिक नाम क्या है?"
        ),
        "ASK_MEMBERS_COUNT": (
            "धन्यवाद, **{guest_name}**! **कुल कितने अतिथि या सदस्य ठहरेंगे?**"
        ),
        "ASK_ROOMS_COUNT": (
            "आप अपने प्रवास के लिए **कितने कमरे** आरक्षित करना चाहते हैं?"
        ),
        "ASK_ROOM_TYPE": (
            "**{hotel_name}** में आप किस प्रकार का कमरा पसंद करेंगे?"
        ),
        "ASK_CHECKIN_DATE": (
            "**आप किस तारीख को चेक-इन करेंगे?** (आप 'आज', 'कल', 'आने वाला गुरुवार' या YYYY-MM-DD कह सकते हैं)"
        ),
        "ASK_CHECKOUT_DATE": (
            "चेक-इन **{checkin_date}** के लिए निर्धारित है।\n\n"
            "**आप कितने दिन या रातें ठहरेंगे (या चेक-आउट की तारीख क्या है)?**"
        ),
        "ASK_FOOD": (
            "**क्या आप अपने ठहरने के साथ भोजन/नाश्ता पैकेज शामिल करना चाहते हैं?**\n\n"
            "• 🍽️ **हाँ, भोजन शामिल** (दैनिक शेफ बुफे नाश्ता और भोजन)\n"
            "• ❌ **सिर्फ कमरा** (बिना भोजन पैकेज के)"
        ),
        "ASK_AIRPORT_VEHICLE": (
            "हवाई अड्डे से आगमन पर, **क्या आप हवाई अड्डा वाहन/ट्रांसफर सेवा बुक करना चाहते हैं?**\n\n"
            "हम निजी शॉफ़र ट्रांसफर सेवा प्रदान करते हैं:\n"
            "🚗 **हवाई अड्डा पिकअप** (एयरपोर्ट से होटल)\n"
            "🚕 **हवाई अड्डा ड्रॉप-ऑफ** (होटल से एयरपोर्ट)\n"
            "🚘 **दोनों (राउंड-ट्रिप)**\n"
            "❌ **कोई वाहन नहीं चाहिए**"
        ),
        "ASK_CONTACT": (
            "आरक्षण पुष्टि के लिए कृपया अपना **ईमेल पता या फोन नंबर** बताएं (या चेक-इन पर देने के लिए 'Skip' कहें):"
        ),
        "EDIT_MENU": (
            "**आप बुकिंग के किस विवरण में बदलाव करना चाहते हैं?**\n\n"
            "नीचे दिए गए विकल्पों में से चुनें या मुझे बताएं (जैसे *'होटल बदलें'*, *'तारीख बदलें'*, *'कमरा बदलें'*):"
        )
    },
    "es": {
        "START": (
            "¡Bienvenido a la **Asistencia de Northstar Airlines**! 🌟 Puedo ayudarle con reservas de hotel, "
            "consultas de reservas existentes y asistencia en viaje.\n\n"
            "**¿Cerca de qué ciudad o aeropuerto desea buscar hoteles?**"
        ),
        "ASK_LOCATION": (
            "**¿Cerca de qué ciudad o aeropuerto desea buscar hoteles?**"
        ),
        "ASK_HOTEL": (
            "Tenemos propiedades de lujo asociadas con **{location_label}**.\n\n"
            "**¿En qué hotel le gustaría hospedarse?**"
        ),
        "ASK_TYPE_AND_NAME": (
            "¿Podría indicarme su **nombre completo**, y si reserva como **huésped individual** o en nombre de una **empresa**?"
        ),
        "ASK_COMPANY_NAME": (
            "¿Cuál es el nombre oficial de su **empresa u organización**?"
        ),
        "ASK_MEMBERS_COUNT": (
            "¡Gracias, **{guest_name}**! **¿Cuántos huéspedes o miembros se hospedarán en total?**"
        ),
        "ASK_ROOMS_COUNT": (
            "**¿Cuántas habitaciones** desea reservar para su estancia?"
        ),
        "ASK_ROOM_TYPE": (
            "¿Qué tipo de habitación prefiere para su estancia en **{hotel_name}**?"
        ),
        "ASK_CHECKIN_DATE": (
            "**¿En qué fecha realizará el check-in?** (Puede decir 'hoy', 'mañana', 'próximo jueves' o AAAA-MM-DD)"
        ),
        "ASK_CHECKOUT_DATE": (
            "El check-in está programado para el **{checkin_date}**.\n\n"
            "**¿Cuántas noches se quedará (o cuál es su fecha de check-out)?**"
        ),
        "ASK_FOOD": (
            "**¿Desea incluir el servicio de comidas / desayuno con su estancia?**\n\n"
            "• 🍽️ **Sí, comida incluida** (Buffet de desayuno gourmet diario y comidas)\n"
            "• ❌ **Solo habitación** (Estancia sin paquete de comidas)"
        ),
        "ASK_AIRPORT_VEHICLE": (
            "Al llegar desde el aeropuerto, **¿desea reservar transporte o traslado privado?**\n\n"
            "Ofrecemos servicio de chófer privado:\n"
            "🚗 **Solo Recogida** (Del aeropuerto al hotel)\n"
            "🚕 **Solo Traslado** (Del hotel al aeropuerto)\n"
            "🚘 **Ambos (Ida y Vuelta)**\n"
            "❌ **Sin transporte**"
        ),
        "ASK_CONTACT": (
            "¿Podría facilitarme su **correo electrónico o teléfono** para la confirmación de la reserva? (O responda 'Skip' para proporcionarlo en el check-in):"
        ),
        "EDIT_MENU": (
            "**¿Qué detalle de la reserva le gustaría modificar?**\n\n"
            "Seleccione una opción o indíquemela (p. ej. *'cambiar hotel'*, *'cambiar fechas'*, *'cambiar habitación'*):"
        )
    }
}

QUICK_REPLIES_LOCALIZED = {
    "hi": {
        "👤 Individual Guest": "👤 व्यक्तिगत अतिथि",
        "🏢 Company / Corporate Booking": "🏢 कंपनी / कॉर्पोरेट बुकिंग",
        "1 Guest": "1 अतिथि",
        "2 Guests": "2 अतिथि",
        "4 Guests": "4 अतिथि",
        "6 Guests": "6 अतिथि",
        "1 Room": "1 कमरा",
        "2 Rooms": "2 कमरे",
        "3 Rooms": "3 कमरे",
        "4 Rooms": "4 कमरे",
        "Today": "आज",
        "Tomorrow": "कल",
        "Coming Thursday": "आने वाला गुरुवार",
        "Next Friday": "अगला शुक्रवार",
        "1 night": "1 रात",
        "2 nights": "2 रातें",
        "3 nights": "3 रातें",
        "5 nights": "5 रातें",
        "7 nights": "7 रातें",
        "🍽️ Yes, Include Food": "🍽️ हाँ, खाना शामिल करें",
        "❌ No Food Needed": "❌ सिर्फ कमरा चाहिए",
        "🚘 Both (Pick-up & Drop)": "🚘 दोनों (पिकअप और ड्रॉप)",
        "🚗 Pick-up Only": "🚗 केवल पिकअप",
        "🚕 Drop-off Only": "🚕 केवल ड्रॉप",
        "❌ None / No": "❌ कोई वाहन नहीं",
        "Skip (Provide at Check-in)": "छोड़ें (चेक-इन पर देंगे)",
        "✅ Yes, Confirm Booking": "✅ हाँ, बुकिंग कन्फर्म करें",
        "✏️ Edit Details": "✏️ विवरण बदलें",
        "❌ Cancel": "❌ रद्द करें",
        "📋 View My Booking Details": "📋 बुकिंग विवरण देखें",
        "🏨 Book Another Room": "🏨 दूसरा कमरा बुक करें"
    },
    "es": {
        "👤 Individual Guest": "👤 Huésped Individual",
        "🏢 Company / Corporate Booking": "🏢 Reserva de Empresa / Corporativa",
        "1 Guest": "1 Huésped",
        "2 Guests": "2 Huéspedes",
        "4 Guests": "4 Huéspedes",
        "6 Guests": "6 Huéspedes",
        "1 Room": "1 Habitación",
        "2 Rooms": "2 Habitaciones",
        "3 Rooms": "3 Habitaciones",
        "4 Rooms": "4 Habitaciones",
        "Today": "Hoy",
        "Tomorrow": "Mañana",
        "Coming Thursday": "Próximo Jueves",
        "Next Friday": "Próximo Viernes",
        "1 night": "1 noche",
        "2 nights": "2 noches",
        "3 nights": "3 noches",
        "5 nights": "5 noches",
        "7 nights": "7 noches",
        "🍽️ Yes, Include Food": "🍽️ Sí, Incluir Comida",
        "❌ No Food Needed": "❌ Solo Habitación",
        "🚘 Both (Pick-up & Drop)": "🚘 Ambos (Ida y Vuelta)",
        "🚗 Pick-up Only": "🚗 Solo Recogida",
        "🚕 Drop-off Only": "🚕 Solo Traslado",
        "❌ None / No": "❌ Sin Transporte",
        "Skip (Provide at Check-in)": "Omitir (Facilitar en check-in)",
        "✅ Yes, Confirm Booking": "✅ Sí, Confirmar Reserva",
        "✏️ Edit Details": "✏️ Modificar Datos",
        "❌ Cancel": "❌ Cancelar",
        "📋 View My Booking Details": "📋 Ver Datos de Reserva",
        "🏨 Book Another Room": "🏨 Reservar Otra Habitación"
    }
}

FAQ_LOCALIZED = {
    "hi": {
        "checkin_time": "हमारा मानक चेक-इन समय दोपहर **3:00 PM** है और चेक-आउट सुबह **11:00 AM** है। उपलब्धता के आधार पर जल्दी चेक-इन या देर से चेक-आउट की सुविधा मिल सकती है।",
        "amenities": "हमारे 5-स्टार सहयोगी होटलों में इन्फिनिटी स्विमिंग पूल, स्पा और सौना, 24/7 फिटनेस सेंटर, मिशेलिन रेस्तरां, रूफटॉप लाउंज, हाई-स्पीड वाई-फाई और हवाई अड्डा शॉफ़र ट्रांसफर शामिल हैं।",
        "breakfast": "मुफ्त स्वादिष्ट बुफे नाश्ता रोजाना सुबह **6:30 AM से 10:30 AM** तक हमारे मुख्य रेस्तरां में परोसा जाता है।",
        "cancellation": "हम आपकी निर्धारित चेक-इन तारीख से **24 घंटे पहले तक मुफ्त रद्दीकरण (Free Cancellation)** की सुविधा प्रदान करते हैं।",
        "wifi": "सभी कमरों, सुइट्स और सार्वजनिक क्षेत्रों में मुफ्त हाई-स्पीड वाई-फाई (500 Mbps तक) उपलब्ध है।",
        "parking": "होटल के सभी अतिथियों के लिए वैले पार्किंग और 24/7 सुरक्षित भूमिगत पार्किंग उपलब्ध है।"
    },
    "es": {
        "checkin_time": "Nuestro horario estándar de check-in es a las **3:00 PM** y el check-out a las **11:00 AM**. Disponibilidad de check-in anticipado o check-out tardío bajo petición.",
        "amenities": "Nuestros hoteles de 5 estrellas cuentan con piscina infinita, spa y sauna, gimnasio 24/7, restaurantes de alta cocina, lounge en azotea, Wi-Fi de alta velocidad y transporte privado.",
        "breakfast": "El desayuno buffet gourmet de cortesía se sirve todos los días de **6:30 AM a 10:30 AM** en nuestro restaurante principal.",
        "cancellation": "Ofrecemos **cancelación gratuita hasta 24 horas antes** de su fecha de check-in programada.",
        "wifi": "Wi-Fi de alta velocidad gratuito (hasta 500 Mbps) disponible en todas las habitaciones y áreas comunes.",
        "parking": "Servicio de aparcacoches y estacionamiento subterráneo seguro las 24 horas para todos los huéspedes."
    }
}

def _clean_guest_display(session: Dict[str, Any], default_name: str = "Valued Guest") -> str:
    raw_name = session.get("guest_name")
    if raw_name:
        raw_name = re.sub(r'\(.*?\)', '', raw_name).strip()
        disallowed = {"not", "suggesting", "able", "do", "this", "that", "trying", "looking", "just", "wondering", "going"}
        if any(w.lower() in disallowed for w in raw_name.split()) or len(raw_name) < 2 or len(raw_name.split()) > 4:
            raw_name = None

    company = session.get("company_name")
    if company:
        company = re.sub(r'\(.*?\)', '', company).strip()

    if raw_name and company:
        return f"{raw_name} ({company})"
    elif raw_name:
        return raw_name
    elif company:
        return company
    return default_name

def format_confirmation_summary_localized(session: Dict[str, Any], lang: str) -> str:
    """Format the localized booking confirmation review card."""
    guest_display = _clean_guest_display(session, default_name="अतिथि" if lang == "hi" else ("Huésped" if lang == "es" else "Valued Guest"))

    contact_display = session.get("contact_email") or session.get("contact_phone") or "Provided at check-in"
    city = session.get('location_city', 'Destination')
    code = session.get('airport_code', '')
    hotel = session.get('hotel_name', 'Luxury Hotel')
    room = session.get('room_name', 'Room')
    rooms_count = session.get('rooms_count', 1)
    members = session.get('total_members', 1)
    cin = session.get('checkin_date', '')
    cout = session.get('checkout_date', '')
    nights = session.get('total_nights', 1)
    price = session.get('price_per_night', 0)
    total = session.get('total_amount', 0)

    if lang == "hi":
        type_str = "कंपनी / कॉर्पोरेट" if session.get("guest_type") == "company" else "व्यक्तिगत अतिथि"
        food_str = "🍽️ हाँ, भोजन शामिल" if session.get("food_included") else "❌ सिर्फ कमरा"
        pickup_str = "✅ हाँ (आगमन शॉफ़र)" if session.get("airport_pickup") else "❌ नहीं"
        drop_str = "✅ हाँ (प्रस्थान शॉफ़र)" if session.get("airport_drop") else "❌ नहीं"
        contact_str = contact_display if contact_display != "Provided at check-in" else "चेक-इन पर दिया जाएगा"

        return (
            f"📋 **बुकिंग सारांश और समीक्षा**:\n\n"
            f"• **गंतव्य / हवाई अड्डा**: {city} ({code})\n"
            f"• **होटल**: {hotel}\n"
            f"• **अतिथि / संस्था**: {guest_display}\n"
            f"• **बुकिंग प्रकार**: {type_str}\n"
            f"• **कुल अतिथि**: {members}\n"
            f"• **आरक्षित कमरे**: {rooms_count} x {room}\n"
            f"• **तारीखें**: {cin} से {cout} ({nights} रातें)\n"
            f"• **भोजन / खानपान**: {food_str}\n"
            f"• **हवाई अड्डा पिकअप**: {pickup_str}\n"
            f"• **हवाई अड्डा ड्रॉप**: {drop_str}\n"
            f"• **दर**: ${price}/रात प्रति कमरा\n"
            f"• **कुल अनुमानित मूल्य**: **${total}**\n"
            f"• **संपर्क**: {contact_str}\n\n"
            f"क्या आप चाहते हैं कि मैं इस बुकिंग की अभी पुष्टि करूँ?"
        )

    elif lang == "es":
        type_str = "Corporativo / Empresa" if session.get("guest_type") == "company" else "Huésped Individual"
        food_str = "🍽️ Sí, comida incluida" if session.get("food_included") else "❌ Solo habitación"
        pickup_str = "✅ Sí (Chófer de llegada)" if session.get("airport_pickup") else "❌ No"
        drop_str = "✅ Sí (Chófer de salida)" if session.get("airport_drop") else "❌ No"
        contact_str = contact_display if contact_display != "Provided at check-in" else "Se proporcionará al check-in"

        return (
            f"📋 **Resumen y Revisión de Reserva**:\n\n"
            f"• **Destino / Aeropuerto**: {city} ({code})\n"
            f"• **Hotel**: {hotel}\n"
            f"• **Huésped / Organización**: {guest_display}\n"
            f"• **Tipo de Reserva**: {type_str}\n"
            f"• **Total de Huéspedes**: {members}\n"
            f"• **Habitaciones Reservadas**: {rooms_count} x {room}\n"
            f"• **Fechas**: {cin} al {cout} ({nights} noches)\n"
            f"• **Comida / Restaurante**: {food_str}\n"
            f"• **Recogida en Aeropuerto**: {pickup_str}\n"
            f"• **Traslado al Aeropuerto**: {drop_str}\n"
            f"• **Tarifa**: ${price}/noche por habitación\n"
            f"• **Precio Total Estimado**: **${total}**\n"
            f"• **Contacto**: {contact_str}\n\n"
            f"¿Desea que confirme y reserve este hotel ahora?"
        )

    # Fallback to English
    return ""

def format_completed_booking_localized(session: Dict[str, Any], lang: str) -> str:
    """Format the localized completed booking confirmation voucher message."""
    b_id = session.get("booking_id", "")
    rooms = session.get("rooms_count", 1)
    room = session.get("room_name", "")
    hotel = session.get("hotel_name", "Luxury Hotel")
    cin = session.get("checkin_date", "")
    cout = session.get("checkout_date", "")
    nights = session.get("total_nights", 1)

    if lang == "hi":
        vehicle_text = "पिकअप और ड्रॉप दोनों की पुष्टि हो गई" if session.get("airport_pickup") and session.get("airport_drop") else ("पिकअप वाहन कन्फर्म" if session.get("airport_pickup") else ("ड्रॉप वाहन कन्फर्म" if session.get("airport_drop") else "कोई वाहन नहीं"))
        return (
            f"🎉 **आरक्षण की पुष्टि हो गई!**\n\n"
            f"आपका बुकिंग संदर्भ कोड **{b_id}** है।\n\n"
            f"हमने **{hotel}** में **{rooms} x {room}** आरक्षित कर दिया है, **{cin}** से **{cout}** ({nights} रातें)।\n\n"
            f"हवाई अड्डा वाहन सेवा: {vehicle_text}।\n\n"
            f"हम {hotel} में आपके सुखद और आरामदायक प्रवास की कामना करते हैं!"
        )
    elif lang == "es":
        vehicle_text = "Recogida y traslado confirmados" if session.get("airport_pickup") and session.get("airport_drop") else ("Recogida confirmada" if session.get("airport_pickup") else ("Traslado confirmado" if session.get("airport_drop") else "Sin transporte"))
        return (
            f"🎉 **¡Reserva Confirmada con Éxito!**\n\n"
            f"Su código de referencia de reserva es **{b_id}**.\n\n"
            f"Hemos reservado {rooms} x {room} en **{hotel}** del **{cin}** al **{cout}** ({nights} noches).\n\n"
            f"Transporte de Aeropuerto: {vehicle_text}.\n\n"
            f"¡Esperamos brindarle una estancia excepcional en {hotel}!"
        )

    return ""

def localize_response(result: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    """
    Transform and translate the assistant's reply, quick replies, and options
    into the selected target language (English, Hindi, or Spanish).
    """
    if not lang or lang == "en":
        return result

    target_lang = lang.lower().strip()
    if target_lang not in ("hi", "es"):
        return result

    current_step = result.get("current_step", "")
    state = result.get("state", {})
    original_reply = result.get("reply", "")

    localized_reply = None

    # 0. If original reply already contains Devanagari script (Hindi), preserve it!
    if target_lang == "hi" and any(0x0900 <= ord(c) <= 0x097F for c in original_reply):
        localized_reply = original_reply

    # 0.1 If original reply is dynamic inquiry answer (weather, search, joke, recommendation, details), preserve it!
    elif any(sym in original_reply for sym in ["🌤️", "💡", "📚", "🔍", "Current Weather", "travel chuckle", "chuckle", "Why don't hotels ever get lonely"]):
        localized_reply = original_reply

    # 0.2 If original reply contains multi-entity acknowledgment, localize acknowledgment gracefully
    elif "Understood! I've noted" in original_reply:
        if target_lang == "hi":
            hi_ack = original_reply
            hi_ack = hi_ack.replace("Understood! I've noted", "समझ गया! मैंने नोट कर लिया है:")
            hi_ack = hi_ack.replace("Destination:", "गंतव्य:")
            hi_ack = hi_ack.replace("Duration:", "ठहरने की अवधि:")
            hi_ack = hi_ack.replace("nights", "रातें")
            hi_ack = hi_ack.replace("Vehicle:", "वाहन:")
            hi_ack = hi_ack.replace("Pick-up & Drop", "पिकअप और ड्रॉप")
            hi_ack = hi_ack.replace("Pick-up", "पिकअप")
            hi_ack = hi_ack.replace("Drop-off", "ड्रॉप")
            hi_ack = hi_ack.replace("Hotel:", "होटल:")
            hi_ack = hi_ack.replace("Room:", "कमरा:")
            hi_ack = hi_ack.replace("Food:", "भोजन:")
            hi_ack = hi_ack.replace("Included", "शामिल")
            hi_ack = hi_ack.replace("Room Only", "सिर्फ कमरा")
            hi_ack = hi_ack.replace("We have luxury properties connected to", "हमारे पास यहाँ उत्कृष्ट लक्ज़री संपत्तियां उपलब्ध हैं:")
            hi_ack = hi_ack.replace("Which hotel would you prefer to stay at?", "आप किस होटल में ठहरना पसंद करेंगे?")
            localized_reply = hi_ack
        elif target_lang == "es":
            es_ack = original_reply
            es_ack = es_ack.replace("Understood! I've noted", "¡Entendido! He registrado:")
            es_ack = es_ack.replace("Destination:", "Destino:")
            es_ack = es_ack.replace("Duration:", "Duración:")
            es_ack = es_ack.replace("nights", "noches")
            es_ack = es_ack.replace("Vehicle:", "Vehículo:")
            es_ack = es_ack.replace("Pick-up & Drop", "Recogida y traslado")
            es_ack = es_ack.replace("Pick-up", "Recogida")
            es_ack = es_ack.replace("Drop-off", "Traslado")
            es_ack = es_ack.replace("Hotel:", "Hotel:")
            es_ack = es_ack.replace("Room:", "Habitación:")
            es_ack = es_ack.replace("Food:", "Comida:")
            es_ack = es_ack.replace("Included", "Incluida")
            es_ack = es_ack.replace("Room Only", "Solo habitación")
            es_ack = es_ack.replace("Which hotel would you prefer to stay at?", "¿En qué hotel te gustaría alojarte?")
            localized_reply = es_ack

    # 1. Check for Completed Booking
    elif current_step == "COMPLETED" or "Reservation Confirmed!" in original_reply or "Booking Reference" in original_reply:
        localized_reply = format_completed_booking_localized(state, target_lang)

    # 2. Check for Confirmation Review Card
    elif current_step == "CONFIRMATION" or "Booking Summary & Review" in original_reply:
        localized_reply = format_confirmation_summary_localized(state, target_lang)

    # 3. Check for Standard Step Prompts
    elif current_step in STEP_PROMPTS_LOCALIZED.get(target_lang, {}):
        template = STEP_PROMPTS_LOCALIZED[target_lang][current_step]
        city_name = state.get('location_city', 'your destination')
        code = state.get('airport_code', '')
        loc_label = f"{city_name} ({code})" if code else city_name
        raw_name = state.get("guest_name")
        if raw_name:
            raw_name = re.sub(r'\(.*?\)', '', raw_name).strip()
            disallowed = {"not", "suggesting", "able", "do", "this", "that", "trying", "looking", "just", "wondering", "going"}
            if any(w.lower() in disallowed for w in raw_name.split()) or len(raw_name) < 2 or len(raw_name.split()) > 4:
                raw_name = None

        guest_name = raw_name or state.get("company_name") or ("अतिथि" if target_lang == "hi" else "huésped")

        localized_reply = template.format(
            location_label=loc_label,
            hotel_name=state.get("hotel_name", "Luxury Hotel"),
            guest_name=guest_name,
            checkin_date=state.get("checkin_date", ""),
            checkout_date=state.get("checkout_date", ""),
            rooms_count=state.get("rooms_count", 1)
        )

    # 4. Check for FAQs
    if not localized_reply:
        for faq_k, faq_text in FAQ_LOCALIZED.get(target_lang, {}).items():
            if faq_k in original_reply.lower() or (faq_k == "checkin_time" and "3:00 pm" in original_reply.lower()) or (faq_k == "breakfast" and "6:30 am" in original_reply.lower()):
                localized_reply = faq_text
                break

    # 5. Fallback phrase replacements for dynamic greetings or messages
    if not localized_reply and original_reply:
        localized_reply = original_reply
        if target_lang == "hi":
            replacements = [
                ("Welcome to Northstar Airline Assistance", "नॉर्थस्टार एयरलाइन सहायता में आपका स्वागत है"),
                ("Which city or airport destination should I search for hotels near?", "आप किस शहर या हवाई अड्डे के पास होटल खोजना चाहते हैं?"),
                ("Which hotel would you prefer to stay at?", "आप किस होटल में ठहरना पसंद करेंगे?"),
                ("How many rooms would you like to reserve for your stay?", "आप कितने कमरे आरक्षित करना चाहते हैं?"),
                ("How many guests or members will be staying in total?", "कुल कितने अतिथि ठहरेंगे?"),
                ("What date will you be checking in?", "आप किस तारीख को चेक-इन करेंगे?"),
                ("No available rooms found", "कोई उपलब्ध कमरा नहीं मिला"),
                ("Please try again", "कृपया पुनः प्रयास करें")
            ]
            for eng, hi in replacements:
                localized_reply = localized_reply.replace(eng, hi)

        elif target_lang == "es":
            replacements = [
                ("Welcome to Northstar Airline Assistance", "Bienvenido a la Asistencia de Northstar Airlines"),
                ("Which city or airport destination should I search for hotels near?", "¿Cerca de qué ciudad o aeropuerto desea buscar hoteles?"),
                ("Which hotel would you prefer to stay at?", "¿En qué hotel le gustaría hospedarse?"),
                ("How many rooms would you like to reserve for your stay?", "¿Cuántas habitaciones desea reservar?"),
                ("How many guests or members will be staying in total?", "¿Cuántos huéspedes se hospedarán en total?"),
                ("What date will you be checking in?", "¿En qué fecha realizará el check-in?"),
                ("No available rooms found", "No se encontraron habitaciones disponibles"),
                ("Please try again", "Por favor, inténtelo de nuevo")
            ]
            for eng, es in replacements:
                localized_reply = localized_reply.replace(eng, es)

    if localized_reply:
        result["reply"] = localized_reply

    # 6. Localize Quick Replies Chips
    qr_map = QUICK_REPLIES_LOCALIZED.get(target_lang, {})
    if result.get("quick_replies"):
        new_qrs = []
        for qr in result["quick_replies"]:
            # If in map, translate; otherwise keep as is (e.g. hotel names or location names)
            new_qrs.append(qr_map.get(qr, qr))
        result["quick_replies"] = new_qrs

    result["language"] = target_lang
    return result
