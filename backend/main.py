from datetime import timedelta, datetime
import asyncio
import os
import uuid
import shutil
import json
import io
import zipfile
from typing import Dict, Set
from xml.sax.saxutils import escape

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
from sqlalchemy.orm import Session, joinedload
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

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


_CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    '</Types>'
)

_ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/>'
    '</Relationships>'
)

_WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets>'
    '<sheet name="订单记录" sheetId="1" r:id="rId1"/>'
    '</sheets>'
    '</workbook>'
)

_WORKBOOK_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
    'Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
    'Target="styles.xml"/>'
    '</Relationships>'
)

_STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>'
)


def _column_letter(index: int) -> str:
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


def _build_sheet_xml(rows: list[list[str]]) -> str:
    max_cols = max((len(r) for r in rows), default=1)
    if rows:
        dimension = f"A1:{_column_letter(max_cols)}{len(rows)}"
    else:
        dimension = "A1:A1"
    rows_xml: list[str] = []
    for row_idx, row_values in enumerate(rows, start=1):
        cells_xml: list[str] = []
        for col_idx in range(1, max_cols + 1):
            value = row_values[col_idx - 1] if col_idx - 1 < len(row_values) else ""
            cell_ref = f"{_column_letter(col_idx)}{row_idx}"
            text = "" if value is None else escape(str(value))
            cells_xml.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{text}'
                "</t></is></c>"
            )
        rows_xml.append(f"<row r=\"{row_idx}\">{''.join(cells_xml)}</row>")
    sheet_data = "".join(rows_xml)
    if sheet_data:
        sheet_data = f"<sheetData>{sheet_data}</sheetData>"
    else:
        sheet_data = "<sheetData/>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<dimension ref=\"{dimension}\"/>"
        f"{sheet_data}"
        "</worksheet>"
    )


def _orders_to_rows(orders: list[models.Order]) -> list[list[str]]:
    rows: list[list[str]] = [["订单ID", "用户名", "活动名称", "票档", "票价", "抢票时间"]]
    for order in orders:
        username = order.user.username if order.user else ""
        event_title = order.event.title if order.event else ""
        seat_type = order.ticket_type.seat_type if order.ticket_type else ""
        price = ""
        if order.ticket_type and order.ticket_type.price is not None:
            price = f"{order.ticket_type.price:.2f}"
        created_at = (
            order.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if order.created_at
            else ""
        )
        rows.append([
            str(order.id),
            username,
            event_title,
            seat_type,
            price,
            created_at,
        ])
    return rows


def _build_orders_workbook(orders: list[models.Order]) -> io.BytesIO:
    buffer = io.BytesIO()
    sheet_xml = _build_sheet_xml(_orders_to_rows(orders))
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        archive.writestr("_rels/.rels", _ROOT_RELS_XML)
        archive.writestr("xl/workbook.xml", _WORKBOOK_XML)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS_XML)
        archive.writestr("xl/styles.xml", _STYLES_XML)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    buffer.seek(0)
    return buffer


def _ensure_admin(user: models.User) -> None:
    if user.username != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以执行该操作")


@app.on_event("startup")
async def startup_event() -> None:
    """Launch background task processing the ticket queue and seed admin."""
    asyncio.create_task(_process_queue())
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin_user = models.User(
                username="admin",
                hashed_password=auth.get_password_hash("admin"),
                energy_coins=10000,
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()


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
        event = db.query(models.Event).filter(models.Event.id == event_id).first()
        if event and datetime.utcnow() < event.sale_start_time:
            await websocket.send_json(
                {
                    "type": "grab_result",
                    "status": "fail",
                    "reason": "抢票尚未开始",
                }
            )
            return
        ticket_type = (
            db.query(models.TicketType)
            .filter(
                models.TicketType.id == ticket_type_id,
                models.TicketType.event_id == event_id,
            )
            .with_for_update()
            .first()
        )
        user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .with_for_update()
            .first()
        )
        if (
            ticket_type
            and user
            and ticket_type.available_qty > 0
            and user.energy_coins >= int(ticket_type.price)
        ):
            ticket_type.available_qty -= 1
            user.energy_coins -= int(ticket_type.price)
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
            reason = "座位已满"
            if not ticket_type or ticket_type.available_qty <= 0:
                reason = "座位已满"
            elif user is None:
                reason = "用户不存在"
            elif user.energy_coins < int(ticket_type.price):
                reason = "能量币不足"
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
                    "reason": reason,
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌"
        )
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise HTTPException(status_code=400, detail="用户不存在")
    return user


@app.post("/auth/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已被注册")
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
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return schemas.Token(access_token=access_token)


@app.get("/users/me", response_model=schemas.User)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


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
        raise HTTPException(status_code=404, detail="用户不存在")
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
        raise HTTPException(status_code=404, detail="用户不存在")
    user.hashed_password = auth.get_password_hash("123456")
    db.commit()
    db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="无法删除当前登录用户")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="无法删除默认管理员账号")
    db.query(models.Order).filter(models.Order.user_id == user_id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()


@app.get("/admin/orders", response_model=list[schemas.Order])
def admin_list_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    orders = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            joinedload(models.Order.event),
            joinedload(models.Order.ticket_type),
        )
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return orders


@app.get("/admin/orders/export")
def admin_export_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    orders = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            joinedload(models.Order.event),
            joinedload(models.Order.ticket_type),
        )
        .order_by(models.Order.created_at.desc())
        .all()
    )
    workbook = _build_orders_workbook(orders)
    filename = f"orders_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/events", response_model=list[schemas.Event])
def read_events(db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    return events


@app.post("/events", response_model=schemas.Event)
async def create_event(
    title: str = Form(...),
    organizer: str = Form(...),
    location: str = Form(...),
    sale_start_time: datetime = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime | None = Form(None),
    description: str | None = Form(None),
    image: UploadFile | None = File(None),
    seat_map: UploadFile | None = File(None),
    ticket_types: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以创建活动")
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
        sale_start_time=sale_start_time,
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
        )
        db.add(tt)
    db.commit()
    db.refresh(db_event)
    return db_event


@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    return event


@app.put("/events/{event_id}", response_model=schemas.Event)
async def update_event(
    event_id: int,
    title: str = Form(...),
    organizer: str = Form(...),
    location: str = Form(...),
    sale_start_time: datetime = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime | None = Form(None),
    description: str | None = Form(None),
    image: UploadFile | None = File(None),
    seat_map: UploadFile | None = File(None),
    ticket_types: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以更新活动")
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if image:
        os.makedirs("static", exist_ok=True)
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("static", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        event.cover_image = f"/static/{filename}"
    if seat_map:
        os.makedirs("static", exist_ok=True)
        ext = os.path.splitext(seat_map.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("static", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(seat_map.file, buffer)
        event.seat_map_url = f"/static/{filename}"
    event.title = title
    event.organizer = organizer
    event.location = location
    event.description = description
    event.sale_start_time = sale_start_time
    event.start_time = start_time
    event.end_time = end_time
    db.query(models.TicketType).filter(models.TicketType.event_id == event.id).delete()
    try:
        tts = json.loads(ticket_types)
    except Exception:
        tts = []
    for t in tts:
        tt = models.TicketType(
            event_id=event.id,
            price=t.get("price", 0),
            seat_type=t.get("seat_type", ""),
            available_qty=t.get("available_qty", 0),
        )
        db.add(tt)
    db.commit()
    db.refresh(event)
    return event


@app.post("/events/{event_id}/tickets", response_model=schemas.Order)
def grab_ticket(
    event_id: int,
    ticket_type_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if datetime.utcnow() < event.sale_start_time:
        raise HTTPException(status_code=400, detail="抢票尚未开始")
    ticket_type = (
        db.query(models.TicketType)
        .filter(
            models.TicketType.id == ticket_type_id,
            models.TicketType.event_id == event_id,
        )
        .with_for_update()
        .first()
    )
    if not ticket_type:
        raise HTTPException(status_code=404, detail="票种不存在")
    user = (
        db.query(models.User)
        .filter(models.User.id == current_user.id)
        .with_for_update()
        .first()
    )
    if ticket_type.available_qty <= 0:
        raise HTTPException(status_code=400, detail="座位已满")
    if user.energy_coins < int(ticket_type.price):
        raise HTTPException(status_code=400, detail="能量币不足")
    ticket_type.available_qty -= 1
    user.energy_coins -= int(ticket_type.price)
    order = models.Order(
        user_id=current_user.id, event_id=event_id, ticket_type_id=ticket_type_id
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/orders/me", response_model=list[schemas.Order])
def read_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    orders = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            joinedload(models.Order.event),
            joinedload(models.Order.ticket_type),
        )
        .filter(models.Order.user_id == current_user.id)
        .all()
    )
    return orders
