"""
Database Schemas for SmartRide – GCTU Smart Campus Initiative

Each Pydantic model corresponds to a MongoDB collection. The collection name
is the lowercase of the class name (e.g., Booking -> "booking").
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Core domain models

class CampusStop(BaseModel):
    """
    Shuttle stop within a campus
    Collection: "campusstop"
    """
    campus: str = Field(..., description="Campus name, e.g., Tesano, Abokobi, Main Campus")
    name: str = Field(..., description="Stop name, e.g., Library, Lecture Block A")
    code: str = Field(..., description="Short unique code for the stop")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    is_active: bool = Field(True, description="Whether the stop is active")

class Route(BaseModel):
    """
    Route connecting stops within a campus or inter-campus
    Collection: "route"
    """
    campus: str = Field(..., description="Campus this route belongs to (or 'Inter-Campus')")
    name: str = Field(..., description="Route name")
    stop_codes: List[str] = Field(..., description="Ordered list of stop codes")
    is_active: bool = Field(True, description="Whether the route is active")

class Shuttle(BaseModel):
    """
    Shuttle vehicle metadata
    Collection: "shuttle"
    """
    identifier: str = Field(..., description="Vehicle identifier")
    campus: str = Field(..., description="Assigned campus")
    route_name: Optional[str] = Field(None, description="Assigned route name")
    battery_level: Optional[int] = Field(100, ge=0, le=100, description="Battery percentage")
    latitude: Optional[float] = Field(None, description="Current latitude")
    longitude: Optional[float] = Field(None, description="Current longitude")
    status: str = Field("idle", description="idle|enroute|charging|maintenance")
    capacity: int = Field(12, ge=1, le=60, description="Total seats")
    occupancy: int = Field(0, ge=0, description="Seats currently occupied")

class Booking(BaseModel):
    """
    Ride booking made by a user
    Collection: "booking"
    """
    name: str = Field(..., description="Full name of rider")
    email: EmailStr = Field(..., description="Email of rider")
    campus: str = Field(..., description="Campus for the ride")
    pickup_code: str = Field(..., description="Pickup stop code")
    dropoff_code: str = Field(..., description="Dropoff stop code")
    scheduled_time: Optional[datetime] = Field(None, description="Planned pickup time; None means ASAP")
    status: str = Field("confirmed", description="confirmed|completed|canceled")
    eta_minutes: Optional[int] = Field(None, ge=0, le=120, description="Estimated minutes until pickup")
    seats: int = Field(1, ge=1, le=6, description="Seats requested")
    qr_token: Optional[str] = Field(None, description="Signed token for boarding QR")

# Example user model if needed elsewhere
class User(BaseModel):
    name: str
    email: EmailStr
    role: str = Field("student", description="student|staff|admin")
    is_active: bool = True
