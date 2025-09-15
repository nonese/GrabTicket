from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    energy_coins = Column(Integer, default=0)

    orders = relationship("Order", back_populates="user")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    organizer = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    sale_start_time = Column(DateTime)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    seat_map_url = Column(String, nullable=True)
    cover_image = Column(String, nullable=True)

    ticket_types = relationship("TicketType", back_populates="event")
    orders = relationship("Order", back_populates="event")


class TicketType(Base):
    __tablename__ = "ticket_types"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    price = Column(Float)
    seat_type = Column(String)
    available_qty = Column(Integer)

    event = relationship("Event", back_populates="ticket_types")
    orders = relationship("Order", back_populates="ticket_type")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    event = relationship("Event", back_populates="orders")
    ticket_type = relationship("TicketType", back_populates="orders")
