import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents

app = FastAPI(title="SmartRide – GCTU Smart Campus Shuttle API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class BookingIn(BaseModel):
    name: str
    email: EmailStr
    campus: str
    pickup_code: str
    dropoff_code: str
    scheduled_time: Optional[datetime] = None

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

# ---------- Seed data endpoints ----------
@app.post("/stops")
def create_stop(stop: StopIn):
    stop_id = create_document("campusstop", stop.model_dump())
    return {"id": stop_id}

@app.get("/stops")
def list_stops(campus: Optional[str] = None):
    filt = {"campus": campus} if campus else {}
    docs = get_documents("campusstop", filt)
    return docs

@app.post("/routes")
def create_route(route: RouteIn):
    route_id = create_document("route", route.model_dump())
    return {"id": route_id}

@app.get("/routes")
def list_routes(campus: Optional[str] = None):
    filt = {"campus": campus} if campus else {}
    return get_documents("route", filt)

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

# ---------- Booking ----------
@app.post("/bookings")
def create_booking(booking: BookingIn):
    # Simple validation: ensure pickup != dropoff
    if booking.pickup_code == booking.dropoff_code:
        raise HTTPException(status_code=400, detail="Pickup and dropoff cannot be the same stop")

    # Optional: estimate ETA as placeholder (would use routing service/real-time positions)
    eta = 10
    data = booking.model_dump()
    data.update({"status": "confirmed", "eta_minutes": eta})

    booking_id = create_document("booking", data)
    return {"id": booking_id, "eta_minutes": eta, "status": "confirmed"}

@app.get("/bookings")
def list_bookings(email: Optional[EmailStr] = None, campus: Optional[str] = None):
    filt = {}
    if email:
        filt["email"] = str(email)
    if campus:
        filt["campus"] = campus
    return get_documents("booking", filt)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
