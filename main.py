import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Query, File, UploadFile, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from config import settings
from database import db_manager
from ollama_client import ollama_client
from booking_agent import booking_agent, STEP_START, STEP_ASK_LOCATION
import voice_service
from models import (
    ChatRequest, ChatResponse, ResetRequest,
    LocationModel, HotelModel, RoomModel, RoomCountUpdateRequest, AvailabilityCheckRequest,
    VoiceChatResponse, TTSRequest
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("hotel_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Hotel Booking Application & Database...")
    try:
        counts = db_manager.seed_database(force=False)
        logger.info(f"MongoDB seeded successfully: {counts['locations']} locations, {counts['hotels']} hotels, {counts['rooms']} room records.")
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")

    # Check Ollama connection
    ollama_ready = await ollama_client.is_available()
    if ollama_ready:
        logger.info(f"Ollama server connected with model '{settings.OLLAMA_MODEL}'.")
    else:
        logger.warning(f"Ollama server or model '{settings.OLLAMA_MODEL}' not reached. Fallback conversational mode active.")

    yield
    logger.info("Hotel Booking Application shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index HTML not found")
    return FileResponse(index_file)

@app.get("/admin", response_class=FileResponse)
async def serve_admin():
    admin_file = STATIC_DIR / "admin.html"
    if not admin_file.exists():
        # Fallback to index if admin.html not yet present
        index_file = STATIC_DIR / "index.html"
        return FileResponse(index_file)
    return FileResponse(admin_file)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Simple ping endpoint for Docker and load balancer health checks."""
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/api/status")
async def get_system_status():
    """Return live system health (MongoDB, Ollama, model, catalog)."""
    mongo_ok = db_manager.is_connected
    ollama_ok = await ollama_client.is_available()
    rooms_count = 0
    locations_count = 0
    hotels_count = 0
    if mongo_ok:
        try:
            rooms_count = len(db_manager.get_all_rooms())
            locations_count = len(db_manager.get_all_locations())
            hotels_count = len(db_manager.get_all_hotels())
        except Exception:
            pass

    return {
        "status": "healthy" if (mongo_ok and ollama_ok) else "degraded",
        "app_name": settings.APP_NAME,
        "database": {
            "connected": mongo_ok,
            "database_name": settings.MONGODB_DB_NAME,
            "locations_count": locations_count,
            "hotels_count": hotels_count,
            "rooms_count": rooms_count
        },
        "ollama": {
            "connected": ollama_ok,
            "host": settings.OLLAMA_HOST,
            "model": settings.OLLAMA_MODEL
        }
    }

# ==============================================================
# CHAT ENDPOINTS
# ==============================================================
@app.post("/api/chat/init")
async def initialize_chat(request: ResetRequest):
    """Start or retrieve chat session. Fresh session starts completely empty until user initiates."""
    session = booking_agent.get_or_create_session(request.session_id)
    
    # If session is fresh and has no messages, leave empty!
    if not session.get("messages"):
        return {
            "session_id": session["session_id"],
            "reply": "",
            "current_step": session.get("current_step", STEP_START),
            "state": session,
            "quick_replies": [],
            "options": None
        }

    last_msg = session["messages"][-1]
    welcome_text = last_msg.get("content", "")
    current_st = session.get("current_step", STEP_START)
    options = None
    if current_st == STEP_ASK_LOCATION:
        options = {"type": "locations", "items": db_manager.get_all_locations()}
    elif current_st == "ASK_HOTEL":
        options = {"type": "hotels", "items": db_manager.get_all_hotels(location_id=session.get("location_id"))}
    elif current_st == "ASK_ROOM_TYPE":
        options = {
            "type": "rooms",
            "hotel_name": session.get("hotel_name"),
            "items": db_manager.get_all_rooms(hotel_id=session.get("hotel_id"))
        }

    qr_list = []
    if current_st == STEP_ASK_LOCATION:
        qr_list = booking_agent.get_location_quick_replies()
    elif current_st == "ASK_ROOM_TYPE":
        qr_list = booking_agent.get_room_quick_replies(session.get("hotel_id"))

    return {
        "session_id": session["session_id"],
        "reply": welcome_text,
        "current_step": current_st,
        "state": session,
        "quick_replies": qr_list,
        "options": options
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    """Process user message through conversational booking agent and include TTS audio."""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await booking_agent.process_user_message(req.session_id, req.message)
    # Generate TTS audio for the reply so frontend can speak at the same time
    try:
        reply_text = result.get("reply", "")
        result["audio_base64"] = await voice_service.generate_tts_data_uri_async(reply_text)
    except Exception as e:
        logger.warning(f"Failed to generate TTS audio in /api/chat: {e}")
        result["audio_base64"] = None
    return ChatResponse(**result)

# ==============================================================
# VOICE SPEECH-TO-TEXT (WHISPER) & TEXT-TO-SPEECH (TTS) ENDPOINTS
# ==============================================================
@app.post("/api/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcribe user-recorded voice audio using Whisper 'tiny' CPU model."""
    try:
        content = await audio.read()
        filename = audio.filename or "recording.webm"
        ext = filename.split(".")[-1] if "." in filename else "webm"
        logger.info(f"[/api/voice/transcribe] Received {len(content)} bytes, filename={filename}")
        text = voice_service.transcribe_audio_bytes(content, file_ext=ext)
        return {"success": True, "text": text}
    except Exception as e:
        logger.error(f"Voice transcription endpoint error: {e}", exc_info=True)
        return {"success": False, "text": "", "error": str(e)}

@app.post("/api/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    1. Transcribe voice input using Whisper 'tiny' CPU model.
    2. Process transcribed message through booking agent.
    3. Generate TTS audio for the reply so frontend speaks immediately.
    """
    try:
        content = await audio.read()
        filename = audio.filename or "recording.webm"
        ext = filename.split(".")[-1] if "." in filename else "webm"
        logger.info(f"[/api/voice/chat] Received audio upload: {len(content)} bytes, filename={filename}")
        user_text = voice_service.transcribe_audio_bytes(content, file_ext=ext)

        if not user_text:
            logger.warning(f"[/api/voice/chat] No speech detected in {len(content)} bytes audio")
            return VoiceChatResponse(
                success=False,
                message="No clear speech detected. Please speak into your microphone and try again.",
                session_id=session_id or ""
            )

        # Process through booking conversational agent
        result = await booking_agent.process_user_message(session_id, user_text)

        # Generate TTS audio for the reply text
        reply_text = result.get("reply", "")
        audio_base64 = await voice_service.generate_tts_data_uri_async(reply_text)

        return VoiceChatResponse(
            success=True,
            user_text=user_text,
            reply=reply_text,
            session_id=result.get("session_id", ""),
            current_step=result.get("current_step", ""),
            state=result.get("state", {}),
            quick_replies=result.get("quick_replies", []),
            booking=result.get("booking"),
            options=result.get("options"),
            audio_base64=audio_base64
        )
    except Exception as e:
        logger.error(f"Voice chat endpoint error: {e}", exc_info=True)
        return VoiceChatResponse(
            success=False,
            message=f"Error processing voice: {e}",
            session_id=session_id or ""
        )

@app.post("/api/voice/tts")
async def tts_endpoint_post(req: TTSRequest):
    """Generate and return MP3 audio for any given text."""
    try:
        audio_bytes = await voice_service.generate_tts_audio_bytes_async(req.text)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to synthesize speech audio")
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice/tts")
async def tts_endpoint_get(text: str = Query(..., description="Text to synthesize to speech")):
    """GET endpoint to play or stream MP3 speech directly."""
    try:
        audio_bytes = await voice_service.generate_tts_audio_bytes_async(text)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to synthesize speech audio")
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/reset")
async def reset_chat(req: ResetRequest):
    """Reset session and start fresh with empty canvas."""
    session_id = req.session_id
    if not session_id:
        session = booking_agent.get_or_create_session()
        session_id = session["session_id"]
    else:
        session = booking_agent.reset_session(session_id)

    return {
        "session_id": session_id,
        "reply": "",
        "current_step": STEP_START,
        "state": session,
        "quick_replies": [],
        "options": None
    }

    welcome_text = (
        "Welcome to **Northstar Airline Assistance**! 🌟\n\n"
        "Let's start fresh. Since you are arriving from the airport, **which city or airport destination are you traveling to?**"
    )
    session.setdefault("messages", []).append({
        "role": "assistant",
        "content": welcome_text,
        "timestamp": ""
    })
    session["current_step"] = STEP_ASK_LOCATION
    db_manager.save_session(session_id, session)

    return {
        "session_id": session_id,
        "reply": welcome_text,
        "current_step": STEP_ASK_LOCATION,
        "state": session,
        "quick_replies": booking_agent.get_location_quick_replies()
    }

# ==============================================================
# BOOKINGS ENDPOINTS
# ==============================================================
@app.get("/api/bookings")
async def list_bookings():
    """Retrieve all confirmed hotel bookings stored in MongoDB."""
    try:
        bookings = db_manager.get_all_bookings()
        return {"success": True, "count": len(bookings), "bookings": bookings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bookings/search")
async def search_booking(query: str):
    """Search for a specific booking by Reference ID, Guest Name, or Email."""
    try:
        booking = db_manager.find_booking_by_query(query)
        if booking:
            return {"success": True, "booking": booking}
        return {"success": False, "message": "No reservation found matching your query."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bookings/{booking_id}")
async def delete_booking_endpoint(booking_id: str):
    """Delete a confirmed reservation by booking ID."""
    try:
        deleted = db_manager.delete_booking(booking_id)
        if deleted:
            return {"success": True, "message": f"Reservation {booking_id} deleted successfully from MongoDB."}
        return {"success": False, "message": f"Reservation {booking_id} not found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================
# CONTROL PANEL & ADMIN API (Locations, Hotels, Rooms, Inventory)
# ==============================================================
@app.get("/api/locations")
async def get_locations():
    """List all airport destination locations."""
    return {"success": True, "locations": db_manager.get_all_locations()}

@app.post("/api/locations")
async def add_location(loc: LocationModel):
    """Control Panel: Add a new airport location."""
    try:
        loc_id = db_manager.add_location(loc.model_dump())
        return {"success": True, "location_id": loc_id, "message": f"Location {loc.city} added successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/locations/{location_id}")
async def delete_location(location_id: str):
    """Control Panel: Delete an airport location."""
    deleted = db_manager.delete_location(location_id)
    return {"success": deleted, "message": f"Location {location_id} deleted."}

@app.get("/api/hotels")
async def get_hotels(location_id: Optional[str] = None):
    """List all luxury hotels, optionally filtered by location_id."""
    return {"success": True, "hotels": db_manager.get_all_hotels(location_id=location_id)}

@app.post("/api/hotels")
async def add_hotel(hotel: HotelModel):
    """Control Panel: Add a new hotel under a location."""
    try:
        hotel_id = db_manager.add_hotel(hotel.model_dump())
        return {"success": True, "hotel_id": hotel_id, "message": f"Hotel '{hotel.name}' added successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hotels/{hotel_id}")
async def delete_hotel(hotel_id: str):
    """Control Panel: Delete a hotel."""
    deleted = db_manager.delete_hotel(hotel_id)
    return {"success": deleted, "message": f"Hotel {hotel_id} deleted."}

@app.get("/api/rooms")
async def get_rooms(hotel_id: Optional[str] = None):
    """Fetch rooms catalog and current availability for a hotel."""
    try:
        rooms = db_manager.get_all_rooms(hotel_id=hotel_id)
        return {"success": True, "rooms": rooms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rooms")
async def add_room(room: RoomModel):
    """Control Panel: Add or update room type."""
    try:
        room_id = db_manager.add_or_update_room(room.model_dump())
        return {"success": True, "room_id": room_id, "message": f"Room '{room.name}' saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rooms/update-count")
async def update_room_count(req: RoomCountUpdateRequest):
    """Control Panel: Adjust total room inventory count for a room."""
    try:
        updated = db_manager.update_room_count(req.room_id, req.new_count, hotel_id=req.hotel_id)
        return {"success": updated, "message": f"Room {req.room_id} count updated to {req.new_count}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rooms/{room_id}")
async def delete_room(room_id: str, hotel_id: Optional[str] = None):
    """Control Panel: Delete a room type."""
    deleted = db_manager.delete_room(room_id, hotel_id=hotel_id)
    return {"success": deleted, "message": f"Room {room_id} deleted."}

@app.post("/api/rooms/check-availability")
async def check_availability_endpoint(req: AvailabilityCheckRequest):
    """Control Panel & API: Check if room inventory is available for given date range."""
    try:
        is_avail, remaining, msg = db_manager.check_room_availability_for_dates(
            hotel_id=req.hotel_id,
            room_id=req.room_id,
            checkin_date=req.checkin_date,
            checkout_date=req.checkout_date,
            requested_count=req.requested_count
        )
        return {
            "success": True,
            "is_available": is_avail,
            "remaining_rooms": remaining,
            "message": msg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_admin_stats():
    """Return summary statistics for Control Panel Dashboard."""
    try:
        locs = db_manager.get_all_locations()
        hotels = db_manager.get_all_hotels()
        rooms = db_manager.get_all_rooms()
        bookings = db_manager.get_all_bookings()
        total_rev = sum(float(b.get("total_amount", 0)) for b in bookings if b.get("status") == "confirmed")
        pickup_count = sum(1 for b in bookings if b.get("airport_pickup"))
        drop_count = sum(1 for b in bookings if b.get("airport_drop"))

        return {
            "success": True,
            "stats": {
                "locations_count": len(locs),
                "hotels_count": len(hotels),
                "rooms_count": len(rooms),
                "bookings_count": len(bookings),
                "total_revenue": round(total_rev, 2),
                "airport_pickups": pickup_count,
                "airport_drops": drop_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rooms/seed")
async def seed_database_endpoint():
    """Force re-seed default locations, hotels, and rooms."""
    try:
        counts = db_manager.seed_database(force=True, clear_bookings=True)
        return {"success": True, "message": "Database seeded successfully with USA locations and hotels.", "counts": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
