import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import hmac
import hashlib
import base64
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="SmartRide – GCTU Smart Campus Shuttle API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET = os.getenv("SMART_RIDE_SECRET", "smartride-dev-secret")

# ---------- Request/Response Models ----------
class StopIn(BaseModel):
    campus: str
    name: str
    code: str
    latitude: float
    longitude: float
    is_active: bool = True

class RouteIn(BaseModel):
    campus: str
    name: str
    stop_codes: List[str]
    is_active: bool = True

class ShuttleIn(BaseModel):
    identifier: str
    campus: str
    route_name: Optional[str] = None
    battery_level: Optional[int] = 100
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str = "idle"
    capacity: int = 12
    occupancy: int = 0

class BookingIn(BaseModel):
    name: str
    email: EmailStr
    campus: str
    pickup_code: str
    dropoff_code: str
    scheduled_time: Optional[datetime] = None
    seats: int = 1

# ---------- Utils ----------

def sign_qr(payload: str) -> str:
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return token

# ---------- Health & Schema ----------
@app.get("/")
def read_root():
    return {"message": "SmartRide API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                response["collections"] = db.list_collection_names()[:10]
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "❌ Not Available"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

@app.get("/schema")
def get_schema():
    # Expose schemas content for viewer
    try:
        from schemas import CampusStop, Route, Shuttle, Booking, User
        return {
            "collections": [
                "campusstop",
                "route",
                "shuttle",
                "booking",
                "user"
            ],
            "models": {
                "CampusStop": CampusStop.model_json_schema(),
                "Route": Route.model_json_schema(),
                "Shuttle": Shuttle.model_json_schema(),
                "Booking": Booking.model_json_schema(),
                "User": User.model_json_schema(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Seed data endpoint ----------
@app.post("/seed/default")
def seed_default():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    campuses = ["Tesano", "Abokobi", "Main Campus"]
    # Stops per campus (example set)
    default_stops = {
        "Tesano": [
            ("Library", "TES-LIB", 5.6152, -0.2323),
            ("Lecture Block A", "TES-LBA", 5.6160, -0.2330),
            ("Admin Block", "TES-ADM", 5.6145, -0.2318),
            ("Hostel Gate", "TES-HOS", 5.6138, -0.2329),
        ],
        "Abokobi": [
            ("Main Gate", "ABK-GAT", 5.6810, -0.1645),
            ("Lab Complex", "ABK-LAB", 5.6818, -0.1652),
            ("Library", "ABK-LIB", 5.6805, -0.1655),
            ("Hostel", "ABK-HOS", 5.6798, -0.1649),
        ],
        "Main Campus": [
            ("Central Hall", "MAIN-HAL", 5.6201, -0.2055),
            ("Science Block", "MAIN-SCI", 5.6207, -0.2063),
            ("ICT Centre", "MAIN-ICT", 5.6194, -0.2058),
            ("Sports Complex", "MAIN-SPT", 5.6211, -0.2049),
        ],
    }

    # Create stops if not exists
    for campus in campuses:
        for name, code, lat, lng in default_stops[campus]:
            if not db["campusstop"].find_one({"code": code}):
                create_document("campusstop", {
                    "campus": campus,
                    "name": name,
                    "code": code,
                    "latitude": lat,
                    "longitude": lng,
                    "is_active": True
                })

    # Routes (one per campus, simple loop)
    default_routes = [
        ("Tesano", "Tesano Loop", ["TES-LIB", "TES-LBA", "TES-ADM", "TES-HOS", "TES-LIB"]),
        ("Abokobi", "Abokobi Loop", ["ABK-GAT", "ABK-LAB", "ABK-LIB", "ABK-HOS", "ABK-GAT"]),
        ("Main Campus", "Main Campus Loop", ["MAIN-HAL", "MAIN-SCI", "MAIN-ICT", "MAIN-SPT", "MAIN-HAL"]),
    ]
    for campus, name, codes in default_routes:
        if not db["route"].find_one({"campus": campus, "name": name}):
            create_document("route", {
                "campus": campus,
                "name": name,
                "stop_codes": codes,
                "is_active": True
            })

    # Shuttles (2 per campus)
    default_shuttles = [
        ("SR-TES-01", "Tesano", "Tesano Loop", 5.6155, -0.2327),
        ("SR-TES-02", "Tesano", "Tesano Loop", 5.6162, -0.2329),
        ("SR-ABK-01", "Abokobi", "Abokobi Loop", 5.6812, -0.1650),
        ("SR-ABK-02", "Abokobi", "Abokobi Loop", 5.6809, -0.1647),
        ("SR-MAIN-01", "Main Campus", "Main Campus Loop", 5.6204, -0.2059),
        ("SR-MAIN-02", "Main Campus", "Main Campus Loop", 5.6209, -0.2052),
    ]
    for ident, campus, route_name, lat, lng in default_shuttles:
        if not db["shuttle"].find_one({"identifier": ident}):
            create_document("shuttle", {
                "identifier": ident,
                "campus": campus,
                "route_name": route_name,
                "battery_level": 100,
                "latitude": lat,
                "longitude": lng,
                "status": "idle",
                "capacity": 12,
                "occupancy": 0
            })

    return {"status": "ok", "message": "Seeded default campuses, stops, routes, and shuttles"}

# ---------- Stops ----------
@app.post("/stops")
def create_stop(stop: StopIn):
    stop_id = create_document("campusstop", stop.model_dump())
    return {"id": stop_id}

@app.get("/stops")
def list_stops(campus: Optional[str] = None):
    filt = {"campus": campus} if campus else {}
    docs = get_documents("campusstop", filt)
    return docs

# ---------- Routes ----------
@app.post("/routes")
def create_route(route: RouteIn):
    route_id = create_document("route", route.model_dump())
    return {"id": route_id}

@app.get("/routes")
def list_routes(campus: Optional[str] = None):
    filt = {"campus": campus} if campus else {}
    return get_documents("route", filt)

# ---------- Shuttles ----------
@app.post("/shuttles")
def register_shuttle(shuttle: ShuttleIn):
    shuttle_id = create_document("shuttle", shuttle.model_dump())
    return {"id": shuttle_id}

@app.get("/shuttles")
def list_shuttles(campus: Optional[str] = None, status: Optional[str] = None):
    filt = {}
    if campus:
        filt["campus"] = campus
    if status:
        filt["status"] = status
    return get_documents("shuttle", filt)

# ---------- Telemetry (simple simulator) ----------
@app.post("/simulate/telemetry")
def simulate_telemetry(campus: Optional[str] = None):
    """Nudges shuttle positions slightly to simulate movement."""
    import random
    filt = {"campus": campus} if campus else {}
    shuttles = db["shuttle"].find(filt)
    count = 0
    for s in shuttles:
        lat = s.get("latitude") or 0
        lng = s.get("longitude") or 0
        lat += random.uniform(-0.0005, 0.0005)
        lng += random.uniform(-0.0005, 0.0005)
        db["shuttle"].update_one({"_id": s["_id"]}, {"$set": {"latitude": lat, "longitude": lng, "updated_at": datetime.utcnow()}})
        count += 1
    return {"updated": count}

# ---------- Booking ----------
@app.post("/bookings")
def create_booking(booking: BookingIn):
    # Simple validation: ensure pickup != dropoff
    if booking.pickup_code == booking.dropoff_code:
        raise HTTPException(status_code=400, detail="Pickup and dropoff cannot be the same stop")

    # capacity check: find an available shuttle in campus
    shuttle = db["shuttle"].find_one({"campus": booking.campus, "status": {"$in": ["idle", "enroute"]}})
    if not shuttle:
        raise HTTPException(status_code=409, detail="No shuttle available right now")

    capacity = shuttle.get("capacity", 12)
    occupancy = shuttle.get("occupancy", 0)
    if occupancy + booking.seats > capacity:
        raise HTTPException(status_code=409, detail="Not enough seats available on the shuttle")

    # reserve seats
    db["shuttle"].update_one({"_id": shuttle["_id"]}, {"$inc": {"occupancy": booking.seats}, "$set": {"status": "enroute", "updated_at": datetime.utcnow()}})

    # ETA placeholder
    eta = 10

    # QR token
    payload = f"{shuttle['identifier']}|{booking.email}|{datetime.utcnow().isoformat()}"
    qr_token = sign_qr(payload)

    data = booking.model_dump()
    data.update({
        "status": "confirmed",
        "eta_minutes": eta,
        "assigned_shuttle_id": str(shuttle["_id"]),
        "assigned_shuttle_identifier": shuttle["identifier"],
        "qr_token": qr_token,
    })

    booking_id = create_document("booking", data)
    return {
        "id": booking_id,
        "eta_minutes": eta,
        "status": "confirmed",
        "qr_token": qr_token,
        "assigned_shuttle": shuttle["identifier"],
    }

@app.get("/bookings")
def list_bookings(email: Optional[EmailStr] = None, campus: Optional[str] = None):
    filt = {}
    if email:
        filt["email"] = str(email)
    if campus:
        filt["campus"] = campus
    return get_documents("booking", filt)

@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str):
    b = db["booking"].find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.get("status") == "canceled":
        return {"status": "already_canceled"}

    scheduled = b.get("scheduled_time")
    if scheduled:
        # Allow cancellation until 5 minutes before scheduled time
        if datetime.utcnow() > scheduled - timedelta(minutes=5):
            raise HTTPException(status_code=400, detail="Cancellation window has passed")

    # Free seats
    seats = int(b.get("seats", 1))
    shuttle_id = b.get("assigned_shuttle_id")
    if shuttle_id:
        try:
            db["shuttle"].update_one({"_id": ObjectId(shuttle_id)}, {"$inc": {"occupancy": -seats}})
        except Exception:
            pass

    db["booking"].update_one({"_id": b["_id"]}, {"$set": {"status": "canceled", "updated_at": datetime.utcnow()}})
    return {"status": "canceled"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
