import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

INDIAN_LOCATIONS = [
    # 1. Chennai (Tamil Nadu)
    {
        "location_id": "LOC-MAA",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "airport_name": "Chennai International Airport (MAA)",
        "airport_code": "MAA",
        "aliases": ["chennai", "madras", "maa", "tamil nadu", "tamilnadu"],
        "description": "Premier gateway to Tamil Nadu, celebrated for Marina Beach, Kapaleeshwarar Temple, and major IT corridors."
    },
    # 2. Coimbatore (Tamil Nadu)
    {
        "location_id": "LOC-CJB",
        "city": "Coimbatore",
        "state": "Tamil Nadu",
        "country": "India",
        "airport_name": "Coimbatore International Airport (CJB)",
        "airport_code": "CJB",
        "aliases": ["coimbatore", "kovai", "cjb", "tamil nadu"],
        "description": "The Manchester of South India, textile & industrial hub nestled near the scenic Western Ghats."
    },
    # 3. Trichy / Tiruchirappalli (Tamil Nadu)
    {
        "location_id": "LOC-TRZ",
        "city": "Trichy",
        "state": "Tamil Nadu",
        "country": "India",
        "airport_name": "Tiruchirappalli International Airport (TRZ)",
        "airport_code": "TRZ",
        "aliases": ["trichy", "tiruchirappalli", "tiruchi", "trz", "tamil nadu"],
        "description": "Historic temple city on River Cauvery, home to the Rockfort Temple and Srirangam Ranganathaswamy Temple."
    },
    # 4. Madurai (Tamil Nadu)
    {
        "location_id": "LOC-IXM",
        "city": "Madurai",
        "state": "Tamil Nadu",
        "country": "India",
        "airport_name": "Madurai International Airport (IXM)",
        "airport_code": "IXM",
        "aliases": ["madurai", "ixm", "tamil nadu"],
        "description": "Cultural capital of Tamil Nadu, world-renowned for the magnificent Meenakshi Amman Temple."
    },
    # 5. Bengaluru (Karnataka)
    {
        "location_id": "LOC-BLR",
        "city": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "airport_name": "Kempegowda International Airport (BLR)",
        "airport_code": "BLR",
        "aliases": ["bengaluru", "bangalore", "blr", "karnataka"],
        "description": "India's Silicon Valley and Garden City, tech capital with vibrant nightlife and pleasant weather."
    },
    # 6. Mangaluru (Karnataka)
    {
        "location_id": "LOC-IXE",
        "city": "Mangaluru",
        "state": "Karnataka",
        "country": "India",
        "airport_name": "Mangaluru International Airport (IXE)",
        "airport_code": "IXE",
        "aliases": ["mangaluru", "mangalore", "ixe", "karnataka"],
        "description": "Coastal port city of Karnataka, famed for pristine beaches, seafood delicacies, and ancient temples."
    },
    # 7. Kochi (Kerala)
    {
        "location_id": "LOC-COK",
        "city": "Kochi",
        "state": "Kerala",
        "country": "India",
        "airport_name": "Cochin International Airport (COK)",
        "airport_code": "COK",
        "aliases": ["kochi", "cochin", "cok", "kerala"],
        "description": "Queen of the Arabian Sea, world's first solar-powered airport, backwaters, and colonial Fort Kochi."
    },
    # 8. Thiruvananthapuram (Kerala)
    {
        "location_id": "LOC-TRV",
        "city": "Thiruvananthapuram",
        "state": "Kerala",
        "country": "India",
        "airport_name": "Thiruvananthapuram International Airport (TRV)",
        "airport_code": "TRV",
        "aliases": ["thiruvananthapuram", "trivandrum", "trv", "kerala"],
        "description": "Kerala's capital, home to the Padmanabhaswamy Temple, Kovalam crescent beaches, and coastal backwaters."
    },
    # 9. Kozhikode (Kerala)
    {
        "location_id": "LOC-CCJ",
        "city": "Kozhikode",
        "state": "Kerala",
        "country": "India",
        "airport_name": "Calicut International Airport (CCJ)",
        "airport_code": "CCJ",
        "aliases": ["kozhikode", "calicut", "ccj", "kerala"],
        "description": "Historical Malabar port city, legendary for culinary delicacies, spice markets, and coastal charm."
    },
    # 10. Mumbai (Maharashtra)
    {
        "location_id": "LOC-BOM",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "airport_name": "Chhatrapati Shivaji Maharaj International Airport (BOM)",
        "airport_code": "BOM",
        "aliases": ["mumbai", "bombay", "bom", "maharashtra"],
        "description": "Financial capital of India, city of dreams, Bollywood, Marine Drive, and vibrant 24/7 energy."
    },
    # 11. Delhi (Delhi NCR)
    {
        "location_id": "LOC-DEL",
        "city": "Delhi",
        "state": "Delhi NCR",
        "country": "India",
        "airport_name": "Indira Gandhi International Airport (DEL)",
        "airport_code": "DEL",
        "aliases": ["delhi", "new delhi", "del", "ncr", "gurugram", "noida"],
        "description": "India's historic capital, blending UNESCO world heritage monuments, embassies, and luxury Aerocity."
    },
    # 12. Hyderabad (Telangana)
    {
        "location_id": "LOC-HYD",
        "city": "Hyderabad",
        "state": "Telangana",
        "country": "India",
        "airport_name": "Rajiv Gandhi International Airport (HYD)",
        "airport_code": "HYD",
        "aliases": ["hyderabad", "hyd", "secunderabad", "telangana"],
        "description": "City of Pearls and Biryani, major IT hub featuring HITEC City, Charminar, and Nizam palaces."
    },
    # 13. Goa (Goa)
    {
        "location_id": "LOC-GOX",
        "city": "Goa",
        "state": "Goa",
        "country": "India",
        "airport_name": "Manohar International Airport Mopa (GOX) / Dabolim (GOI)",
        "airport_code": "GOX",
        "aliases": ["goa", "gox", "goi", "panaji", "panjim", "mopa", "dabolim"],
        "description": "India's premier beach resort destination, famous for sun-kissed sands, Portuguese villas, and nightlife."
    },
    # 14. Kolkata (West Bengal)
    {
        "location_id": "LOC-CCU",
        "city": "Kolkata",
        "state": "West Bengal",
        "country": "India",
        "airport_name": "Netaji Subhash Chandra Bose International Airport (CCU)",
        "airport_code": "CCU",
        "aliases": ["kolkata", "calcutta", "ccu", "west bengal"],
        "description": "City of Joy and cultural capital, steeped in colonial heritage, Howrah Bridge, art, and grand hospitality."
    }
]

INDIAN_HOTELS = [
    # 1. Chennai (MAA) - 5 Hotels
    {
        "hotel_id": "HTL-MAA-AIRPORT",
        "location_id": "LOC-MAA",
        "name": "Grand Azure Airport Palace & Spa",
        "address": "GST Road, Meenambakkam, Chennai (1.5 km to MAA Airport)",
        "description": "5-star luxury airport retreat with 24/7 runway shuttle, full-service spa, and rooftop pool.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-MAA-MARINA",
        "location_id": "LOC-MAA",
        "name": "Grand Azure Marina Bay Luxury Hotel",
        "address": "Santhome High Road, Marina Promenade, Chennai",
        "description": "Oceanfront luxury overlooking the Bay of Bengal with coastal seafood dining and beach sunrise views.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-MAA-OMR",
        "location_id": "LOC-MAA",
        "name": "Grand Azure IT Expressway Tech Tower",
        "address": "Old Mahabalipuram Road (OMR), Sholinganallur, Chennai",
        "description": "High-tech corporate hotel featuring executive meeting lounges, fiber net, and direct IT corridor access.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-MAA-GUINDY",
        "location_id": "LOC-MAA",
        "name": "Grand Azure Guindy Royal Regency",
        "address": "Mount Road, Adjacent to Guindy National Park, Chennai",
        "description": "Prestigious business regency with tranquil forest garden views, grand ballroom, and fine dining.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-MAA-TEMPLE",
        "location_id": "LOC-MAA",
        "name": "Grand Azure Mahabalipuram Ocean Resort",
        "address": "East Coast Road (ECR), Beachfront, Kovalam/Mahabalipuram",
        "description": "Idyllic beach resort with private sandy shoreline, Ayurvedic rejuvenation spa, and private ocean villas.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },

    # 2. Coimbatore (CJB) - 5 Hotels
    {
        "hotel_id": "HTL-CJB-AIRPORT",
        "location_id": "LOC-CJB",
        "name": "Grand Azure Avinashi Airport Suites",
        "address": "Avinashi Road, Civil Aerodrome Post, Coimbatore (1 km to CJB)",
        "description": "Contemporary airport suites with express check-in, complimentary airport transfers, and rooftop lounge.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CJB-RACECOURSE",
        "location_id": "LOC-CJB",
        "name": "Grand Azure Race Course Luxury Hotel",
        "address": "Race Course Road, Central Promenade, Coimbatore",
        "description": "Elite luxury property in the greenest quarter of Coimbatore, known for royal service and fine dining.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CJB-BROOKFIELDS",
        "location_id": "LOC-CJB",
        "name": "Grand Azure Brookefields Residency",
        "address": "Dr. Krishnasamy Mudaliar Road, Central Coimbatore",
        "description": "Vibrant city hotel located steps from prime shopping, textile markets, and entertainment complexes.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CJB-PEELAMEDU",
        "location_id": "LOC-CJB",
        "name": "Grand Azure Peelamedu Executive Hotel",
        "address": "Avinashi Road, Peelamedu Industrial Zone, Coimbatore",
        "description": "Modern business suites engineered for entrepreneurs, corporate delegations, and international visitors.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CJB-HILLS",
        "location_id": "LOC-CJB",
        "name": "Grand Azure Siruvani Foothills Retreat",
        "address": "Siruvani Main Road, Western Ghats Valley, Coimbatore",
        "description": "Scenic eco-wellness retreat surrounded by coconut plantations and misty Nilgiri hill vistas.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },

    # 3. Trichy / Tiruchirappalli (TRZ) - 5 Hotels
    {
        "hotel_id": "HTL-TRZ-AIRPORT",
        "location_id": "LOC-TRZ",
        "name": "Grand Azure International Airport Grand",
        "address": "Pudukkottai Main Road, Airport Zone, Trichy (800m to TRZ)",
        "description": "Premier airport hotel offering comfortable soundproof suites, express shuttles, and 24-hr multi-cuisine restaurant.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRZ-ROCKFORT",
        "location_id": "LOC-TRZ",
        "name": "Grand Azure Rockfort Heritage Palace",
        "address": "Chinthamani, Direct View of Rockfort Temple, Trichy",
        "description": "Heritage palace hotel featuring spectacular rooftop vistas of the floodlit ancient Rockfort fortress.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRZ-SRIRANGAM",
        "location_id": "LOC-TRZ",
        "name": "Grand Azure Srirangam Divine Suites",
        "address": "North Chitra Street, Near Srirangam Rajagopuram, Trichy",
        "description": "Serene spiritual sanctuary with traditional Tamil architecture and direct access to Sri Ranganathaswamy Temple.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRZ-CANTONMENT",
        "location_id": "LOC-TRZ",
        "name": "Grand Azure Cantonment Business Hotel",
        "address": "Collector Office Road, Cantonment Central, Trichy",
        "description": "Leading central business hotel near Trichy Railway Junction and commercial business complexes.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRZ-CAUVERY",
        "location_id": "LOC-TRZ",
        "name": "Grand Azure Cauvery Riverfront Resort",
        "address": "Mambalasalai, Banks of River Cauvery, Trichy",
        "description": "Tranquil riverfront resort featuring lush riverside gardens, infinity pool, and authentic South Indian dining.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },

    # 4. Madurai (IXM) - 5 Hotels
    {
        "hotel_id": "HTL-IXM-AIRPORT",
        "location_id": "LOC-IXM",
        "name": "Grand Azure Madurai Airport Chola Suites",
        "address": "Airport Ring Road, Perungudi, Madurai (1.2 km to IXM)",
        "description": "Comfortable luxury suites conveniently located right outside Madurai Airport terminal.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXM-MEENAKSHI",
        "location_id": "LOC-IXM",
        "name": "Grand Azure Meenakshi Royal Palace",
        "address": "West Veli Street, Heritage Quarter, Madurai",
        "description": "Opulent palace hotel adjacent to Meenakshi Amman Temple with traditional temple architecture and rooftop dining.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXM-BYPASS",
        "location_id": "LOC-IXM",
        "name": "Grand Azure Bye-Pass Business Regency",
        "address": "Vanniar Bye-Pass Road, Madurai City",
        "description": "Modern executive business hotel with high-speed connectivity, conference halls, and multi-cuisine restaurant.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXM-PASUMALAI",
        "location_id": "LOC-IXM",
        "name": "Grand Azure Pasumalai Hillside Resort",
        "address": "TPK Road, Pasumalai Hill, Madurai",
        "description": "Stunning hillside resort set amidst acres of landscaped greenery, historic banyan trees, and peacock gardens.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXM-TEPPAM",
        "location_id": "LOC-IXM",
        "name": "Grand Azure Vandiyur Lakefront Hotel",
        "address": "East Coast Road, Near Teppakulam Lake, Madurai",
        "description": "Relaxing water-view property near the historic Mariamman Teppakulam tank with tranquil evening breezes.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },

    # 5. Bengaluru (BLR) - 5 Hotels
    {
        "hotel_id": "HTL-BLR-AEROCITY",
        "location_id": "LOC-BLR",
        "name": "Grand Azure Kempegowda Aerocity Hotel",
        "address": "Devanahalli Airport Expressway, Bengaluru (2 km to BLR)",
        "description": "Ultra-modern luxury hotel connected directly to BLR with VIP runway lounges and fast airport transfer.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BLR-WHITEFIELD",
        "location_id": "LOC-BLR",
        "name": "Grand Azure Whitefield Tech Haven",
        "address": "ITPB Main Road, Whitefield Tech Zone, Bengaluru",
        "description": "Premier tech-lifestyle hotel close to major software parks, microbreweries, and luxury shopping.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BLR-MGROAD",
        "location_id": "LOC-BLR",
        "name": "Grand Azure MG Road Luxury Suites",
        "address": "Mahatma Gandhi Road, Bengaluru Central Commercial District",
        "description": "Urban luxury landmark in the bustling heart of Bangalore, surrounded by elite dining and Cubbon Park.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BLR-ELECTRONIC",
        "location_id": "LOC-BLR",
        "name": "Grand Azure Electronic City Executive Towers",
        "address": "Hosur Road, Electronic City Phase 1, Bengaluru",
        "description": "Tailored for IT executives and international business leaders with ergonomic work suites and wellness club.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BLR-NANDI",
        "location_id": "LOC-BLR",
        "name": "Grand Azure Nandi Foothills Resort & Spa",
        "address": "Nandi Hills Valley, Devanahalli, North Bengaluru",
        "description": "Magnificent hillside luxury retreat with panoramic Nandi sunrise views, temperature-controlled pool, and spa.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },

    # 6. Mangaluru (IXE) - 5 Hotels
    {
        "hotel_id": "HTL-IXE-AIRPORT",
        "location_id": "LOC-IXE",
        "name": "Grand Azure Kenjar Airport Resort",
        "address": "Kenjar, Bajpe Airport Highway, Mangaluru (1 km to IXE)",
        "description": "Tranquil hilltop airport resort with direct proximity to Mangaluru Airport and coastal greenery views.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXE-PANAMBUR",
        "location_id": "LOC-IXE",
        "name": "Grand Azure Panambur Beachfront Resort",
        "address": "Panambur Beach Road, Coastal Mangaluru",
        "description": "Arabian Sea beach resort featuring golden sands, water sport excursions, and coastal Mangalorean seafood.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXE-KADRI",
        "location_id": "LOC-IXE",
        "name": "Grand Azure Kadri Hills Luxury Palace",
        "address": "Kadri Hills, Central Mangaluru",
        "description": "Regal hilltop palace hotel surrounded by Kadri Park, ancient temples, and refreshing coastal breezes.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXE-HAMPAN",
        "location_id": "LOC-IXE",
        "name": "Grand Azure Hampankatta City Central",
        "address": "K.S. Rao Road, Hampankatta, Mangaluru",
        "description": "Vibrant central business hotel within walking distance of Mangalore Central Junction and markets.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-IXE-ULLAL",
        "location_id": "LOC-IXE",
        "name": "Grand Azure Ullal Ocean Sands Villa",
        "address": "Someshwar Beach Road, Ullal, Mangaluru",
        "description": "Exclusive oceanfront villa sanctuary where gentle Arabian Sea waves meet private luxury sundecks.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },

    # 7. Kochi (COK) - 5 Hotels
    {
        "hotel_id": "HTL-COK-AIRPORT",
        "location_id": "LOC-COK",
        "name": "Grand Azure Solar Sky Airport Hotel",
        "address": "Airport Road, Nedumbassery, Kochi (800m to COK)",
        "description": "Eco-luxury airport hotel directly adjacent to Cochin International with 24/7 complimentary shuttle.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-COK-FORTKOCHI",
        "location_id": "LOC-COK",
        "name": "Grand Azure Fort Kochi Colonial Heritage",
        "address": "Princess Street, Fort Kochi Heritage Quarter",
        "description": "Charming boutique colonial mansion close to Chinese fishing nets, spice bazaars, and art cafes.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-COK-MARINEDRIVE",
        "location_id": "LOC-COK",
        "name": "Grand Azure Marine Drive Waterfront Tower",
        "address": "Marine Drive Promenade, Ernakulam, Kochi",
        "description": "Towering modern waterfront hotel overlooking Cochin harbour and Rainbow Bridge with rooftop infinity pool.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-COK-KUMBALANGI",
        "location_id": "LOC-COK",
        "name": "Grand Azure Backwater Luxury Villas",
        "address": "Vembanad Lakefront, Kumbalangi, Kochi",
        "description": "World-class backwater resort offering traditional private houseboats, lakefront villas, and Ayurvedic therapies.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-COK-INFOPARK",
        "location_id": "LOC-COK",
        "name": "Grand Azure Kakkanad Tech Park Suites",
        "address": "Seaport-Airport Road, Infopark Phase 1, Kakkanad, Kochi",
        "description": "Modern executive hotel tailored for IT professionals and corporate delegates visiting SmartCity Kochi.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },

    # 8. Thiruvananthapuram (TRV) - 5 Hotels
    {
        "hotel_id": "HTL-TRV-AIRPORT",
        "location_id": "LOC-TRV",
        "name": "Grand Azure Shankumugham Airport Resort",
        "address": "Airport Road, Shanghumugham, Trivandrum (1 km to TRV)",
        "description": "Beachside airport luxury hotel where guests enjoy stunning coastal sunsets and quick 3-minute airport transfers.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRV-KOVALAM",
        "location_id": "LOC-TRV",
        "name": "Grand Azure Kovalam Cliffside Beach Resort",
        "address": "Lighthouse Beach Road, Kovalam, Trivandrum",
        "description": "Legendary beach resort perched on rocky cliff overlooking the Kovalam lighthouse and Arabian Sea.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRV-ROYAL",
        "location_id": "LOC-TRV",
        "name": "Grand Azure Royal Heritage Hotel",
        "address": "East Fort, Near Padmanabhaswamy Temple, Trivandrum",
        "description": "Historic Travancore royal residence offering teakwood architecture, vegetarian royal thali, and quiet luxury.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRV-TECHNO",
        "location_id": "LOC-TRV",
        "name": "Grand Azure Technopark Executive Suites",
        "address": "Kazhakkoottam Highway, Technopark Campus, Trivandrum",
        "description": "Modern business suites with conference halls, high-speed Wi-Fi, and fitness center near Technopark.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-TRV-VARKALA",
        "location_id": "LOC-TRV",
        "name": "Grand Azure Varkala Palm Cliff Retreat",
        "address": "North Cliff, Varkala Beach Promenade, Trivandrum",
        "description": "Bohemian luxury resort on Varkala's red cliffs with panoramic sunset dining and yoga pavilions.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },

    # 9. Kozhikode (CCJ) - 5 Hotels
    {
        "hotel_id": "HTL-CCJ-AIRPORT",
        "location_id": "LOC-CCJ",
        "name": "Grand Azure Karipur Airport Grand Hotel",
        "address": "Calicut Airport Post, Kondotty, Kozhikode (1 km to CCJ)",
        "description": "Full-service transit and luxury hotel catering to Malabar Gulf travelers with VIP airport check-in support.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCJ-BEACH",
        "location_id": "LOC-CCJ",
        "name": "Grand Azure Kozhikode Beachfront Palace",
        "address": "Beach Road, Near Old Sea Pier, Kozhikode",
        "description": "Grand coastal palace on the historic Calicut beach promenade, famous for authentic Malabar Biryani.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCJ-MANANCHIRA",
        "location_id": "LOC-CCJ",
        "name": "Grand Azure Mananchira Heritage Hotel",
        "address": "Mavoor Road, Overlooking Mananchira Square, Kozhikode",
        "description": "Central city hotel facing the historic Mananchira lake, offering colonial charm and modern amenities.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCJ-BEYPORE",
        "location_id": "LOC-CCJ",
        "name": "Grand Azure Beypore Marina Resort",
        "address": "Beypore Port Road, River Chaliyar Estuary, Kozhikode",
        "description": "Unique river-estuary resort near the historic wooden dhow shipbuilding yard with sunset boat cruises.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCJ-WAYANAD",
        "location_id": "LOC-CCJ",
        "name": "Grand Azure Malabar Gateway Retreat",
        "address": "NH 766, Foothills of Thamarassery Ghat, Kozhikode",
        "description": "Lush foothills resort ideal for travelers heading to the misty tea estates of Wayanad.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },

    # 10. Mumbai (BOM) - 5 Hotels
    {
        "hotel_id": "HTL-BOM-AIRPORT",
        "location_id": "LOC-BOM",
        "name": "Grand Azure Terminal 2 Airport Palace",
        "address": "Sahar Airport Road, Andheri East, Mumbai (500m to BOM T2)",
        "description": "Luxury haven right at Mumbai Airport T2 with soundproof suites, express chauffeur, and grand atrium.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BOM-JUHU",
        "location_id": "LOC-BOM",
        "name": "Grand Azure Juhu Beach Luxury Suites",
        "address": "Juhu Tara Road, Juhu Beachfront, Mumbai",
        "description": "Glamorous beachfront hotel frequented by Bollywood royalty, featuring ocean-facing infinity pool.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BOM-BKC",
        "location_id": "LOC-BOM",
        "name": "Grand Azure BKC Financial Tower",
        "address": "Bandra Kurla Complex (BKC), G Block, Mumbai",
        "description": "Sophisticated financial district suites next to major multinational corporate headquarters.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BOM-MARINE",
        "location_id": "LOC-BOM",
        "name": "Grand Azure Marine Drive Waterfront Hotel",
        "address": "Netaji Subhash Chandra Bose Road, Marine Drive, Mumbai",
        "description": "Iconic waterfront landmark on the Queen's Necklace with breathtaking Arabian Sea sunset vistas.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-BOM-POWAI",
        "location_id": "LOC-BOM",
        "name": "Grand Azure Powai Lakeview Sanctuary",
        "address": "Hiranandani Gardens, Powai Lake, Mumbai",
        "description": "Serene neo-classical hotel overlooking Powai Lake, adjacent to prime business parks and IIT Bombay.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },

    # 11. Delhi (DEL) - 5 Hotels
    {
        "hotel_id": "HTL-DEL-AEROCITY",
        "location_id": "LOC-DEL",
        "name": "Grand Azure IGI Aerocity Grand Hotel",
        "address": "Asset Area 4, Hospitality District, Aerocity, Delhi (1 km to DEL)",
        "description": "World-class Aerocity hotel with direct metro connection to Terminal 3, luxury spa, and global dining.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-DEL-LUTYENS",
        "location_id": "LOC-DEL",
        "name": "Grand Azure Lutyens Royal Palace",
        "address": "Barakhamba Road, Connaught Place, Central New Delhi",
        "description": "Aristocratic luxury palace in Delhi's historic power center, close to India Gate and President's Estate.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-DEL-GURGAON",
        "location_id": "LOC-DEL",
        "name": "Grand Azure Cyber City Sky Suites",
        "address": "DLF Cyber City Phase 2, Gurugram / Delhi NCR",
        "description": "Futuristic skyscraper hotel integrated into Gurgaon's Fortune 500 tech district with helipad access.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-DEL-CHANAKYA",
        "location_id": "LOC-DEL",
        "name": "Grand Azure Diplomatic Enclave Hotel",
        "address": "Shantipath, Chanakyapuri, New Delhi",
        "description": "Secure, high-end sanctuary surrounded by embassies, international commissions, and rose gardens.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-DEL-QUTUB",
        "location_id": "LOC-DEL",
        "name": "Grand Azure Qutub Minar Heritage Villa",
        "address": "Mehrauli Archaeological Park Road, South Delhi",
        "description": "Boutique heritage retreat overlooking the majestic 12th-century Qutub Minar with lush courtyards.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },

    # 12. Hyderabad (HYD) - 5 Hotels
    {
        "hotel_id": "HTL-HYD-AIRPORT",
        "location_id": "LOC-HYD",
        "name": "Grand Azure Shamshabad Airport Resort",
        "address": "RGIA Airport Approach Road, Shamshabad, Hyderabad (1.5 km to HYD)",
        "description": "Expansive luxury transit resort with Olympic pool, tennis courts, and 24/7 express airport transfers.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-HYD-HITEC",
        "location_id": "LOC-HYD",
        "name": "Grand Azure Cyber Towers Luxury Hotel",
        "address": "HITEC City Main Road, Madhapur, Hyderabad",
        "description": "Premier tech-district luxury hotel adjacent to Google, Microsoft, and Amazon corporate campuses.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-HYD-BANJARA",
        "location_id": "LOC-HYD",
        "name": "Grand Azure Banjara Hills Royal Palace",
        "address": "Road No. 1, Banjara Hills, Hyderabad",
        "description": "Regal palace hotel in Hyderabad's most exclusive zip code, celebrating Hyderabadi Nizam royal heritage.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-HYD-JUBILEE",
        "location_id": "LOC-HYD",
        "name": "Grand Azure Jubilee Hills Executive Retreat",
        "address": "Road No. 36, Jubilee Hills, Hyderabad",
        "description": "Sophisticated urban retreat surrounded by fine designer boutiques, celebrity residences, and clubs.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-HYD-HUSSAIN",
        "location_id": "LOC-HYD",
        "name": "Grand Azure Hussain Sagar Lakefront Tower",
        "address": "Necklace Road, Tank Bund, Hyderabad",
        "description": "Stunning lakefront property with panoramic views of the Buddha statue and shimmering Hyderabad skyline.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },

    # 13. Goa (GOX) - 5 Hotels
    {
        "hotel_id": "HTL-GOX-AIRPORT",
        "location_id": "LOC-GOX",
        "name": "Grand Azure Mopa Airport Rainforest Resort",
        "address": "Mopa Airport Expressway, Pernem, North Goa (2 km to GOX)",
        "description": "Luxurious rainforest resort just minutes from Goa's new international airport with infinity forest pool.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-GOX-CALANGUTE",
        "location_id": "LOC-GOX",
        "name": "Grand Azure Calangute Beach Luxury Resort",
        "address": "Calangute Beach Road, North Goa",
        "description": "Vibrant beachside resort on Goa's liveliest shoreline with private beach beds, cabanas, and sunset DJ sets.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-GOX-CANDOLIM",
        "location_id": "LOC-GOX",
        "name": "Grand Azure Candolim Beachfront Villa",
        "address": "Fort Aguada Road, Candolim Beach, North Goa",
        "description": "Upscale beachfront property featuring private plunge pools, seafood shack dining, and water sports.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-GOX-PANJIM",
        "location_id": "LOC-GOX",
        "name": "Grand Azure Panaji Heritage Mandovi Hotel",
        "address": "D.B. Marg, River Mandovi Promenade, Panaji, Goa",
        "description": "Portuguese colonial hotel in Goa's Latin Quarter (Fontainhas) overlooking floating casino yachts.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-GOX-COLVA",
        "location_id": "LOC-GOX",
        "name": "Grand Azure South Goa White Sands Palace",
        "address": "Colva Beach Road, South Goa",
        "description": "Tranquil 5-star haven on South Goa's endless white powdery beaches, ideal for peaceful romantic getaways.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },

    # 14. Kolkata (CCU) - 5 Hotels
    {
        "hotel_id": "HTL-CCU-AIRPORT",
        "location_id": "LOC-CCU",
        "name": "Grand Azure Dum Dum Airport Grand Hotel",
        "address": "Jessore Road, Dum Dum, Kolkata (1 km to CCU Airport)",
        "description": "5-star gateway hotel near Kolkata Airport with soundproof executive suites and 24-hr Bengali fine dining.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCU-PARKSTREET",
        "location_id": "LOC-CCU",
        "name": "Grand Azure Park Street Heritage Palace",
        "address": "Park Street Commercial Hub, Central Kolkata",
        "description": "Legendary heritage hotel in the culinary and entertainment epicentre of Kolkata with vintage jazz bar.",
        "rating": 5.0,
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCU-NEWTOWN",
        "location_id": "LOC-CCU",
        "name": "Grand Azure New Town Tech City Suites",
        "address": "Major Arterial Road, Action Area 1, New Town, Kolkata",
        "description": "State-of-the-art smart hotel near Eco Park and IT corridor with rooftop helipad and infinity pool.",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCU-SALTLAKE",
        "location_id": "LOC-CCU",
        "name": "Grand Azure Salt Lake City Tower",
        "address": "Sector V, Electronic Complex, Salt Lake, Kolkata",
        "description": "High-rise executive suites designed for tech leaders and corporate conferences in Salt Lake Sector V.",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80"
    },
    {
        "hotel_id": "HTL-CCU-VICTORIA",
        "location_id": "LOC-CCU",
        "name": "Grand Azure Victoria Memorial View Resort",
        "address": "AJC Bose Road, Overlooking the Maidan, Kolkata",
        "description": "Breathtaking views of Victoria Memorial and the lush green Maidan with colonial afternoon high tea.",
        "rating": 4.9,
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    }
]

INDIAN_ROOMS_TEMPLATE = [
    {
        "room_id": "DLX-SGL",
        "name": "Deluxe Single Room",
        "category": "Standard",
        "description": "Comfortable, ergonomically appointed room designed for solo travelers or professionals with dedicated high-speed workspace.",
        "price_per_night": 45.0,
        "capacity_per_room": 1,
        "total_rooms": 10,
        "amenities": ["King Single Bed", "High-speed Wi-Fi", "Ergonomic Desk", "Smart TV", "City View", "Free Breakfast"],
        "badge": "Popular for Solo / Work",
        "image_url": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "EXE-DBL",
        "name": "Executive Double Room",
        "category": "Executive",
        "description": "Spacious, elegantly appointed room featuring a plush king-size bed, private balcony, and marble rain shower bathroom.",
        "price_per_night": 75.0,
        "capacity_per_room": 2,
        "total_rooms": 15,
        "amenities": ["Plush King Bed", "Private Balcony", "Complimentary Breakfast", "Mini Bar", "4K TV", "Rain Shower"],
        "badge": "Best Value",
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "CORP-STE",
        "name": "Corporate Business Suite",
        "category": "Business",
        "description": "Tailored for company executives and corporate delegations, offering an integrated meeting & lounge area with fiber net.",
        "price_per_night": 135.0,
        "capacity_per_room": 3,
        "total_rooms": 8,
        "amenities": ["Meeting Lounge Area", "High-Speed Fiber Net", "Executive Club Access", "Daily Buffet Breakfast", "Workstation & Monitor", "Soundproof"],
        "badge": "Ideal for Companies",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "FAM-VLA",
        "name": "Luxury Family & Team Villa",
        "category": "Villa",
        "description": "Expansive multi-bedroom villa with private kitchenette, landscaped terrace, and living room for families or corporate teams.",
        "price_per_night": 220.0,
        "capacity_per_room": 5,
        "total_rooms": 5,
        "amenities": ["2 Master Bedrooms", "Private Living Room & Kitchenette", "Garden Terrace", "Complimentary Buffet", "Pool Access", "Dedicated Host"],
        "badge": "Family & Group Choice",
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "PRES-PNT",
        "name": "Presidential Penthouse Suite",
        "category": "Luxury",
        "description": "Ultimate top-floor luxury penthouse with panoramic skyline and runway views, private jacuzzi, and 24/7 personal butler.",
        "price_per_night": 380.0,
        "capacity_per_room": 4,
        "total_rooms": 3,
        "amenities": ["Top Floor Skyline View", "Private Jacuzzi", "24/7 Personal Butler", "Chauffeur Airport Pickup", "Premium Wine Bar", "VIP Dining"],
        "badge": "Ultra Luxury VIP",
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    }
]

def main():
    from database import db_manager
    print("=" * 60)
    print("SEEDING INDIAN AIRPORTS, HOTELS, AND ROOMS DATABASE")
    print("=" * 60)

    # Completely wipe old entries
    print("Clearing old locations, hotels, rooms, bookings, and sessions...")
    db_manager.locations_collection.delete_many({})
    db_manager.hotels_collection.delete_many({})
    db_manager.rooms_collection.delete_many({})
    db_manager.bookings_collection.delete_many({})
    db_manager.sessions_collection.delete_many({})
    print("Collections cleared successfully.")

    # Insert 14 Indian Airport Locations
    from datetime import datetime
    loc_docs = [dict(loc, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for loc in INDIAN_LOCATIONS]
    db_manager.locations_collection.insert_many(loc_docs)
    print(f"Inserted {len(loc_docs)} Indian Airport Locations.")

    # Insert 70 Luxury Hotels (5 per airport)
    hotel_docs = [dict(h, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for h in INDIAN_HOTELS]
    db_manager.hotels_collection.insert_many(hotel_docs)
    print(f"Inserted {len(hotel_docs)} Luxury Hotels (5 per airport).")

    # Insert 350 Room categories (5 per hotel across 70 hotels)
    room_docs = []
    for h in INDIAN_HOTELS:
        for r in INDIAN_ROOMS_TEMPLATE:
            doc = dict(r)
            doc["hotel_id"] = h["hotel_id"]
            doc["hotel_name"] = h["name"]
            doc["location_id"] = h["location_id"]
            doc["available_rooms"] = doc["total_rooms"]
            doc["created_at"] = datetime.utcnow()
            doc["updated_at"] = datetime.utcnow()
            room_docs.append(doc)

    db_manager.rooms_collection.insert_many(room_docs)
    print(f"Inserted {len(room_docs)} Room Categories across all 70 hotels.")

    print("\nVERIFYING SEEDED COUNTS IN MONGODB:")
    loc_count = db_manager.locations_collection.count_documents({})
    hotel_count = db_manager.hotels_collection.count_documents({})
    room_count = db_manager.rooms_collection.count_documents({})
    booking_count = db_manager.bookings_collection.count_documents({})
    print(f"  • Locations: {loc_count} (Expected 14)")
    print(f"  • Hotels:    {hotel_count} (Expected 70, 5 per airport)")
    print(f"  • Rooms:     {room_count} (Expected 350, 5 per hotel)")
    print(f"  • Bookings:  {booking_count} (Expected 0 - clean fresh ledger)")

    # Verify each airport has exactly 5 hotels
    for loc in INDIAN_LOCATIONS:
        cnt = db_manager.hotels_collection.count_documents({"location_id": loc["location_id"]})
        print(f"    - {loc['city']} ({loc['airport_code']}): {cnt} hotels")
        assert cnt >= 5, f"Expected at least 5 hotels for {loc['city']}, got {cnt}"

    print("\nSUCCESS: All Indian airports and hotels seeded successfully!")

if __name__ == "__main__":
    main()
