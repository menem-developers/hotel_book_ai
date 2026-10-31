import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

USA_LOCATIONS = [
    # 1. New York City (JFK)
    {
        "location_id": "LOC-JFK",
        "city": "New York",
        "state": "New York",
        "country": "United States",
        "airport_name": "John F. Kennedy International Airport (JFK)",
        "airport_code": "JFK",
        "aliases": ["new york", "nyc", "jfk", "new york city", "manhattan", "queens", "brooklyn"],
        "description": "The premier global gateway to the Big Apple, world capital of finance, culture, Broadway theater, and iconic skyline landmarks."
    },
    # 2. Los Angeles (LAX)
    {
        "location_id": "LOC-LAX",
        "city": "Los Angeles",
        "state": "California",
        "country": "United States",
        "airport_name": "Los Angeles International Airport (LAX)",
        "airport_code": "LAX",
        "aliases": ["los angeles", "lax", "la", "hollywood", "beverly hills", "california", "socal"],
        "description": "Southern California's entertainment capital, home to Hollywood, palm-lined boulevards, Pacific coast beaches, and luxury lifestyle."
    },
    # 3. Chicago (ORD)
    {
        "location_id": "LOC-ORD",
        "city": "Chicago",
        "state": "Illinois",
        "country": "United States",
        "airport_name": "O'Hare International Airport (ORD)",
        "airport_code": "ORD",
        "aliases": ["chicago", "ord", "ohare", "o'hare", "illinois", "windy city"],
        "description": "The architectural marvel of the Midwest on Lake Michigan, home to the Magnificent Mile, deep dish dining, and world-class jazz culture."
    },
    # 4. Miami (MIA)
    {
        "location_id": "LOC-MIA",
        "city": "Miami",
        "state": "Florida",
        "country": "United States",
        "airport_name": "Miami International Airport (MIA)",
        "airport_code": "MIA",
        "aliases": ["miami", "mia", "south beach", "biscayne", "florida", "sunshine state"],
        "description": "Tropical cosmopolitan capital celebrated for Art Deco South Beach, vibrant nightlife, turquoise ocean waters, and Brickell financial towers."
    },
    # 5. San Francisco (SFO)
    {
        "location_id": "LOC-SFO",
        "city": "San Francisco",
        "state": "California",
        "country": "United States",
        "airport_name": "San Francisco International Airport (SFO)",
        "airport_code": "SFO",
        "aliases": ["san francisco", "sfo", "bay area", "silicon valley", "sf", "california"],
        "description": "Global technology and innovation capital, renowned for the Golden Gate Bridge, historic cable cars, and scenic Pacific hills."
    },
    # 6. Dallas / Fort Worth (DFW)
    {
        "location_id": "LOC-DFW",
        "city": "Dallas",
        "state": "Texas",
        "country": "United States",
        "airport_name": "Dallas/Fort Worth International Airport (DFW)",
        "airport_code": "DFW",
        "aliases": ["dallas", "dfw", "fort worth", "texas", "lone star"],
        "description": "Dynamic commercial powerhouse of Texas, famed for world-class arts districts, Fortune 500 headquarters, and warm Lone Star hospitality."
    },
    # 7. Atlanta (ATL)
    {
        "location_id": "LOC-ATL",
        "city": "Atlanta",
        "state": "Georgia",
        "country": "United States",
        "airport_name": "Hartsfield-Jackson Atlanta International Airport (ATL)",
        "airport_code": "ATL",
        "aliases": ["atlanta", "atl", "georgia", "the atl"],
        "description": "The bustling cultural and economic capital of the American South, home to global titans, Peachtree boulevards, and lush urban canopies."
    },
    # 8. Seattle (SEA)
    {
        "location_id": "LOC-SEA",
        "city": "Seattle",
        "state": "Washington",
        "country": "United States",
        "airport_name": "Seattle-Tacoma International Airport (SEA)",
        "airport_code": "SEA",
        "aliases": ["seattle", "sea", "seatac", "sea-tac", "washington", "emerald city"],
        "description": "The Emerald City of the Pacific Northwest, blending majestic evergreen mountains, Elliott Bay waters, Pike Place, and top cloud-tech titans."
    },
    # 9. Las Vegas (LAS)
    {
        "location_id": "LOC-LAS",
        "city": "Las Vegas",
        "state": "Nevada",
        "country": "United States",
        "airport_name": "Harry Reid International Airport (LAS)",
        "airport_code": "LAS",
        "aliases": ["las vegas", "las", "vegas", "the strip", "nevada"],
        "description": "The world's entertainment and luxury resort capital in the Mojave Desert, iconic for the neon Strip, Michelin dining, and grand spectacles."
    },
    # 10. Boston (BOS)
    {
        "location_id": "LOC-BOS",
        "city": "Boston",
        "state": "Massachusetts",
        "country": "United States",
        "airport_name": "Boston Logan International Airport (BOS)",
        "airport_code": "BOS",
        "aliases": ["boston", "bos", "logan", "massachusetts", "cambridge"],
        "description": "America's cradle of liberty and intellectual capital, renowned for Harvard, MIT, historic Freedom Trail, and Back Bay brownstones."
    },
    # 11. Washington D.C. (IAD)
    {
        "location_id": "LOC-IAD",
        "city": "Washington",
        "state": "District of Columbia",
        "country": "United States",
        "airport_name": "Washington Dulles International Airport (IAD)",
        "airport_code": "IAD",
        "aliases": ["washington", "dc", "washington dc", "iad", "dulles", "district of columbia", "virginia"],
        "description": "The nation's historic capital and center of diplomacy, showcasing the National Mall, iconic monuments, and Smithsonian institutions."
    },
    # 12. Orlando (MCO)
    {
        "location_id": "LOC-MCO",
        "city": "Orlando",
        "state": "Florida",
        "country": "United States",
        "airport_name": "Orlando International Airport (MCO)",
        "airport_code": "MCO",
        "aliases": ["orlando", "mco", "florida", "lake buena vista", "disney"],
        "description": "The world-famous theme park and resort vacation capital, bathed in Central Florida sunshine with championship golf and pristine lakes."
    },
    # 13. Denver (DEN)
    {
        "location_id": "LOC-DEN",
        "city": "Denver",
        "state": "Colorado",
        "country": "United States",
        "airport_name": "Denver International Airport (DEN)",
        "airport_code": "DEN",
        "aliases": ["denver", "den", "colorado", "mile high", "rocky mountains"],
        "description": "The Mile High City at the gateway to the majestic Rocky Mountains, celebrated for alpine adventure, craft culture, and historic LoDo arts."
    },
    # 14. Houston (IAH)
    {
        "location_id": "LOC-IAH",
        "city": "Houston",
        "state": "Texas",
        "country": "United States",
        "airport_name": "George Bush Intercontinental Airport (IAH)",
        "airport_code": "IAH",
        "aliases": ["houston", "iah", "texas", "space city"],
        "description": "Space City and global energy capital, featuring NASA Johnson Space Center, the world's largest medical district, and fine arts museum campus."
    }
]

USA_HOTELS = [
    # -------------------------------------------------------------
    # 1. New York (JFK) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-JFK-001",
        "location_id": "LOC-JFK",
        "name": "Grand Azure JFK Runway Palace & Spa",
        "address": "JFK Access Road, Queens, New York, NY 11430 (1 km to JFK Terminal 4)",
        "description": "5-star luxury airport retreat featuring 24/7 runway chauffeur shuttle, rooftop infinity pool, and soundproof executive suites.",
        "rating": 4.9,
        "amenities": ["24/7 Runway Chauffeur", "Soundproof Suites", "Rooftop Pool", "Full-Service Spa", "Fine Dining", "High-Speed Wi-Fi"],
        "badge": "5-Star Airport Luxury",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["jfk airport", "runway palace", "queens", "new york airport", "jfk terminal"]
    },
    {
        "hotel_id": "HTL-JFK-002",
        "location_id": "LOC-JFK",
        "name": "Grand Azure Central Park Skyline Tower",
        "address": "Central Park South & 5th Avenue, Manhattan, New York, NY 10019",
        "description": "Iconic Manhattan landmark with panoramic Central Park vistas, Michelin-starred gastronomy, and luxury Rolls-Royce city transfers.",
        "rating": 5.0,
        "amenities": ["Central Park Views", "Michelin Dining", "Rolls-Royce Transfers", "Butler Service", "Wellness Center", "Rooftop Lounge"],
        "badge": "Flagship Luxury Landmark",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["central park", "manhattan", "5th ave", "fifth avenue", "times square", "midtown"]
    },
    {
        "hotel_id": "HTL-JFK-003",
        "location_id": "LOC-JFK",
        "name": "Grand Azure Wall Street Financial Regency",
        "address": "Wall Street & Broad Street, Financial District, Manhattan, NY 10005",
        "description": "Distinguished financial district sanctuary tailored for corporate executives, featuring private boardrooms and bespoke concierge.",
        "rating": 4.8,
        "amenities": ["Executive Boardrooms", "Fiber-Optic Net", "Club Lounge", "Cocktail Vault", "Helipad Transfer Access"],
        "badge": "Corporate & Financial Choice",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["wall street", "fidi", "financial district", "downtown manhattan", "broad street"]
    },
    {
        "hotel_id": "HTL-JFK-004",
        "location_id": "LOC-JFK",
        "name": "Grand Azure Brooklyn Bridge Waterfront Resort",
        "address": "Old Fulton Street, DUMBO Waterfront Promenade, Brooklyn, NY 11201",
        "description": "Spectacular waterfront haven overlooking the East River and Manhattan skyline, with direct ferry access and sunset deck.",
        "rating": 4.9,
        "amenities": ["Skyline Sunset Views", "Private Marina Access", "Farm-to-Table Dining", "Heated Pool", "Artisan Coffee Bar"],
        "badge": "Scenic Waterfront",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["brooklyn", "brooklyn bridge", "dumbo", "waterfront", "east river"]
    },
    {
        "hotel_id": "HTL-JFK-005",
        "location_id": "LOC-JFK",
        "name": "Grand Azure SoHo Historic Landmark Suites",
        "address": "Prince Street & Mercer, SoHo Cast Iron Historic District, NY 10012",
        "description": "Boutique heritage residence set within SoHo's historic cobblestone streets, showcasing high-ceiling artist lofts and private courtyards.",
        "rating": 4.8,
        "amenities": ["Historic Lofts", "Courtyard Garden", "Sommelier Tastings", "Designer Boutiques", "Personal Shopper"],
        "badge": "Historic Boutique",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["soho", "prince street", "mercer", "historic loft", "cast iron"]
    },

    # -------------------------------------------------------------
    # 2. Los Angeles (LAX) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-LAX-001",
        "location_id": "LOC-LAX",
        "name": "Grand Azure LAX Runway Luxury Haven",
        "address": "Century Boulevard, Los Angeles, CA 90045 (500m to LAX Airport)",
        "description": "Ultra-convenient luxury airport property featuring sound-insulated suites, 24/7 express terminal chauffeur, and California garden pool.",
        "rating": 4.9,
        "amenities": ["24/7 LAX Chauffeur", "Soundproof Glass", "Outdoor Garden Pool", "Express Check-In", "Executive Club Lounge"],
        "badge": "Top Airport Retreat",
        "image_url": "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=800&q=80",
        "aliases": ["lax airport", "century blvd", "los angeles airport", "lax haven"]
    },
    {
        "hotel_id": "HTL-LAX-002",
        "location_id": "LOC-LAX",
        "name": "Grand Azure Beverly Hills Royal Residence",
        "address": "Rodeo Drive & Wilshire Boulevard, Beverly Hills, CA 90212",
        "description": "World-celebrated palace on iconic Rodeo Drive, offering celebrity-tier service, rooftop cabanas, and private penthouse villas.",
        "rating": 5.0,
        "amenities": ["Rodeo Drive Access", "Rooftop Cabana Pool", "Celebrity Chef Dining", "Full-Service Spa", "Private Chauffeur"],
        "badge": "VIP Celebrity Palace",
        "image_url": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80",
        "aliases": ["beverly hills", "rodeo drive", "wilshire", "luxury residence", "beverly"]
    },
    {
        "hotel_id": "HTL-LAX-003",
        "location_id": "LOC-LAX",
        "name": "Grand Azure Santa Monica Oceanfront Resort",
        "address": "Ocean Avenue & Colorado, Santa Monica Beachfront, CA 90401",
        "description": "Premier beachfront resort overlooking Santa Monica Pier and Pacific sunsets, featuring infinity pool and coastal dining.",
        "rating": 4.9,
        "amenities": ["Direct Beach Access", "Pacific Ocean Views", "Oceanfront Dining", "Bicycle Valet", "Heated Pool"],
        "badge": "Beachfront Luxury",
        "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
        "aliases": ["santa monica", "ocean ave", "beachfront", "santa monica pier", "pacific"]
    },
    {
        "hotel_id": "HTL-LAX-004",
        "location_id": "LOC-LAX",
        "name": "Grand Azure Silicon Beach Tech Suites",
        "address": "Venice Boulevard & Playa Vista Core, Los Angeles, CA 90066",
        "description": "Contemporary high-tech hotel tailored for entertainment and tech executives, with private meeting pods and outdoor courtyards.",
        "rating": 4.8,
        "amenities": ["Silicon Beach Work Pods", "Ultra Fiber Net", "Tech Lounge", "Wellness Gym", "Smart Room Automation"],
        "badge": "Tech & Silicon Beach",
        "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "aliases": ["silicon beach", "playa vista", "venice", "tech suites"]
    },
    {
        "hotel_id": "HTL-LAX-005",
        "location_id": "LOC-LAX",
        "name": "Grand Azure Hollywood Hills Sky Sanctuary",
        "address": "Sunset Boulevard, West Hollywood / Hollywood Hills, CA 90069",
        "description": "Dramatic hillside haven overlooking the glittering Los Angeles basin, with rooftop DJ lounge and private bungalow suites.",
        "rating": 4.8,
        "amenities": ["Sunset Strip Views", "Hillside Bungalows", "Skyline Infinity Pool", "Nightlife Access", "Valet Parking"],
        "badge": "Hillside Sky Resort",
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80",
        "aliases": ["hollywood", "hollywood hills", "sunset blvd", "west hollywood", "weho"]
    },

    # -------------------------------------------------------------
    # 3. Chicago (ORD) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-ORD-001",
        "location_id": "LOC-ORD",
        "name": "Grand Azure O'Hare International Gateway",
        "address": "O'Hare Airport Way, Chicago, IL 60666 (1 km to ORD Airport)",
        "description": "Convenient luxury airport hotel with covered terminal walkways, heated indoor lap pool, and 24/7 flight departure concierge.",
        "rating": 4.8,
        "amenities": ["Direct Airport Shuttles", "Heated Indoor Pool", "Flight Concierge", "Soundproof Suites", "Executive Lounge"],
        "badge": "Airport Gateway",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["ohare", "o'hare", "chicago airport", "ohare gateway", "ord airport"]
    },
    {
        "hotel_id": "HTL-ORD-002",
        "location_id": "LOC-ORD",
        "name": "Grand Azure Magnificent Mile Luxury Palace",
        "address": "North Michigan Avenue, Magnificent Mile, Chicago, IL 60611",
        "description": "Prestigious Michigan Avenue flagship in Chicago's premier shopping and dining district with views of the historic Water Tower.",
        "rating": 5.0,
        "amenities": ["Michigan Ave Location", "Prime Shopping Access", "Michelin-Inspired Steakhouse", "Full Spa & Sauna", "Chauffeur Service"],
        "badge": "Premier Michigan Ave Landmark",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["magnificent mile", "michigan ave", "water tower", "north michigan", "downtown chicago"]
    },
    {
        "hotel_id": "HTL-ORD-003",
        "location_id": "LOC-ORD",
        "name": "Grand Azure The Loop Financial Grand Hotel",
        "address": "South LaSalle Street, Financial District, The Loop, Chicago, IL 60604",
        "description": "Neo-classical luxury residence located in the heart of Chicago's commercial core, surrounded by historic exchanges and theaters.",
        "rating": 4.8,
        "amenities": ["Financial District Core", "Conference Center", "Artisan Whiskey Lounge", "High-Speed Business Hub"],
        "badge": "Financial & Business Core",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["the loop", "loop", "lasalle", "chicago financial"]
    },
    {
        "hotel_id": "HTL-ORD-004",
        "location_id": "LOC-ORD",
        "name": "Grand Azure Navy Pier Lakefront Sanctuary",
        "address": "East Grand Avenue, Navy Pier Promenade / Lake Michigan, Chicago, IL 60611",
        "description": "Breathtaking lakefront sanctuary boasting unobstructed Lake Michigan panoramas, rooftop firepits, and boat docking.",
        "rating": 4.9,
        "amenities": ["Lake Michigan Panoramas", "Rooftop Firepits", "Lake Cruise Concierge", "Seafood Grill", "Glass Solarium"],
        "badge": "Lakefront Scenic",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["navy pier", "lake michigan", "lakefront", "grand ave"]
    },
    {
        "hotel_id": "HTL-ORD-005",
        "location_id": "LOC-ORD",
        "name": "Grand Azure Gold Coast Historic Manor",
        "address": "East Bellevue Place, Gold Coast Historic District, Chicago, IL 60611",
        "description": "Aristocratic boutique mansion nestled in the leafy Gold Coast, steps from Oak Street beach and bespoke designer boutiques.",
        "rating": 4.9,
        "amenities": ["Historic Architecture", "Oak Street Access", "Fireplace Suites", "Private Courtyard", "Sommelier Service"],
        "badge": "Historic Gold Coast",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["gold coast", "bellevue", "oak street", "historic manor"]
    },

    # -------------------------------------------------------------
    # 4. Miami (MIA) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-MIA-001",
        "location_id": "LOC-MIA",
        "name": "Grand Azure MIA Airport Concourse Retreat",
        "address": "NW 36th Street, Miami, FL 33142 (1 km to MIA Airport Terminal)",
        "description": "Resort-style airport property with tropical palm courtyards, 24/7 terminal airport shuttle, and poolside bar.",
        "rating": 4.8,
        "amenities": ["24/7 Airport Shuttle", "Tropical Palm Pool", "Soundproof Suites", "Poolside Mojito Bar", "Early Check-In"],
        "badge": "Airport Oasis",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["mia airport", "miami airport", "concourse retreat", "nw 36th"]
    },
    {
        "hotel_id": "HTL-MIA-002",
        "location_id": "LOC-MIA",
        "name": "Grand Azure South Beach Ocean Promenade",
        "address": "Ocean Drive & 10th Street, South Beach, Miami Beach, FL 33139",
        "description": "Iconic Art Deco beachfront palace directly on Ocean Drive, celebrated for private cabanas, turquoise beach club, and Latin cuisine.",
        "rating": 5.0,
        "amenities": ["Direct Ocean Drive Access", "VIP Beach Club", "Art Deco Heritage", "Rooftop Pool", "Live Music Lounge"],
        "badge": "South Beach Icon",
        "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
        "aliases": ["south beach", "ocean drive", "miami beach", "art deco", "beach club"]
    },
    {
        "hotel_id": "HTL-MIA-003",
        "location_id": "LOC-MIA",
        "name": "Grand Azure Brickell Financial Sky Tower",
        "address": "Brickell Avenue & 14th Street, Financial District, Miami, FL 33131",
        "description": "Sleek glass tower soaring above Miami's financial corridor, with panoramic bayfront views, infinity pool, and Japanese dining.",
        "rating": 4.9,
        "amenities": ["Brickell Ave Location", "Skyline Infinity Pool", "Award-Winning Dining", "Helipad Access", "Luxury Chauffeur"],
        "badge": "Financial & Luxury Tower",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["brickell", "financial district miami", "brickell ave", "sky tower"]
    },
    {
        "hotel_id": "HTL-MIA-004",
        "location_id": "LOC-MIA",
        "name": "Grand Azure Biscayne Bay Marina Resort",
        "address": "Biscayne Boulevard & NE 17th Terrace, Miami, FL 33132",
        "description": "Waterfront resort featuring private deep-water yacht slips, Venetian pool deck, and direct access to Downtown arts centers.",
        "rating": 4.8,
        "amenities": ["Private Yacht Marina", "Biscayne Bay Views", "Venetian Pool Deck", "Water Taxi Service", "Spa & Wellness"],
        "badge": "Yacht Marina Resort",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["biscayne", "biscayne bay", "marina resort", "biscayne blvd"]
    },
    {
        "hotel_id": "HTL-MIA-005",
        "location_id": "LOC-MIA",
        "name": "Grand Azure Coral Gables Historic Villa",
        "address": "Anastasia Avenue & Biltmore Way, Coral Gables, FL 33134",
        "description": "Historic Mediterranean revival estate surrounded by banyan trees and championship golf, offering an oasis of calm elegance.",
        "rating": 4.9,
        "amenities": ["Mediterranean Architecture", "Championship Golf", "Historic Colonnades", "Fine French-Creole Cuisine"],
        "badge": "Historic Estate",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["coral gables", "historic villa", "biltmore", "anastasia"]
    },

    # -------------------------------------------------------------
    # 5. San Francisco (SFO) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-SFO-001",
        "location_id": "LOC-SFO",
        "name": "Grand Azure SFO Bayview Airport Palace",
        "address": "Bayshore Highway, Burlingame, CA 94010 (2 km to SFO Airport)",
        "description": "Picturesque bayfront airport property with scenic runway panoramas across San Francisco Bay, running trails, and shuttle.",
        "rating": 4.8,
        "amenities": ["24/7 SFO Airport Shuttle", "Bayfront Jogging Path", "Soundproof Suites", "Bay View Dining", "Business Hub"],
        "badge": "Bayfront Airport Haven",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["sfo airport", "san francisco airport", "bayview", "burlingame"]
    },
    {
        "hotel_id": "HTL-SFO-002",
        "location_id": "LOC-SFO",
        "name": "Grand Azure Nob Hill Heritage Royal Manor",
        "address": "California & Powell Streets, Nob Hill, San Francisco, CA 94108",
        "description": "Grand historic mansion perched atop Nob Hill with direct cable car access, panoramic Bay Bridge views, and ballroom dining.",
        "rating": 5.0,
        "amenities": ["Cable Car Stop", "Nob Hill Crest Views", "Heritage Grand Ballroom", "Sommelier Wine Vault", "Private Chauffeur"],
        "badge": "Nob Hill Landmark",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["nob hill", "powell", "california street", "cable car", "downtown sf"]
    },
    {
        "hotel_id": "HTL-SFO-003",
        "location_id": "LOC-SFO",
        "name": "Grand Azure Silicon Valley Tech Resort",
        "address": "Sand Hill Road, Menlo Park / Palo Alto Border, CA 94025",
        "description": "Venture capital and tech corridor retreat surrounded by heritage redwoods, with private outdoor cabanas and boardroom suites.",
        "rating": 4.9,
        "amenities": ["Sand Hill Road Core", "Redwood Gardens", "Private Executive Suites", "Ultra Fiber Speed", "Tesla Fleet Transfers"],
        "badge": "Silicon Valley VC Hub",
        "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "aliases": ["silicon valley", "sand hill", "menlo park", "palo alto", "tech resort"]
    },
    {
        "hotel_id": "HTL-SFO-004",
        "location_id": "LOC-SFO",
        "name": "Grand Azure Embarcadero Waterfront Suites",
        "address": "The Embarcadero & Ferry Building Promenade, San Francisco, CA 94105",
        "description": "Waterfront property right on the Embarcadero overlooking the sparkling Bay Bridge and Ferry Building artisan farmers market.",
        "rating": 4.9,
        "amenities": ["Bay Bridge Lights Views", "Ferry Building Access", "Seafood Brasserie", "Rooftop Terrace", "Bicycle Valet"],
        "badge": "Waterfront Landmark",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["embarcadero", "ferry building", "bay bridge", "waterfront suites"]
    },
    {
        "hotel_id": "HTL-SFO-005",
        "location_id": "LOC-SFO",
        "name": "Grand Azure Union Square Premier Tower",
        "address": "Geary Street & Stockton, Union Square Arts District, San Francisco, CA 94102",
        "description": "Centrally situated luxury skyscraper in Union Square, steps from premier department stores, Broadway theater, and Chinatown.",
        "rating": 4.8,
        "amenities": ["Union Square Core", "Theater District Steps", "Designer Retail Access", "Skyline Cocktails", "24/7 Concierge"],
        "badge": "Shopping & Theater Core",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["union square", "geary", "theater district", "premier tower"]
    },

    # -------------------------------------------------------------
    # 6. Dallas / Fort Worth (DFW) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-DFW-001",
        "location_id": "LOC-DFW",
        "name": "Grand Azure DFW Terminal Sky Haven",
        "address": "International Parkway, DFW Airport, TX 75261 (Inside DFW Terminal Area)",
        "description": "Directly integrated into DFW Airport with express Skylink terminal access, soundproof suites, and heated outdoor pool.",
        "rating": 4.9,
        "amenities": ["Skylink Direct Access", "24/7 Runway Chauffeur", "Soundproof Rooms", "Texas Prime Steakhouse", "Full Spa"],
        "badge": "DFW Airport Gateway",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["dfw airport", "dallas airport", "international parkway", "sky haven"]
    },
    {
        "hotel_id": "HTL-DFW-002",
        "location_id": "LOC-DFW",
        "name": "Grand Azure Uptown Dallas Arts Residence",
        "address": "McKinney Avenue & Pearl Street, Uptown Arts District, Dallas, TX 75201",
        "description": "Sophisticated Uptown Dallas residence located along the historic McKinney Avenue trolley line, close to Klyde Warren Park.",
        "rating": 4.9,
        "amenities": ["McKinney Trolley Stop", "Klyde Warren Park Access", "Rooftop Pool & Bar", "Gourmet Texas Bistro", "House Car Service"],
        "badge": "Uptown Cultural Residence",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["uptown dallas", "mckinney", "klyde warren", "arts district dallas"]
    },
    {
        "hotel_id": "HTL-DFW-003",
        "location_id": "LOC-DFW",
        "name": "Grand Azure Downtown Dallas Royal Tower",
        "address": "Commerce Street & Akard, Downtown Financial District, Dallas, TX 75202",
        "description": "Magnificent high-rise hotel featuring panoramic Pegasus skyline vistas, grand ballrooms, and corporate meeting venues.",
        "rating": 4.8,
        "amenities": ["Financial Core Location", "Grand Ballrooms", "Executive Club", "High-Tech Workstations", "Fitness Center"],
        "badge": "Downtown Commerce Hub",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["downtown dallas", "commerce street", "royal tower dallas"]
    },
    {
        "hotel_id": "HTL-DFW-004",
        "location_id": "LOC-DFW",
        "name": "Grand Azure Las Colinas Lakeside Resort",
        "address": "Mandalay Canal Walk, Las Colinas, Irving, TX 75039",
        "description": "Scenic canal-side resort featuring Venetian gondola rides, lakeside dining, championship golf, and headquarters corridor access.",
        "rating": 4.8,
        "amenities": ["Canal Gondolas", "Lakeside Terrace", "Championship Golf Access", "Resort Pool", "Spa & Wellness"],
        "badge": "Lakeside Oasis",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["las colinas", "irving", "mandalay canal", "lakeside resort"]
    },
    {
        "hotel_id": "HTL-DFW-005",
        "location_id": "LOC-DFW",
        "name": "Grand Azure Fort Worth Stockyards Heritage Villa",
        "address": "Exchange Avenue & Main, Historic Stockyards, Fort Worth, TX 76164",
        "description": "Western luxury boutique villa celebrating Fort Worth heritage with artisan leather finishings, saloons, and rodeos.",
        "rating": 4.9,
        "amenities": ["Stockyards Location", "Artisan Western Suites", "Private Whiskey Saloon", "Rodeo Concierge", "Firepit Courtyard"],
        "badge": "Western Heritage Luxury",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["fort worth", "stockyards", "exchange ave", "heritage villa"]
    },

    # -------------------------------------------------------------
    # 7. Atlanta (ATL) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-ATL-001",
        "location_id": "LOC-ATL",
        "name": "Grand Azure ATL Terminal Chauffeur Retreat",
        "address": "Hartsfield Center Parkway, Atlanta, GA 30354 (1.2 km to ATL Airport)",
        "description": "Premier airport sanctuary right by the world's busiest hub, offering private terminal chauffeur, indoor pool, and Southern hospitality.",
        "rating": 4.9,
        "amenities": ["24/7 Terminal Chauffeur", "Indoor Heated Pool", "Southern Gastronomy", "Soundproof Suites", "Executive Lounge"],
        "badge": "World-Class Airport Hub",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["atl airport", "atlanta airport", "hartsfield", "chauffeur retreat"]
    },
    {
        "hotel_id": "HTL-ATL-002",
        "location_id": "LOC-ATL",
        "name": "Grand Azure Buckhead Grand Royal Residence",
        "address": "Peachtree Road NE, Buckhead Luxury Quarter, Atlanta, GA 30326",
        "description": "The jewel of Buckhead, surrounded by luxury retail, fine dining, private spa retreats, and manicured southern gardens.",
        "rating": 5.0,
        "amenities": ["Peachtree Road Access", "Buckhead Shopping Valet", "Award-Winning Spa", "Butler Service", "Rolls-Royce Car"],
        "badge": "Buckhead Luxury Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["buckhead", "peachtree", "peachtree road", "royal residence atlanta"]
    },
    {
        "hotel_id": "HTL-ATL-003",
        "location_id": "LOC-ATL",
        "name": "Grand Azure Midtown Arts & Tech Tower",
        "address": "Spring Street NW & 14th Street, Midtown Innovation District, Atlanta, GA 30309",
        "description": "Modern skyscraper located between Georgia Tech and the Woodruff Arts Center, featuring panoramic skyline views and tech suites.",
        "rating": 4.8,
        "amenities": ["Midtown Arts Core", "Tech Innovation Lounge", "Infinity Skyline Pool", "Craft Cocktail Bar", "Fiber Net"],
        "badge": "Midtown Innovation & Arts",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["midtown atlanta", "spring street", "woodruff", "midtown tower"]
    },
    {
        "hotel_id": "HTL-ATL-004",
        "location_id": "LOC-ATL",
        "name": "Grand Azure Centennial Park Palace",
        "address": "Centennial Olympic Park Drive, Downtown Atlanta, GA 30313",
        "description": "Centrally located overlooking Centennial Olympic Park, steps from the Georgia Aquarium, World of Coca-Cola, and Mercedes-Benz Stadium.",
        "rating": 4.8,
        "amenities": ["Centennial Park Views", "Aquarium Steps", "Stadium Concierge", "Southern Steakhouse", "Rooftop Terrace"],
        "badge": "Centennial Park Downtown",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["centennial park", "downtown atlanta", "georgia aquarium", "mercedes benz stadium"]
    },
    {
        "hotel_id": "HTL-ATL-005",
        "location_id": "LOC-ATL",
        "name": "Grand Azure Perimeter Tech Park Suites",
        "address": "Concourse Parkway, Perimeter Center / Sandy Springs, GA 30328",
        "description": "Corporate campus retreat set beside the iconic King and Queen towers, featuring executive boardrooms and parkland trails.",
        "rating": 4.7,
        "amenities": ["Perimeter Center Core", "King & Queen Views", "Corporate Boardrooms", "Tennis Courts", "Nature Trail Access"],
        "badge": "Corporate Perimeter",
        "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "aliases": ["perimeter", "sandy springs", "concourse", "tech park atlanta"]
    },

    # -------------------------------------------------------------
    # 8. Seattle (SEA) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-SEA-001",
        "location_id": "LOC-SEA",
        "name": "Grand Azure SeaTac Runway Luxury Haven",
        "address": "International Boulevard, SeaTac, WA 98158 (800m to SEA Airport)",
        "description": "Warm Pacific Northwest airport retreat with 24/7 SeaTac chauffeur, indoor cedar sauna, and soundproof mountain-view suites.",
        "rating": 4.8,
        "amenities": ["24/7 SeaTac Chauffeur", "Indoor Cedar Sauna", "Mt. Rainier Views", "Pacific Salmon Bistro", "Soundproof Suites"],
        "badge": "SeaTac Luxury Haven",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["seatac", "sea airport", "seattle airport", "seatac haven"]
    },
    {
        "hotel_id": "HTL-SEA-002",
        "location_id": "LOC-SEA",
        "name": "Grand Azure Pike Place Waterfront Palace",
        "address": "1st Avenue & Pike Street, Downtown Seattle, WA 98101",
        "description": "Iconic Seattle landmark overlooking Pike Place Market and Puget Sound, renowned for fresh seafood dining and Puget Sound ferry views.",
        "rating": 5.0,
        "amenities": ["Pike Place Market Steps", "Puget Sound Panoramas", "Rooftop Sunset Lounge", "Bespoke Coffee Bar", "Waterfront Access"],
        "badge": "Pike Place Waterfront Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["pike place", "downtown seattle", "puget sound", "1st ave", "waterfront seattle"]
    },
    {
        "hotel_id": "HTL-SEA-003",
        "location_id": "LOC-SEA",
        "name": "Grand Azure South Lake Union Cloud Tech Tower",
        "address": "Westlake Avenue N & Mercer Street, South Lake Union, Seattle, WA 98109",
        "description": "Futuristic skyscraper in the heart of Seattle's global cloud computing and biotech corridor, steps from Lake Union park.",
        "rating": 4.9,
        "amenities": ["Cloud Tech Campus Core", "Lake Union Streetcar", "Smart Work Suites", "Artisan Roastery", "Rooftop Firepits"],
        "badge": "Cloud Tech Hub",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["south lake union", "slu", "amazon campus", "westlake", "tech tower seattle"]
    },
    {
        "hotel_id": "HTL-SEA-004",
        "location_id": "LOC-SEA",
        "name": "Grand Azure Elliott Bay Marina Resort",
        "address": "Alaskan Way & Pier 66, Elliott Bay Harbor, Seattle, WA 98121",
        "description": "Dramatic maritime resort situated on Elliott Bay with private cruise embarkation concierge and Olympic Mountain panoramas.",
        "rating": 4.8,
        "amenities": ["Olympic Mountain Views", "Cruise Pier Access", "Maritime Oyster Bar", "Heated Waterfront Terrace", "Marina Slips"],
        "badge": "Elliott Bay Scenic",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["elliott bay", "alaskan way", "pier 66", "marina resort seattle"]
    },
    {
        "hotel_id": "HTL-SEA-005",
        "location_id": "LOC-SEA",
        "name": "Grand Azure Bellevue Downtown Grand Suites",
        "address": "Bellevue Way NE & NE 8th Street, Downtown Bellevue, WA 98004",
        "description": "High-end Eastside retreat surrounded by luxury shopping, tech headquarters, and manicured parks across Lake Washington.",
        "rating": 4.9,
        "amenities": ["Bellevue Square Access", "Lake Washington Proximity", "Executive Boardrooms", "Indoor Lap Pool", "Fine Asian Dining"],
        "badge": "Bellevue Eastside Luxury",
        "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "aliases": ["bellevue", "bellevue square", "eastside", "bellevue suites"]
    },

    # -------------------------------------------------------------
    # 9. Las Vegas (LAS) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-LAS-001",
        "location_id": "LOC-LAS",
        "name": "Grand Azure LAS Sky Harbor Airport Sanctuary",
        "address": "Wayne Newton Boulevard, Las Vegas, NV 89119 (1 km to LAS Airport)",
        "description": "Peaceful non-gaming oasis minutes from the airport terminals and the south end of the Strip, with 24/7 VIP shuttle.",
        "rating": 4.8,
        "amenities": ["24/7 VIP Shuttle", "Non-Gaming Oasis", "Lagoon Pool", "Express Check-In", "Steakhouse Dining"],
        "badge": "Airport Oasis",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["las airport", "vegas airport", "wayne newton", "las sanctuary"]
    },
    {
        "hotel_id": "HTL-LAS-002",
        "location_id": "LOC-LAS",
        "name": "Grand Azure Bellagio Strip Grand Palace",
        "address": "Las Vegas Boulevard South, The Strip, Las Vegas, NV 89109",
        "description": "Ultra-glamorous mega-resort situated center-Strip, featuring iconic fountain spectacles, Michelin-starred culinary villas, and VIP casino.",
        "rating": 5.0,
        "amenities": ["Center-Strip Location", "Iconic Fountains View", "Michelin Dining", "VIP Gaming Salon", "Dayclub & Nightclub Access"],
        "badge": "Center-Strip Mega Palace",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["the strip", "bellagio", "las vegas strip", "strip palace", "center strip"]
    },
    {
        "hotel_id": "HTL-LAS-003",
        "location_id": "LOC-LAS",
        "name": "Grand Azure Downtown Fremont Arts Manor",
        "address": "East Fremont Street, Downtown Arts District, Las Vegas, NV 89101",
        "description": "Vibrant boutique hotel blending vintage neon glamour with modern culinary pop-ups and live entertainment in historic Downtown.",
        "rating": 4.7,
        "amenities": ["Fremont Experience Access", "Vintage Neon Courtyard", "Rooftop Pool & Stage", "Craft Cocktail Saloon"],
        "badge": "Downtown Arts & Fremont",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["fremont", "downtown vegas", "fremont street", "arts district vegas"]
    },
    {
        "hotel_id": "HTL-LAS-004",
        "location_id": "LOC-LAS",
        "name": "Grand Azure Red Rock Mountain Spa & Resort",
        "address": "Red Rock Canyon Road, Summerlin Foothills, Las Vegas, NV 89135",
        "description": "Tranquil desert sanctuary nestled against the crimson sandstone of Red Rock Canyon, offering world-class spa and golf.",
        "rating": 4.9,
        "amenities": ["Red Rock Canyon Vistas", "Sandstone Spa", "Championship Golf", "Poolside Cabana Village", "Hiking Guide"],
        "badge": "Desert Canyon Sanctuary",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["red rock", "summerlin", "red rock canyon", "canyon spa"]
    },
    {
        "hotel_id": "HTL-LAS-005",
        "location_id": "LOC-LAS",
        "name": "Grand Azure Wynn Vista Luxury Penthouse Tower",
        "address": "Sands Avenue & Las Vegas Blvd, North Strip, Las Vegas, NV 89109",
        "description": "Opulent high-roller penthouse skyscraper featuring floor-to-ceiling glass views, private atrium waterfalls, and helicopter transfers.",
        "rating": 4.9,
        "amenities": ["Penthouse Sky Suites", "Helicopter Transfers", "Atrium Waterfalls", "Private Butler Floor", "Golf Course Access"],
        "badge": "High-Roller Penthouse",
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80",
        "aliases": ["wynn", "sands", "north strip", "high roller tower"]
    },

    # -------------------------------------------------------------
    # 10. Boston (BOS) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-BOS-001",
        "location_id": "LOC-BOS",
        "name": "Grand Azure Boston Logan Harbor Palace",
        "address": "Harborside Drive, Boston Logan Airport, MA 02128 (Direct Airport Access)",
        "description": "Premier harborfront airport retreat offering water taxi connections to Downtown Boston, soundproof suites, and harbor dining.",
        "rating": 4.8,
        "amenities": ["Water Taxi to Downtown", "24/7 Logan Shuttle", "Harbor Skyline Views", "New England Chowder Bistro", "Indoor Pool"],
        "badge": "Harbor Airport Palace",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["logan", "boston airport", "harborside", "logan palace"]
    },
    {
        "hotel_id": "HTL-BOS-002",
        "location_id": "LOC-BOS",
        "name": "Grand Azure Back Bay Copley Residence",
        "address": "Boylston Street & Copley Square, Back Bay, Boston, MA 02116",
        "description": "Aristocratic luxury landmark in historic Back Bay overlooking Trinity Church, with high-tea salon and Newbury Street retail access.",
        "rating": 5.0,
        "amenities": ["Copley Square Views", "Newbury Street Shopping", "Historic High Tea", "Butler Service", "House Car Valet"],
        "badge": "Back Bay Landmark Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["back bay", "copley", "boylston", "newbury", "downtown boston"]
    },
    {
        "hotel_id": "HTL-BOS-003",
        "location_id": "LOC-BOS",
        "name": "Grand Azure Cambridge Innovation Suites",
        "address": "Kendall Square & Broadway, Cambridge, MA 02142 (Adjacent to MIT & Harvard)",
        "description": "High-tech innovation retreat in Kendall Square, favored by biotech founders and academic dignitaries, featuring smart suites.",
        "rating": 4.9,
        "amenities": ["Kendall Square Core", "MIT & Harvard Access", "Smart Suites", "Innovation Conference Lab", "Charles River Views"],
        "badge": "Academic & Biotech Core",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["cambridge", "kendall", "mit", "harvard", "innovation suites"]
    },
    {
        "hotel_id": "HTL-BOS-004",
        "location_id": "LOC-BOS",
        "name": "Grand Azure Boston Seaport Waterfront Resort",
        "address": "Seaport Boulevard & Boston Harbor, Seaport District, Boston, MA 02210",
        "description": "Chic waterfront resort in the buzzing Seaport District, showcasing rooftop harbor terraces, contemporary art, and fresh lobster bars.",
        "rating": 4.9,
        "amenities": ["Harbor Terrace Views", "Seaport Dining Access", "Rooftop Lounge", "Harbor Ferry Steps", "Artisan Cocktail Bar"],
        "badge": "Seaport Waterfront",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["seaport", "seaport district", "boston harbor", "seaport blvd"]
    },
    {
        "hotel_id": "HTL-BOS-005",
        "location_id": "LOC-BOS",
        "name": "Grand Azure Beacon Hill Heritage Manor",
        "address": "Charles Street & Mount Vernon, Historic Beacon Hill, Boston, MA 02108",
        "description": "Exclusive boutique hotel set among gas-lit cobblestone streets and Federal-era brick townhouses near the Boston Common.",
        "rating": 4.8,
        "amenities": ["Gas-Lit Cobblestone Streets", "Boston Common Access", "Working Fireplaces", "Private Library & Bar"],
        "badge": "Historic Beacon Hill",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["beacon hill", "charles street", "boston common", "heritage manor"]
    },

    # -------------------------------------------------------------
    # 11. Washington D.C. (IAD) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-IAD-001",
        "location_id": "LOC-IAD",
        "name": "Grand Azure Dulles Runway Executive Palace",
        "address": "Aviation Drive, Dulles International Airport, VA 20166 (Inside Airport Complex)",
        "description": "Diplomatic and executive airport retreat with direct access to Dulles terminals, AeroTrain, and private secure briefing suites.",
        "rating": 4.8,
        "amenities": ["24/7 Dulles Chauffeur", "Secure Briefing Rooms", "Soundproof Suites", "Executive Lounge", "Indoor Pool"],
        "badge": "Diplomatic Airport Palace",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["dulles", "iad airport", "aviation drive", "dulles palace"]
    },
    {
        "hotel_id": "HTL-IAD-002",
        "location_id": "LOC-IAD",
        "name": "Grand Azure Georgetown Presidential Residence",
        "address": "M Street NW & Wisconsin Avenue, Historic Georgetown, Washington, DC 20007",
        "description": "Historic landmark residence overlooking the C&O Canal and Potomac River, frequented by heads of state and international delegations.",
        "rating": 5.0,
        "amenities": ["Georgetown Historic Core", "Potomac River Views", "Presidential Butler Service", "Diplomatic Security Standards", "Fine French Dining"],
        "badge": "Diplomatic Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["georgetown", "m street", "potomac", "presidential residence dc", "downtown dc"]
    },
    {
        "hotel_id": "HTL-IAD-003",
        "location_id": "LOC-IAD",
        "name": "Grand Azure National Mall Diplomatic Tower",
        "address": "Pennsylvania Avenue NW, Downtown Washington, DC 20004",
        "description": "Prominently located on Pennsylvania Avenue between the White House and US Capitol, with views of the Washington Monument.",
        "rating": 4.9,
        "amenities": ["Pennsylvania Ave Address", "White House Proximity", "Rooftop Monument Views", "Executive Club", "House Chauffeur"],
        "badge": "Monument & Mall Luxury",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["national mall", "pennsylvania ave", "white house", "capitol", "monument tower"]
    },
    {
        "hotel_id": "HTL-IAD-004",
        "location_id": "LOC-IAD",
        "name": "Grand Azure Capitol Hill Statesman Suites",
        "address": "New Jersey Avenue SE, Capitol Hill Historic District, Washington, DC 20003",
        "description": "Distinguished address steps from the US Capitol and Library of Congress, tailored for congressional leaders and policy summits.",
        "rating": 4.8,
        "amenities": ["Capitol Steps", "Congressional Suites", "Private Dining Library", "High-Security Standards", "Fiber Net"],
        "badge": "Capitol Hill Luxury",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["capitol hill", "congressional", "statesman suites", "new jersey ave"]
    },
    {
        "hotel_id": "HTL-IAD-005",
        "location_id": "LOC-IAD",
        "name": "Grand Azure Dupont Circle Heritage Manor",
        "address": "Connecticut Avenue NW, Embassy Row / Dupont Circle, Washington, DC 20036",
        "description": "Boutique Beaux-Arts palace nestled on Embassy Row, surrounded by international embassies, diplomatic gardens, and bistros.",
        "rating": 4.8,
        "amenities": ["Embassy Row Address", "Beaux-Arts Architecture", "Courtyard Garden", "Sommelier Wine Vault"],
        "badge": "Embassy Row Heritage",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["dupont circle", "embassy row", "connecticut ave", "dupont manor"]
    },

    # -------------------------------------------------------------
    # 12. Orlando (MCO) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-MCO-001",
        "location_id": "LOC-MCO",
        "name": "Grand Azure MCO Airport Concourse Haven",
        "address": "Jeff Fuqua Boulevard, Orlando International Airport, FL 32827",
        "description": "Resort-style airport property featuring atrium palm trees, 24/7 express terminal shuttle, soundproof suites, and heated outdoor pool.",
        "rating": 4.8,
        "amenities": ["24/7 Terminal Shuttle", "Heated Outdoor Pool", "Soundproof Family Suites", "Early Theme Park Concierge", "Lagoon Bar"],
        "badge": "Airport Family Oasis",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["mco airport", "orlando airport", "jeff fuqua", "concourse haven"]
    },
    {
        "hotel_id": "HTL-MCO-002",
        "location_id": "LOC-MCO",
        "name": "Grand Azure Lake Buena Vista Grand Palace",
        "address": "Hotel Plaza Boulevard, Lake Buena Vista / Disney Springs Core, FL 32830",
        "description": "Magnificent family & luxury resort with private lazy river, character dining, fireworks viewing lounge, and park shuttles.",
        "rating": 5.0,
        "amenities": ["Fireworks View Lounge", "Private Lazy River", "VIP Park Shuttles", "Full-Service Spa", "Kids Adventure Club"],
        "badge": "Lake Buena Vista Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["lake buena vista", "disney", "disney springs", "buena vista palace", "fireworks view"]
    },
    {
        "hotel_id": "HTL-MCO-003",
        "location_id": "LOC-MCO",
        "name": "Grand Azure International Drive Sky Resort",
        "address": "International Drive, Convention & Entertainment Corridor, Orlando, FL 32819",
        "description": "High-rise resort tower in the center of International Drive, offering sky dining, rooftop pool, and convention walkway.",
        "rating": 4.8,
        "amenities": ["Convention Center Walkway", "Rooftop Sky Dining", "Resort Pool with Cabanas", "Game Lounge", "Theme Park Shuttles"],
        "badge": "Convention & Sky Resort",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["international drive", "i-drive", "convention center orlando", "sky resort"]
    },
    {
        "hotel_id": "HTL-MCO-004",
        "location_id": "LOC-MCO",
        "name": "Grand Azure Universal Sunset Oasis Resort",
        "address": "Universal Boulevard & Adventure Way, Theme Park District, Orlando, FL 32819",
        "description": "Tropical paradise resort situated minutes from Universal Studios, with sandy zero-entry pool, waterfalls, and private cabanas.",
        "rating": 4.9,
        "amenities": ["Universal Parks Shuttle", "Zero-Entry Sand Pool", "Tropical Waterfalls", "Tiki Cocktail Lounge", "Family Suites"],
        "badge": "Theme Park Oasis",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["universal", "universal studios", "universal blvd", "sunset oasis"]
    },
    {
        "hotel_id": "HTL-MCO-005",
        "location_id": "LOC-MCO",
        "name": "Grand Azure Winter Park Heritage Villa",
        "address": "Park Avenue & Canton, Historic Winter Park Lakes, FL 32789",
        "description": "Boutique lakeside villa in historic Winter Park, surrounded by cobblestone streets, scenic chain of lakes boat tours, and museums.",
        "rating": 4.9,
        "amenities": ["Chain of Lakes Access", "Park Avenue Boutiques", "Scenic Boat Tours", "Courtyard Dining", "Historic Ambiance"],
        "badge": "Lakeside Heritage Villa",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["winter park", "park ave orlando", "chain of lakes", "heritage villa orlando"]
    },

    # -------------------------------------------------------------
    # 13. Denver (DEN) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-DEN-001",
        "location_id": "LOC-DEN",
        "name": "Grand Azure Denver International Runway Spa",
        "address": "Peña Boulevard, Denver International Airport, CO 80249 (Adjacent to Terminal)",
        "description": "Striking architectural hotel connected directly to DIA terminal, featuring heated mountain-view pool and Rocky Mountain spa.",
        "rating": 4.9,
        "amenities": ["Direct Terminal Access", "Rocky Mountain Views", "Heated Outdoor Pool", "Alpine Spa", "Soundproof Suites"],
        "badge": "Mile-High Airport Spa",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["den airport", "denver airport", "dia", "peña blvd", "runway spa"]
    },
    {
        "hotel_id": "HTL-DEN-002",
        "location_id": "LOC-DEN",
        "name": "Grand Azure LoDo Union Station Grand Hotel",
        "address": "Wazee Street & 17th, Lower Downtown (LoDo) Historic District, Denver, CO 80202",
        "description": "Prestigious luxury residence steps from historic Denver Union Station, Coors Field, and LoDo's vibrant dining and craft breweries.",
        "rating": 5.0,
        "amenities": ["Union Station Steps", "Airport Train Direct", "Rooftop Mountain View Deck", "Colorado Craft Grill", "House Tesla Car"],
        "badge": "LoDo Historic Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["lodo", "union station", "downtown denver", "wazee", "coors field"]
    },
    {
        "hotel_id": "HTL-DEN-003",
        "location_id": "LOC-DEN",
        "name": "Grand Azure Cherry Creek Luxury Residence",
        "address": "East 1st Avenue & University, Cherry Creek Shopping District, Denver, CO 80206",
        "description": "Chic residential luxury hotel in Denver's upscale Cherry Creek enclave, surrounded by art galleries and outdoor cafes.",
        "rating": 4.9,
        "amenities": ["Cherry Creek Shopping", "Art Gallery Corridor", "Rooftop Pool & Lounge", "Full Spa & Wellness", "Bicycle Valet"],
        "badge": "Cherry Creek Enclave",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["cherry creek", "cherry creek north", "luxury residence denver"]
    },
    {
        "hotel_id": "HTL-DEN-004",
        "location_id": "LOC-DEN",
        "name": "Grand Azure Rocky Mountain Foothills Resort",
        "address": "Red Rocks Park Vista Way, Golden / West Denver Foothills, CO 80401",
        "description": "Alpine foothill sanctuary minutes from iconic Red Rocks Amphitheatre, offering outdoor firepits, hiking guides, and mountain spas.",
        "rating": 4.8,
        "amenities": ["Red Rocks Amphitheatre Shuttles", "Mountain Firepits", "Hiking & Ski Guides", "Alpine Hot Tubs", "Lodge Dining"],
        "badge": "Red Rocks Foothills Resort",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["rocky mountains", "red rocks", "golden", "foothills resort", "alpine"]
    },
    {
        "hotel_id": "HTL-DEN-005",
        "location_id": "LOC-DEN",
        "name": "Grand Azure Boulder Alpine Panorama Manor",
        "address": "Pearl Street & 9th, Historic Boulder Foothills, CO 80302",
        "description": "Boutique alpine manor located on historic Pearl Street overlooking the iconic Flatirons rock formations, with organic culinary menus.",
        "rating": 4.9,
        "amenities": ["Flatirons Views", "Pearl Street Mall Steps", "Farm-to-Table Gastronomy", "Organic Wellness Spa", "Mountain Bikes"],
        "badge": "Boulder Flatirons Manor",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["boulder", "pearl street", "flatirons", "panorama manor"]
    },

    # -------------------------------------------------------------
    # 14. Houston (IAH) - 5 Hotels
    # -------------------------------------------------------------
    {
        "hotel_id": "HTL-IAH-001",
        "location_id": "LOC-IAH",
        "name": "Grand Azure IAH Bush Terminal Sky Sanctuary",
        "address": "John F. Kennedy Boulevard, Houston, TX 77032 (Adjacent to IAH Terminal)",
        "description": "Contemporary airport property with express underground train to all IAH terminals, soundproof suites, and heated outdoor pool.",
        "rating": 4.8,
        "amenities": ["Direct Terminal Train", "24/7 IAH Shuttle", "Soundproof Suites", "Texas Smokehouse & Grill", "Outdoor Pool"],
        "badge": "IAH Airport Sanctuary",
        "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "aliases": ["iah airport", "houston airport", "bush intercontinental", "jfk blvd houston"]
    },
    {
        "hotel_id": "HTL-IAH-002",
        "location_id": "LOC-IAH",
        "name": "Grand Azure Galleria Uptown Luxury Palace",
        "address": "Westheimer Road & Post Oak, Uptown Galleria District, Houston, TX 77056",
        "description": "Prestigious palace in Houston's premier shopping and business corridor, featuring designer suites, full spa, and rooftop cabanas.",
        "rating": 5.0,
        "amenities": ["Galleria Shopping Access", "Post Oak Luxury Corridor", "Championship Spa", "Helipad Access", "Rolls-Royce House Car"],
        "badge": "Galleria Uptown Flagship",
        "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
        "aliases": ["galleria", "uptown houston", "westheimer", "post oak", "downtown houston"]
    },
    {
        "hotel_id": "HTL-IAH-003",
        "location_id": "LOC-IAH",
        "name": "Grand Azure Energy Corridor Tech Suites",
        "address": "Eldridge Parkway & I-10, Energy Corridor, Houston, TX 77079",
        "description": "Tailored for international energy executives and corporate delegations, with boardroom facilities and Terry Hershey park trail access.",
        "rating": 4.8,
        "amenities": ["Energy Corridor Core", "Corporate Boardrooms", "High-Speed Fiber", "Park Trail Proximity", "Executive Lounge"],
        "badge": "Energy Corridor Corporate",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
        "aliases": ["energy corridor", "eldridge", "energy suites", "i-10 houston"]
    },
    {
        "hotel_id": "HTL-IAH-004",
        "location_id": "LOC-IAH",
        "name": "Grand Azure Downtown Houston Grand Tower",
        "address": "Texas Avenue & Main Street, Downtown Theater District, Houston, TX 77002",
        "description": "Historic high-rise in Downtown Houston's theater and cultural core, with underground tunnel network access and rooftop deck.",
        "rating": 4.8,
        "amenities": ["Theater District Steps", "Downtown Tunnel Network", "Skyline Rooftop Deck", "Fine Texas Dining", "Business Center"],
        "badge": "Downtown Theater Core",
        "image_url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800&q=80",
        "aliases": ["downtown houston", "texas avenue", "theater district", "grand tower houston"]
    },
    {
        "hotel_id": "HTL-IAH-005",
        "location_id": "LOC-IAH",
        "name": "Grand Azure The Woodlands Lakeside Resort",
        "address": "Woodlands Parkway & Waterway Square, The Woodlands, TX 77380",
        "description": "Scenic master-planned lakeside resort surrounded by towering pine trees, waterway cruisers, golf courses, and open-air pavilions.",
        "rating": 4.9,
        "amenities": ["Woodlands Waterway Cruiser", "Championship Golf", "Heated Resort Pool", "Pine Forest Trails", "Fine Dining"],
        "badge": "Woodlands Lakeside Oasis",
        "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80",
        "aliases": ["the woodlands", "woodlands waterway", "lakeside resort houston"]
    }
]

USA_ROOMS_TEMPLATE = [
    {
        "room_id": "DLX-SGL",
        "name": "Deluxe Single Room",
        "category": "Standard",
        "description": "Ergonomically appointed luxury room designed for solo travelers or professionals with dedicated high-speed fiber workspace.",
        "price_per_night": 145.0,
        "capacity_per_room": 1,
        "total_rooms": 10,
        "amenities": ["King Single Bed", "High-Speed Wi-Fi", "Ergonomic Desk", "Smart 4K TV", "City Skyline View", "Gourmet Breakfast"],
        "badge": "Popular for Solo / Work",
        "image_url": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "EXE-DBL",
        "name": "Executive Double Room",
        "category": "Executive",
        "description": "Spacious, elegantly appointed room featuring a plush king-size bed, private balcony, and Italian marble rain shower.",
        "price_per_night": 220.0,
        "capacity_per_room": 2,
        "total_rooms": 15,
        "amenities": ["Plush King Bed", "Private Balcony", "Complimentary Breakfast", "Artisan Mini Bar", "55-inch OLED TV", "Rain Shower"],
        "badge": "Best Value",
        "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "CORP-STE",
        "name": "Corporate Business Suite",
        "category": "Business",
        "description": "Tailored for company executives and corporate delegations, offering an integrated meeting & lounge area with fiber net.",
        "price_per_night": 350.0,
        "capacity_per_room": 3,
        "total_rooms": 8,
        "amenities": ["Meeting Lounge Area", "High-Speed Fiber Net", "Executive Club Access", "Daily Buffet Breakfast", "Workstation & Dual Monitors", "Soundproof"],
        "badge": "Ideal for Companies",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "FAM-VLA",
        "name": "Luxury Family & Team Villa",
        "category": "Villa",
        "description": "Expansive multi-bedroom villa with private kitchenette, landscaped terrace, and living room for families or corporate teams.",
        "price_per_night": 520.0,
        "capacity_per_room": 5,
        "total_rooms": 5,
        "amenities": ["2 Master Bedrooms", "Private Living Room & Kitchenette", "Scenic Terrace", "Complimentary Buffet", "Heated Pool Access", "Dedicated Host"],
        "badge": "Family & Group Choice",
        "image_url": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=800&q=80"
    },
    {
        "room_id": "PRES-PNT",
        "name": "Presidential Penthouse Suite",
        "category": "Penthouse",
        "description": "Ultra-exclusive top-floor penthouse with 360-degree skyline views, private jacuzzi terrace, champagne butler, and private elevator.",
        "price_per_night": 850.0,
        "capacity_per_room": 6,
        "total_rooms": 3,
        "amenities": ["360 Skyline Terrace", "Private Jacuzzi", "Dedicated 24/7 Butler", "California King Master", "Private Chauffeur Included", "Grand Piano"],
        "badge": "VIP & Presidential",
        "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80"
    }
]
