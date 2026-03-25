import os
import json
from datetime import datetime, timedelta, timezone
from urllib import error as urllib_error
from urllib import request as urllib_request
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, joinedload

from database import Base, engine, get_db
from models import (
    AuditLogModel,
    CartItemModel,
    FlowerModel,
    OrderItemModel,
    OrderModel,
    OrderStatus,
    UserModel,
    UserRole,
)
from prompts import (
    CRITERIA_EXTRACTION_SYSTEM_PROMPT,
    RECOMMENDATION_SYSTEM_PROMPT,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

BOOTSTRAP_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_REPLY_MODEL = os.getenv("OLLAMA_REPLY_MODEL", OLLAMA_MODEL)
OLLAMA_EXTRACTION_MODEL = os.getenv("OLLAMA_EXTRACTION_MODEL", OLLAMA_REPLY_MODEL)
OLLAMA_EXTRACT_WITH_LLM = os.getenv("OLLAMA_EXTRACT_WITH_LLM", "false").lower() == "true"
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

# bcrypt currently has compatibility issues on some Python builds (e.g. 3.14 on Windows),
# so we use a widely supported scheme that doesn't require the bcrypt wheel.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)

DEFAULT_FLOWERS_FILE = Path(__file__).resolve().parent.parent / "front" / "src" / "product.json"


def _ensure_schema() -> None:
    if engine is None:
        return

    inspector = inspect(engine)
    with engine.begin() as conn:
        bouquet_columns = {column["name"] for column in inspector.get_columns("bouquets")}
        if "description" not in bouquet_columns:
            conn.execute(text("ALTER TABLE bouquets ADD COLUMN description TEXT NOT NULL DEFAULT ''"))
        if "category" not in bouquet_columns:
            conn.execute(
                text("ALTER TABLE bouquets ADD COLUMN category VARCHAR(255) NOT NULL DEFAULT 'Другое'")
            )

        order_columns = {column["name"] for column in inspector.get_columns("app_orders")}
        if "delivery_address" not in order_columns:
            conn.execute(
                text("ALTER TABLE app_orders ADD COLUMN delivery_address TEXT NOT NULL DEFAULT ''")
            )
        if "payment_method" not in order_columns:
            conn.execute(
                text("ALTER TABLE app_orders ADD COLUMN payment_method VARCHAR(255) NOT NULL DEFAULT ''")
            )


def _seed_flowers(db: Session) -> None:
    if db.query(FlowerModel).first() is not None or not DEFAULT_FLOWERS_FILE.exists():
        return

    with DEFAULT_FLOWERS_FILE.open("r", encoding="utf-8") as file:
        raw_items = json.load(file)

    seen_names: set[str] = set()
    for item in raw_items:
        name = str(item.get("title", "")).strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        db.add(
            FlowerModel(
                name=name,
                description=str(item.get("description", "")).strip(),
                category=str(item.get("category", "Другое")).strip() or "Другое",
                price=float(item.get("price", 0)),
                image_url=str(item.get("image", "")).strip(),
            )
        )
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)
    _ensure_schema()

    # Ensure at least one admin exists (dev-friendly bootstrap).
    from database import SessionLocal

    if SessionLocal is None:
        return
    db = SessionLocal()
    try:
        admin = db.query(UserModel).filter(UserModel.username == BOOTSTRAP_ADMIN_USERNAME).one_or_none()
        if admin is None:
            db.add(
                UserModel(
                    username=BOOTSTRAP_ADMIN_USERNAME,
                    password_hash=pwd_context.hash(BOOTSTRAP_ADMIN_PASSWORD),
                    role=UserRole.admin,
                )
            )
        else:
            if not pwd_context.verify(BOOTSTRAP_ADMIN_PASSWORD, admin.password_hash):
                admin.password_hash = pwd_context.hash(BOOTSTRAP_ADMIN_PASSWORD)
            admin.role = UserRole.admin
        db.commit()
        _seed_flowers(db)
    finally:
        db.close()


def _create_access_token(*, sub: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserModel:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserModel).filter(UserModel.username == username).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(user: UserModel = Depends(get_current_user)) -> UserModel:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def _audit(
    *,
    db: Session,
    actor: UserModel,
    action: str,
    entity: str,
    entity_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
    meta: dict | None = None,
) -> None:
    row = AuditLogModel(
        actor_user_id=actor.id,
        actor_username=actor.username,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=jsonable_encoder(before) if before is not None else None,
        after=jsonable_encoder(after) if after is not None else None,
        meta=jsonable_encoder(meta) if meta is not None else None,
    )
    db.add(row)
    db.commit()


class FlowerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="Другое", min_length=1, max_length=255)
    price: float = Field(ge=0)
    image_url: str = Field(min_length=1, max_length=1024)

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_description(cls, v: object) -> str:
        # DB may contain NULL for description; API must still return valid strings.
        if v is None:
            return ""
        return str(v)


class FlowerCreate(FlowerBase):
    pass


class FlowerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    price: float | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, min_length=1, max_length=1024)


class FlowerOut(FlowerBase):
    id: int


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole


class AdminUserOut(UserOut):
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CartItemAdd(BaseModel):
    flower_id: int
    qty: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    qty: int = Field(gt=0)


class CartItemOut(BaseModel):
    id: int
    flower: FlowerOut
    qty: int


class OrderItemOut(BaseModel):
    flower: FlowerOut
    qty: int
    unit_price: float


class OrderOut(BaseModel):
    id: int
    status: OrderStatus
    delivery_address: str
    payment_method: str
    created_at: datetime
    user_id: int | None = None
    user_username: str | None = None
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderCreate(BaseModel):
    address: str = Field(min_length=5, max_length=4000)
    payment_method: str = Field(min_length=2, max_length=255)


class AuditLogOut(BaseModel):
    id: int
    actor_username: str
    action: str
    entity: str
    entity_id: int | None
    before: dict | None
    after: dict | None
    meta: dict | None
    created_at: datetime


class AssistantMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AssistantCriteriaOut(BaseModel):
    style: str | None = None
    recipient: str | None = None
    budget_text: str | None = None
    budget_max: float | None = None


class AssistantProductOut(FlowerOut):
    match_reason: str | None = None


class AssistantChatRequest(BaseModel):
    messages: list[AssistantMessageIn] = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=6)


class AssistantChatResponse(BaseModel):
    reply: str
    needs_clarification: bool
    criteria: AssistantCriteriaOut
    products: list[AssistantProductOut]
    source: str


STYLE_KEYWORDS: dict[str, list[str]] = {
    "нежный": ["нежн", "роз", "pink", "white", "бел", "пион", "тюльпан", "роман"],
    "романтичный": ["роман", "роз", "red", "крас", "пион", "серд"],
    "яркий": ["ярк", "red", "крас", "orange", "оранж", "сад", "микс"],
    "классический": ["white", "бел", "роз", "classic", "класс"],
}

RECIPIENT_KEYWORDS: dict[str, list[str]] = {
    "девушке": ["нежн", "роман", "роз", "пион", "тюльпан", "pink", "бел"],
    "маме": ["класс", "бел", "сад", "лилия", "хриз"],
    "коллеге": ["класс", "микс", "white", "бел"],
}


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _budget_from_text(text: str) -> tuple[str | None, float | None]:
    lowered = _normalize_text(text)
    digits = "".join(ch if ch.isdigit() else " " for ch in lowered).split()
    if digits:
        numeric_values = [float(part) for part in digits]
        return "numeric", max(numeric_values)
    if any(token in lowered for token in ["недорог", "дешев", "бюджет", "эконом"]):
        return "budget", 3500.0
    if any(token in lowered for token in ["средн", "оптимал"]):
        return "mid", 6000.0
    if any(token in lowered for token in ["премиум", "дорог", "роскош", "люкс"]):
        return "premium", 12000.0
    return None, None


def _extract_criteria_fallback(messages: list[AssistantMessageIn]) -> dict:
    conversation = " ".join(message.content for message in messages)
    lowered = _normalize_text(conversation)

    style = None
    for candidate in STYLE_KEYWORDS:
        if candidate in lowered:
            style = candidate
            break

    recipient = None
    for candidate in RECIPIENT_KEYWORDS:
        if candidate in lowered:
            recipient = candidate
            break

    budget_text, budget_max = _budget_from_text(conversation)
    needs_budget = budget_max is None and budget_text is None

    return {
        "style": style,
        "recipient": recipient,
        "budget_text": budget_text,
        "budget_max": budget_max,
        "needs_budget": needs_budget,
        "clarification_question": (
            "Подскажите, пожалуйста, в каком бюджете подобрать варианты?"
            if needs_budget
            else None
        ),
        "search_summary": conversation.strip(),
    }


def _call_ollama(*, messages: list[dict], json_mode: bool = False, temperature: float = 0.2) -> str:
    return _call_ollama_with_model(
        messages=messages,
        model=OLLAMA_REPLY_MODEL,
        json_mode=json_mode,
        temperature=temperature,
    )


def _call_ollama_with_model(
    *,
    messages: list[dict],
    model: str,
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"

    req = urllib_request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable at {OLLAMA_BASE_URL}: {exc.reason}",
        ) from exc

    try:
        payload = json.loads(raw)
        return payload["message"]["content"]
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Invalid response from Ollama") from exc


def _stream_ollama(
    *,
    messages: list[dict],
    model: str,
    temperature: float = 0.2,
):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature},
    }

    req = urllib_request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = chunk.get("message") or {}
                content = message.get("content") or ""
                if content:
                    yield content
                if chunk.get("done"):
                    break
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable at {OLLAMA_BASE_URL}: {exc.reason}",
        ) from exc


def _extract_criteria_with_ollama(messages: list[AssistantMessageIn]) -> dict:
    conversation = "\n".join(f"{item.role}: {item.content}" for item in messages)
    prompt = [
        {
            "role": "system",
            "content": CRITERIA_EXTRACTION_SYSTEM_PROMPT,
        },
        {"role": "user", "content": conversation},
    ]

    content = _call_ollama_with_model(
        messages=prompt,
        model=OLLAMA_EXTRACTION_MODEL,
        json_mode=True,
        temperature=0,
    )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return _extract_criteria_fallback(messages)

    budget_text = parsed.get("budget_text")
    budget_max = parsed.get("budget_max")
    if budget_max is not None:
        try:
            budget_max = float(budget_max)
        except (TypeError, ValueError):
            budget_max = None

    if budget_max is None and budget_text:
        _, inferred_budget = _budget_from_text(str(budget_text))
        budget_max = inferred_budget

    needs_budget = bool(parsed.get("needs_budget")) and budget_max is None and not budget_text
    if budget_max is None and not budget_text:
        needs_budget = True

    return {
        "style": parsed.get("style"),
        "recipient": parsed.get("recipient"),
        "budget_text": budget_text,
        "budget_max": budget_max,
        "needs_budget": needs_budget,
        "clarification_question": (
            parsed.get("clarification_question")
            or "Подскажите, пожалуйста, в каком бюджете подобрать варианты?"
        )
        if needs_budget
        else None,
        "search_summary": parsed.get("search_summary") or conversation,
    }


def _extract_criteria(messages: list[AssistantMessageIn]) -> dict:
    fallback = _extract_criteria_fallback(messages)
    if not OLLAMA_EXTRACT_WITH_LLM:
        return fallback

    has_enough_signal = bool(fallback.get("budget_max") is not None and (fallback.get("style") or fallback.get("recipient")))
    if has_enough_signal:
        return fallback

    try:
        parsed = _extract_criteria_with_ollama(messages)
    except HTTPException:
        return fallback

    return {
        "style": parsed.get("style") or fallback.get("style"),
        "recipient": parsed.get("recipient") or fallback.get("recipient"),
        "budget_text": parsed.get("budget_text") or fallback.get("budget_text"),
        "budget_max": parsed.get("budget_max") if parsed.get("budget_max") is not None else fallback.get("budget_max"),
        "needs_budget": parsed.get("needs_budget", fallback.get("needs_budget")),
        "clarification_question": parsed.get("clarification_question") or fallback.get("clarification_question"),
        "search_summary": parsed.get("search_summary") or fallback.get("search_summary"),
    }


def _match_reason(*, style: str | None, recipient: str | None, budget_max: float | None, price: float) -> str:
    parts: list[str] = []
    if style:
        parts.append(f"подходит по стилю: {style}")
    if recipient:
        parts.append(f"уместно для: {recipient}")
    if budget_max is not None and price <= budget_max:
        parts.append("вписывается в бюджет")
    elif budget_max is not None:
        parts.append("слегка выше бюджета")
    return ", ".join(parts) if parts else "подобран по вашему запросу"


def search_products(
    *,
    db: Session,
    style: str | None,
    recipient: str | None,
    budget_max: float | None,
    limit: int,
) -> list[AssistantProductOut]:
    rows = db.query(FlowerModel).order_by(FlowerModel.price.asc(), FlowerModel.id.asc()).all()
    if not rows:
        return []

    candidates: list[tuple[float, FlowerModel]] = []
    style_keywords = STYLE_KEYWORDS.get(_normalize_text(style), [])
    recipient_keywords = RECIPIENT_KEYWORDS.get(_normalize_text(recipient), [])

    for row in rows:
        haystack = _normalize_text(row.name)
        price = float(row.price)
        score = 0.0

        for keyword in style_keywords:
            if keyword in haystack:
                score += 4
        for keyword in recipient_keywords:
            if keyword in haystack:
                score += 3

        if budget_max is not None:
            if price <= budget_max:
                score += 3 + max(0.0, (budget_max - price) / max(budget_max, 1))
            else:
                score -= 5 + ((price - budget_max) / max(budget_max, 1))
        else:
            score += 1

        candidates.append((score, row))

    within_budget = [item for item in candidates if budget_max is None or float(item[1].price) <= budget_max]
    ranked = within_budget or candidates
    ranked.sort(key=lambda item: (-item[0], float(item[1].price), item[1].id))

    return [
        AssistantProductOut(
            id=row.id,
            name=row.name,
            description=row.description,
            category=row.category,
            price=float(row.price),
            image_url=row.image_url,
            match_reason=_match_reason(
                style=style,
                recipient=recipient,
                budget_max=budget_max,
                price=float(row.price),
            ),
        )
        for _, row in ranked[:limit]
    ]


def _build_assistant_reply(
    *,
    criteria: dict,
    products: list[AssistantProductOut],
) -> str:
    if not products:
        return (
            "Сейчас не нашёл подходящих букетов по этим условиям. "
            "Могу подобрать варианты, если немного расширим бюджет или изменим стиль."
        )

    products_json = json.dumps([product.model_dump() for product in products], ensure_ascii=False)
    criteria_json = json.dumps(
        {
            "style": criteria.get("style"),
            "recipient": criteria.get("recipient"),
            "budget_text": criteria.get("budget_text"),
            "budget_max": criteria.get("budget_max"),
        },
        ensure_ascii=False,
    )

    prompt = [
        {
            "role": "system",
            "content": RECOMMENDATION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Критерии клиента: {criteria_json}\n"
                f"Найденные товары: {products_json}"
            ),
        },
    ]

    return _call_ollama_with_model(
        messages=prompt,
        model=OLLAMA_REPLY_MODEL,
        json_mode=False,
        temperature=0.4,
    ).strip()


def _stream_assistant_reply(
    *,
    criteria: dict,
    products: list[AssistantProductOut],
):
    products_json = json.dumps([product.model_dump() for product in products], ensure_ascii=False)
    criteria_json = json.dumps(
        {
            "style": criteria.get("style"),
            "recipient": criteria.get("recipient"),
            "budget_text": criteria.get("budget_text"),
            "budget_max": criteria.get("budget_max"),
        },
        ensure_ascii=False,
    )

    prompt = [
        {
            "role": "system",
            "content": RECOMMENDATION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"РљСЂРёС‚РµСЂРёРё РєР»РёРµРЅС‚Р°: {criteria_json}\n"
                f"РќР°Р№РґРµРЅРЅС‹Рµ С‚РѕРІР°СЂС‹: {products_json}"
            ),
        },
    ]

    return _stream_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, temperature=0.4)


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/assistant/health")
def assistant_health() -> dict:
    prompt = [
        {
            "role": "system",
            "content": "Ответь одним словом ok.",
        },
        {
            "role": "user",
            "content": "ping",
        },
    ]
    try:
        reply = _call_ollama(messages=prompt, json_mode=False, temperature=0).strip()
    except HTTPException:
        raise

    return {
        "status": "ok",
        "provider": "ollama",
        "model": OLLAMA_REPLY_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "reply": reply,
    }


@app.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> AssistantChatResponse:
    criteria = _extract_criteria(payload.messages)

    criteria_out = AssistantCriteriaOut(
        style=criteria.get("style"),
        recipient=criteria.get("recipient"),
        budget_text=criteria.get("budget_text"),
        budget_max=criteria.get("budget_max"),
    )

    if criteria.get("needs_budget"):
        return AssistantChatResponse(
            reply=criteria.get("clarification_question")
            or "Подскажите, пожалуйста, в каком бюджете подобрать варианты?",
            needs_clarification=True,
            criteria=criteria_out,
            products=[],
            source=f"ollama:{OLLAMA_REPLY_MODEL}",
        )

    try:
        products = search_products(
            db=db,
            style=criteria.get("style"),
            recipient=criteria.get("recipient"),
            budget_max=criteria.get("budget_max"),
            limit=payload.limit,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database is unavailable. Connect Radmin VPN and ensure PostgreSQL is reachable "
                "before requesting consultant recommendations."
            ),
        ) from exc

    reply = _build_assistant_reply(criteria=criteria, products=products)

    return AssistantChatResponse(
        reply=reply,
        needs_clarification=False,
        criteria=criteria_out,
        products=products,
        source=f"ollama:{OLLAMA_REPLY_MODEL}",
    )


@app.post("/assistant/chat/stream")
def assistant_chat_stream(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    def event_stream():
        criteria = _extract_criteria(payload.messages)
        criteria_out = AssistantCriteriaOut(
            style=criteria.get("style"),
            recipient=criteria.get("recipient"),
            budget_text=criteria.get("budget_text"),
            budget_max=criteria.get("budget_max"),
        )

        if criteria.get("needs_budget"):
            reply = criteria.get("clarification_question") or "РџРѕРґСЃРєР°Р¶РёС‚Рµ, РїРѕР¶Р°Р»СѓР№СЃС‚Р°, РІ РєР°РєРѕРј Р±СЋРґР¶РµС‚Рµ РїРѕРґРѕР±СЂР°С‚СЊ РІР°СЂРёР°РЅС‚С‹?"
            yield _sse_event(
                {
                    "type": "done",
                    "reply": reply,
                    "criteria": criteria_out.model_dump(),
                    "products": [],
                    "needs_clarification": True,
                    "source": f"ollama:{OLLAMA_REPLY_MODEL}",
                }
            )
            return

        try:
            products = search_products(
                db=db,
                style=criteria.get("style"),
                recipient=criteria.get("recipient"),
                budget_max=criteria.get("budget_max"),
                limit=payload.limit,
            )
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Database is unavailable. Connect Radmin VPN and ensure PostgreSQL is reachable "
                    "before requesting consultant recommendations."
                ),
            ) from exc

        if not products:
            reply = _build_assistant_reply(criteria=criteria, products=products)
            yield _sse_event(
                {
                    "type": "done",
                    "reply": reply,
                    "criteria": criteria_out.model_dump(),
                    "products": [],
                    "needs_clarification": False,
                    "source": f"ollama:{OLLAMA_REPLY_MODEL}",
                }
            )
            return

        yield _sse_event(
            {
                "type": "meta",
                "criteria": criteria_out.model_dump(),
                "products": [product.model_dump() for product in products],
                "needs_clarification": False,
                "source": f"ollama:{OLLAMA_REPLY_MODEL}",
            }
        )

        reply_parts: list[str] = []
        for chunk in _stream_assistant_reply(criteria=criteria, products=products):
            reply_parts.append(chunk)
            yield _sse_event({"type": "delta", "delta": chunk})

        yield _sse_event(
            {
                "type": "done",
                "reply": "".join(reply_parts).strip(),
                "criteria": criteria_out.model_dump(),
                "products": [product.model_dump() for product in products],
                "needs_clarification": False,
                "source": f"ollama:{OLLAMA_REPLY_MODEL}",
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/auth/register", response_model=UserOut)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> UserOut:
    exists = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = UserModel(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role)


@app.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if user is None or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = _create_access_token(sub=user.username, role=user.role.value)
    return TokenOut(access_token=token)


@app.get("/me", response_model=UserOut)
def me(current_user: UserModel = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, username=current_user.username, role=current_user.role)


@app.get("/flowers", response_model=list[FlowerOut])
def list_flowers(db: Session = Depends(get_db)) -> list[FlowerOut]:
    rows = db.query(FlowerModel).order_by(FlowerModel.id.asc()).all()
    flowers: list[FlowerOut] = []
    for r in rows:
        # Защита от "битых" строк в БД (NULL/пустые значения, невалидные типы).
        try:
            flowers.append(
                FlowerOut(
                    id=r.id,
                    name=str(r.name or "").strip(),
                    description=r.description or "",
                    category=str(r.category or "Другое").strip(),
                    price=float(r.price or 0),
                    image_url=str(r.image_url or "").strip(),
                )
            )
        except Exception:
            continue
    return flowers


@app.get("/flowers/{flower_id}", response_model=FlowerOut)
def get_flower(flower_id: int, db: Session = Depends(get_db)) -> FlowerOut:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    try:
        return FlowerOut(
            id=row.id,
            name=str(row.name or "").strip(),
            description=row.description or "",
            category=str(row.category or "Другое").strip(),
            price=float(row.price or 0),
            image_url=str(row.image_url or "").strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid flower data: {exc}") from exc


@app.post("/admin/flowers", response_model=FlowerOut)
def admin_create_flower(
    payload: FlowerCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin),
) -> FlowerOut:
    row = FlowerModel(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        price=payload.price,
        image_url=str(payload.image_url),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _audit(
        db=db,
        actor=admin,
        action="create",
        entity="flower",
        entity_id=row.id,
        after={
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "category": row.category,
            "price": float(row.price),
            "image_url": row.image_url,
        },
    )
    return FlowerOut(
        id=row.id,
        name=row.name,
        description=row.description,
        category=row.category,
        price=float(row.price),
        image_url=row.image_url,
    )


@app.patch("/admin/flowers/{flower_id}", response_model=FlowerOut)
def admin_update_flower(
    flower_id: int,
    payload: FlowerUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin),
) -> FlowerOut:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")

    before = {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "price": float(row.price),
        "image_url": row.image_url,
    }
    if payload.name is not None:
        row.name = payload.name
    if payload.description is not None:
        row.description = payload.description
    if payload.category is not None:
        row.category = payload.category
    if payload.price is not None:
        row.price = payload.price
    if payload.image_url is not None:
        row.image_url = payload.image_url

    db.commit()
    db.refresh(row)
    after = {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "price": float(row.price),
        "image_url": row.image_url,
    }
    _audit(
        db=db,
        actor=admin,
        action="update",
        entity="flower",
        entity_id=row.id,
        before=before,
        after=after,
    )
    return FlowerOut(
        id=row.id,
        name=row.name,
        description=row.description,
        category=row.category,
        price=float(row.price),
        image_url=row.image_url,
    )


@app.delete("/admin/flowers/{flower_id}")
def admin_delete_flower(
    flower_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin),
) -> dict:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    before = {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "price": float(row.price),
        "image_url": row.image_url,
    }
    db.delete(row)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete",
        entity="flower",
        entity_id=flower_id,
        before=before,
    )
    return {"deleted": True}


@app.get("/cart", response_model=list[CartItemOut])
def get_cart(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CartItemOut]:
    items = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id.asc())
        .all()
    )
    return [
        CartItemOut(
            id=i.id,
            qty=i.qty,
            flower=FlowerOut(
                id=i.flower.id,
                name=i.flower.name,
                description=i.flower.description,
                category=i.flower.category,
                price=float(i.flower.price),
                image_url=i.flower.image_url,
            ),
        )
        for i in items
    ]


@app.post("/cart/items", response_model=CartItemOut)
def add_to_cart(
    payload: CartItemAdd,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemOut:
    flower = db.query(FlowerModel).filter(FlowerModel.id == payload.flower_id).one_or_none()
    if flower is None:
        raise HTTPException(status_code=404, detail="Flower not found")

    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id, CartItemModel.flower_id == payload.flower_id)
        .one_or_none()
    )
    if item is None:
        item = CartItemModel(user_id=current_user.id, flower_id=payload.flower_id, qty=payload.qty)
        db.add(item)
    else:
        item.qty += payload.qty

    db.commit()
    db.refresh(item)
    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.id == item.id)
        .one()
    )
    return CartItemOut(
        id=item.id,
        qty=item.qty,
        flower=FlowerOut(
            id=item.flower.id,
            name=item.flower.name,
            description=item.flower.description,
            category=item.flower.category,
            price=float(item.flower.price),
            image_url=item.flower.image_url,
        ),
    )


@app.patch("/cart/items/{item_id}", response_model=CartItemOut)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemOut:
    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.id == item_id, CartItemModel.user_id == current_user.id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    item.qty = payload.qty
    db.commit()
    db.refresh(item)
    return CartItemOut(
        id=item.id,
        qty=item.qty,
        flower=FlowerOut(
            id=item.flower.id,
            name=item.flower.name,
            description=item.flower.description,
            category=item.flower.category,
            price=float(item.flower.price),
            image_url=item.flower.image_url,
        ),
    )


@app.delete("/cart/items/{item_id}")
def delete_cart_item(
    item_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.query(CartItemModel).filter(CartItemModel.id == item_id, CartItemModel.user_id == current_user.id).one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.post("/orders/from-cart", response_model=OrderOut)
def create_order_from_cart(
    payload: OrderCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderOut:
    cart_items = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id)
        .all()
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = OrderModel(
        user_id=current_user.id,
        status=OrderStatus.new,
        delivery_address=payload.address.strip(),
        payment_method=payload.payment_method.strip(),
    )
    db.add(order)
    db.flush()  # assigns order.id

    for ci in cart_items:
        db.add(
            OrderItemModel(
                order_id=order.id,
                flower_id=ci.flower_id,
                qty=ci.qty,
                unit_price=float(ci.flower.price),
            )
        )
        db.delete(ci)

    db.commit()
    order = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.id == order.id)
        .one()
    )

    return OrderOut(
        id=order.id,
        status=order.status,
        delivery_address=order.delivery_address,
        payment_method=order.payment_method,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    description=it.flower.description,
                    category=it.flower.category,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/me/orders", response_model=list[OrderOut])
def my_orders(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderOut]:
    orders = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.user_id == current_user.id)
        .order_by(OrderModel.id.desc())
        .all()
    )
    return [
        OrderOut(
            id=o.id,
            status=o.status,
            delivery_address=o.delivery_address,
            payment_method=o.payment_method,
            created_at=o.created_at,
            items=[
                OrderItemOut(
                    flower=FlowerOut(
                        id=it.flower.id,
                        name=it.flower.name,
                        description=it.flower.description,
                        category=it.flower.category,
                        price=float(it.flower.price),
                        image_url=it.flower.image_url,
                    ),
                    qty=it.qty,
                    unit_price=float(it.unit_price),
                )
                for it in o.items
            ],
        )
        for o in orders
    ]


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderOut:
    order = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.id == order_id)
        .one_or_none()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    return OrderOut(
        id=order.id,
        status=order.status,
        delivery_address=order.delivery_address,
        payment_method=order.payment_method,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    description=it.flower.description,
                    category=it.flower.category,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/admin/orders", response_model=list[OrderOut])
def admin_list_orders(_: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> list[OrderOut]:
    orders = (
        db.query(OrderModel)
        .options(
            joinedload(OrderModel.user),
            joinedload(OrderModel.items).joinedload(OrderItemModel.flower),
        )
        .order_by(OrderModel.id.desc())
        .all()
    )
    return [
        OrderOut(
            id=o.id,
            status=o.status,
            delivery_address=o.delivery_address,
            payment_method=o.payment_method,
            created_at=o.created_at,
            user_id=o.user_id,
            user_username=o.user.username if o.user else None,
            items=[
                OrderItemOut(
                    flower=FlowerOut(
                        id=it.flower.id,
                        name=it.flower.name,
                        description=it.flower.description,
                        category=it.flower.category,
                        price=float(it.flower.price),
                        image_url=it.flower.image_url,
                    ),
                    qty=it.qty,
                    unit_price=float(it.unit_price),
                )
                for it in o.items
            ],
        )
        for o in orders
    ]


@app.patch("/admin/orders/{order_id}/status", response_model=OrderOut)
def admin_update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = (
        db.query(OrderModel)
        .options(
            joinedload(OrderModel.user),
            joinedload(OrderModel.items).joinedload(OrderItemModel.flower),
        )
        .filter(OrderModel.id == order_id)
        .one_or_none()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    before = {"id": order.id, "status": order.status.value}
    order.status = payload.status
    db.commit()
    db.refresh(order)
    _audit(
        db=db,
        actor=admin,
        action="update_status",
        entity="order",
        entity_id=order.id,
        before=before,
        after={"id": order.id, "status": order.status.value},
    )

    return OrderOut(
        id=order.id,
        status=order.status,
        delivery_address=order.delivery_address,
        payment_method=order.payment_method,
        created_at=order.created_at,
        user_id=order.user_id,
        user_username=order.user.username if order.user else None,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    description=it.flower.description,
                    category=it.flower.category,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/admin/users", response_model=list[AdminUserOut])
def admin_list_users(_: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> list[AdminUserOut]:
    users = db.query(UserModel).order_by(UserModel.id.asc()).all()
    return [
        AdminUserOut(
            id=user.id,
            username=user.username,
            role=user.role,
            created_at=user.created_at,
        )
        for user in users
    ]


@app.get("/admin/users/{user_id}", response_model=UserOut)
def admin_get_user(user_id: int, _: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    user = db.query(UserModel).filter(UserModel.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=user.id, username=user.username, role=user.role)


@app.get("/admin/audit", response_model=list[AuditLogOut])
def admin_list_audit(
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 100,
) -> list[AuditLogOut]:
    rows = (
        db.query(AuditLogModel)
        .order_by(AuditLogModel.id.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return [
        AuditLogOut(
            id=r.id,
            actor_username=r.actor_username,
            action=r.action,
            entity=r.entity,
            entity_id=r.entity_id,
            before=r.before,
            after=r.after,
            meta=r.meta,
            created_at=r.created_at,
        )
        for r in rows
    ]


@app.get("/admin/audit/{audit_id}", response_model=AuditLogOut)
def admin_get_audit(
    audit_id: int,
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AuditLogOut:
    r = db.query(AuditLogModel).filter(AuditLogModel.id == audit_id).one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogOut(
        id=r.id,
        actor_username=r.actor_username,
        action=r.action,
        entity=r.entity,
        entity_id=r.entity_id,
        before=r.before,
        after=r.after,
        meta=r.meta,
        created_at=r.created_at,
    )


@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    user = db.query(UserModel).filter(UserModel.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    before = {"id": user.id, "username": user.username, "role": user.role.value}
    db.delete(user)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete",
        entity="user",
        entity_id=user_id,
        before=before,
    )
    return {"deleted": True}
