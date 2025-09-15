from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    energy_coins: int = 0


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserUpdateCoins(BaseModel):
    energy_coins: int


class TicketTypeBase(BaseModel):
    price: float
    seat_type: str
    available_qty: int


class TicketType(TicketTypeBase):
    id: int

    class Config:
        orm_mode = True


class EventBase(BaseModel):
    title: str
    organizer: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    sale_start_time: datetime
    start_time: datetime
    end_time: datetime
    seat_map_url: Optional[str] = None
    cover_image: Optional[str] = None


class Event(EventBase):
    id: int
    ticket_types: List[TicketType] = []

    class Config:
        orm_mode = True


class Order(BaseModel):
    id: int
    ticket_type: TicketType
    created_at: datetime

    class Config:
        orm_mode = True
