from datetime import timedelta, datetime
import asyncio
import os
import uuid
import shutil
import json
from typing import Dict, Set

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

from . import auth, models, schemas
from .database import Base, engine, get_db, SessionLocal

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GrabTicket API")
app.mount("/static", StaticFiles(directory="static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Store active WebSocket connections per event
event_connections: Dict[int, Set[WebSocket]] = {}

# Queue to ensure sequential ticket processing
ticket_queue: asyncio.Queue = asyncio.Queue()


@app.on_event("startup")
async def startup_event() -> None:
    """Launch background task processing the ticket queue."""
    asyncio.create_task(_process_queue())


async def _process_queue() -> None:
    while True:
        request = await ticket_queue.get()
        try:
            await _handle_grab_request(request)
        finally:
            ticket_queue.task_done()


async def _handle_grab_request(request: dict) -> None:
    event_id = request["event_id"]
    ticket_type_id = request["ticket_type_id"]
    websocket: WebSocket = request["websocket"]
    user_id = request["user_id"]
    db = SessionLocal()
    try:
        ticket_type = (
            db.query(models.TicketType)
            .filter(
                models.TicketType.id == ticket_type_id,
                models.TicketType.event_id == event_id,
            )
            .with_for_update()
            .first()
        )
        if ticket_type and ticket_type.available_qty > 0:
            ticket_type.available_qty -= 1
            order = models.Order(
                user_id=user_id, event_id=event_id, ticket_type_id=ticket_type_id
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            await websocket.send_json(
                {"type": "grab_result", "status": "success", "order_id": order.id}
            )
        else:
            alternatives = (
                db.query(models.TicketType)
                .filter(
                    models.TicketType.event_id == event_id,
                    models.TicketType.available_qty > 0,
                )
                .all()
            )
            alt_list = [
                {
                    "ticket_type_id": t.id,
                    "seat_type": t.seat_type,
                    "available_qty": t.available_qty,
                }
                for t in alternatives
                if t.id != ticket_type_id
            ]
            await websocket.send_json(
                {
                    "type": "grab_result",
                    "status": "fail",
                    "reason": "Tickets sold out",
                    "alternatives": alt_list,
                }
            )
        await _broadcast_seat_counts(event_id, db)
    finally:
        db.close()


async def _broadcast_seat_counts(event_id: int, db: Session | None = None) -> None:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        ticket_types = (
            db.query(models.TicketType)
            .filter(models.TicketType.event_id == event_id)
            .all()
        )
        data = {
            "type": "seat_counts",
            "tickets": [
                {
                    "ticket_type_id": t.id,
                    "seat_type": t.seat_type,
                    "available_qty": t.available_qty,
                }
                for t in ticket_types
            ],
        }
        for conn in list(event_connections.get(event_id, set())):
            try:
                await conn.send_json(data)
            except Exception:
                event_connections[event_id].discard(conn)
    finally:
        if close_db:
            db.close()


def _get_user_by_token(token: str, db: Session) -> models.User | None:
    token_data = auth.decode_access_token(token)
    if token_data is None or token_data.username is None:
        return None
    return (
        db.query(models.User)
        .filter(models.User.username == token_data.username)
        .first()
    )


@app.websocket("/ws/events/{event_id}")
async def event_ws(websocket: WebSocket, event_id: int, token: str) -> None:
    await websocket.accept()
    db = SessionLocal()
    user = _get_user_by_token(token, db)
    if user is None:
        await websocket.close(code=1008)
        db.close()
        return

    connections = event_connections.setdefault(event_id, set())
    connections.add(websocket)

    try:
        await _broadcast_seat_counts(event_id, db)
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "grab":
                ticket_type_id = data.get("ticket_type_id")
                if ticket_type_id is not None:
                    await ticket_queue.put(
                        {
                            "websocket": websocket,
                            "user_id": user.id,
                            "event_id": event_id,
                            "ticket_type_id": int(ticket_type_id),
                        }
                    )
    except WebSocketDisconnect:
        pass
    finally:
        connections.remove(websocket)
        db.close()


# Dependency
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = auth.decode_access_token(token)
    if token_data is None or token_data.username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")
    return user


@app.post("/auth/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        energy_coins=user.energy_coins,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return schemas.Token(access_token=access_token)


@app.get("/admin/users", response_model=list[schemas.User])
def admin_list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    users = db.query(models.User).all()
    return users


@app.put("/admin/users/{user_id}/coins", response_model=schemas.User)
def admin_update_coins(
    user_id: int,
    data: schemas.UserUpdateCoins,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.energy_coins = data.energy_coins
    db.commit()
    db.refresh(user)
    return user


@app.post("/admin/users/{user_id}/reset_password", response_model=schemas.User)
def admin_reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = auth.get_password_hash("123456")
    db.commit()
    db.refresh(user)
    return user


@app.get("/events", response_model=list[schemas.Event])
def read_events(db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    return events


@app.post("/events", response_model=schemas.Event)
async def create_event(
    title: str = Form(...),
    organizer: str = Form(...),
    location: str = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    description: str | None = Form(None),
    image: UploadFile | None = File(None),
    seat_map: UploadFile | None = File(None),
    ticket_types: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    image_path = None
    seat_map_path = None
    if image:
        os.makedirs("static", exist_ok=True)
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("static", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = f"/static/{filename}"
    if seat_map:
        os.makedirs("static", exist_ok=True)
        ext = os.path.splitext(seat_map.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("static", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(seat_map.file, buffer)
        seat_map_path = f"/static/{filename}"

    db_event = models.Event(
        title=title,
        organizer=organizer,
        location=location,
        description=description,
        start_time=start_time,
        end_time=end_time,
        cover_image=image_path,
        seat_map_url=seat_map_path,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    try:
        tts = json.loads(ticket_types)
    except Exception:
        tts = []
    for t in tts:
        tt = models.TicketType(
            event_id=db_event.id,
            price=t.get("price", 0),
            seat_type=t.get("seat_type", ""),
            available_qty=t.get("available_qty", 0),
            pos_x=t.get("pos_x", 0),
            pos_y=t.get("pos_y", 0),
        )
        db.add(tt)
    db.commit()
    db.refresh(db_event)
    return db_event


@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.post("/events/{event_id}/tickets", response_model=schemas.Order)
def grab_ticket(event_id: int, ticket_type_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    ticket_type = db.query(models.TicketType).filter(models.TicketType.id == ticket_type_id, models.TicketType.event_id == event_id).with_for_update().first()
    if not ticket_type:
        raise HTTPException(status_code=404, detail="Ticket type not found")
    if ticket_type.available_qty <= 0:
        raise HTTPException(status_code=400, detail="Tickets sold out")
    ticket_type.available_qty -= 1
    order = models.Order(user_id=current_user.id, event_id=event_id, ticket_type_id=ticket_type_id)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
