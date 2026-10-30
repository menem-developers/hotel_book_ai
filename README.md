# 🏨 Grand Azure Hotel & Suites — AI Assistant

An intelligent, conversational hotel booking assistant powered by **FastAPI**, **Ollama** (local `llama3.2:1b` model), and **MongoDB**.

---

## 🌟 Key Features

1. **Local AI Model Integration with Ollama**:
   - Uses local `llama3.2:1b` (or any model specified in `.env`) running on your Ollama server (`http://127.0.0.1:11434`).
   - Friendly, hospitable virtual **AI Concierge**.
   - Enforces **strict one-by-one conversational interaction** so users are never overwhelmed by multiple questions at once.

2. **Seeded MongoDB Rooms Database**:
   - Automatically initializes a default catalog of rooms in MongoDB (`hotel_booking` database, `rooms` collection):
     - **Deluxe Single Room** ($85/night, 1 guest)
     - **Executive Double Room** ($140/night, 2 guests)
     - **Corporate Business Suite** ($240/night, 3 guests)
     - **Luxury Family & Team Villa** ($380/night, 5 guests)
     - **Presidential Penthouse Suite** ($550/night, 4 guests)
   - Dynamic real-time room availability and inventory updates upon booking.

3. **Step-by-Step Conversational Booking Flow**:
   - **Step 1**: Welcomes guest and asks for their full name & whether they are booking as an **Individual** or for a **Company / Corporate Team**.
   - **Step 2 (If Company)**: Asks for Company / Organization name.
   - **Step 3**: Asks how many total members / guests will be staying.
   - **Step 4**: Asks how many rooms are needed (with intelligent suggestions based on group size).
   - **Step 5**: Presents available rooms from MongoDB and asks for room preference.
   - **Step 6**: Asks for Check-in date (supports flexible natural dates like *'tomorrow'*, *'Nov 1st'*, or *'2026-11-10'*).
   - **Step 7**: Asks for Check-out date (or number of nights) and automatically calculates the total price and duration.
   - **Step 8**: Asks for contact phone number or email address.
   - **Step 9**: Displays a complete itemized reservation review and asks for confirmation.
   - **Step 10**: On confirmation, stores the booking record in the MongoDB `bookings` collection and issues a unique booking reference ID (e.g. `BK-847291`).

4. **Modern Web UI**:
   - Luxury hotel aesthetic with obsidian/navy and gold accents.
   - **Real-time Status Badges**: Live indicators for MongoDB and Ollama connectivity.
   - **Live Rooms Catalog (Left Panel)**: Shows all room types, amenities, guest capacities, and current availability directly from MongoDB.
   - **Interactive Chat Concierge (Center)**: Message bubble stream, quick-reply suggestion pills, markdown formatting, and typing indicators.
   - **Reservation Progress Tracker (Right Panel)**: Step-by-step timeline and live estimated bill card.
   - **Bookings Ledger Modal**: View all finalized reservations recorded in MongoDB.

---

## 🛠️ Configuration (`.env`)

Configuration parameters are loaded directly from the project's `.env` file:

```env
# Application Settings
APP_NAME=Hotel Booking AI Assistant
PORT=8000
HOST=0.0.0.0
DEBUG=True

# MongoDB Configuration
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DB_NAME=hotel_booking

# Ollama LLM Configuration
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
```

---

## 🚀 Running the Application

To launch the FastAPI server and Web UI:

```powershell
python main.py
```
Or with Uvicorn directly:
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once started, open your browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📡 API Endpoints

- `GET /` — Serves the interactive Web UI.
- `GET /api/status` — Returns system health status (MongoDB & Ollama connectivity, active model).
- `GET /api/rooms` — Returns all room categories and available counts from MongoDB.
- `POST /api/rooms/seed` — Forces re-seeding the room types in MongoDB.
- `POST /api/chat/init` — Starts a new session or retrieves the active session with the initial welcome message.
- `POST /api/chat` — Sends a message to the AI concierge and receives the conversational response, updated booking state, and quick-reply options.
- `POST /api/chat/reset` — Clears the conversational session state to start fresh.
- `GET /api/bookings` — Lists all confirmed bookings recorded in MongoDB.
