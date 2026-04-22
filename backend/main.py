import os
import json
import re
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
from forecast import forecast_router
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


OPENAPI_TAGS = [
    {"name": "user", "description": "Операции авторизованного пользователя."},
    {"name": "admin", "description": "Административные операции."},
    {"name": "guest", "description": "Публичные и служебные endpoints без авторизации."},
    {"name": "ollama", "description": "Endpoints, связанные с ассистентом и Ollama."},
    {"name": "forecast", "description": "Прогнозирование спроса и переобучение модели XGBoost."},
]


app = FastAPI(openapi_tags=OPENAPI_TAGS)
app.include_router(forecast_router, prefix="/forecast", tags=["forecast"])

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
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1qaz")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_REPLY_MODEL = os.getenv("OLLAMA_REPLY_MODEL", OLLAMA_MODEL)
OLLAMA_EXTRACTION_MODEL = os.getenv("OLLAMA_EXTRACTION_MODEL", OLLAMA_REPLY_MODEL)
OLLAMA_EXTRACT_WITH_LLM = os.getenv("OLLAMA_EXTRACT_WITH_LLM", "true").lower() == "true"
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
    budget_min: float | None = None
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


def _last_user_message(messages: list[AssistantMessageIn]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content.strip()
    return ""


def _tokenize_search_text(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", _normalize_text(text))
    stopwords = {
        "для", "под", "подбери", "подобрать", "покажи", "показать", "хочу", "нужен", "нужно", "надо",
        "мне", "нам", "это", "этот", "эта", "есть", "что", "какой", "какие", "как", "или", "ещё",
        "еще", "то", "на", "к", "ко", "по", "из", "в", "во", "с", "со", "до", "от", "и", "а", "но",
        "не", "очень", "самый", "самая", "самое", "букет", "букета", "букеты", "букетов", "вариант",
        "варианты", "товар", "товары",
    }
    return [token for token in tokens if len(token) > 1 and token not in stopwords and not token.isdigit()]


def _extract_budget_candidates(text: str) -> list[float]:
    lowered = _normalize_text(text)
    cleaned = re.sub(r"\b\d{1,2}\s+(марта|февраля|января|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b", " ", lowered)
    cleaned = re.sub(r"\b(20\d{2}|19\d{2})\b", " ", cleaned)
    cleaned = re.sub(r"\b\d+\s*лет\b", " ", cleaned)
    cleaned = re.sub(r"\b\d+\s*(шт|штук)\b", " ", cleaned)

    matches: list[float] = []
    for raw_value, unit in re.findall(
        r"(?:до|не\s+дороже|не\s+выше|максимум|макс(?:имум)?|в\s+пределах|в\s+районе|примерно|около|бюджет(?:ом)?\s*(?:до)?|за)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?",
        cleaned,
    ):
        try:
            numeric = float(raw_value.replace(" ", ""))
        except ValueError:
            continue
        if unit in {"тыс", "тысяча", "тысячи", "тысяч", "k"}:
            numeric *= 1000
        if 300 <= numeric <= 300000:
            matches.append(numeric)

    for raw_value, _unit in re.findall(r"(\d+(?:[.,]\d+)?)\s*(тыс|тысяч[аи]?|k)\b", cleaned):
        try:
            numeric = float(raw_value.replace(",", ".")) * 1000
        except ValueError:
            continue
        if 300 <= numeric <= 300000:
            matches.append(numeric)

    for raw_value in re.findall(r"(\d[\d\s]{2,8})\s*(?:руб|р|₽)\b", cleaned):
        try:
            numeric = float(raw_value.replace(" ", ""))
        except ValueError:
            continue
        if 300 <= numeric <= 300000:
            matches.append(numeric)

    return matches

def _budget_range_from_text(text: str) -> tuple[str | None, float | None, float | None]:
    lowered = _normalize_text(text)
    range_match = re.search(
        r"(?:от|с)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?\s*(?:до|-|–|—)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?",
        lowered,
    )
    if range_match:
        min_raw, min_unit, max_raw, max_unit = range_match.groups()

        def _to_number(raw: str, unit: str | None) -> float | None:
            try:
                value = float(raw.replace(" ", ""))
            except ValueError:
                return None
            if unit in {"тыс", "тысяча", "тысячи", "тысяч", "k"}:
                value *= 1000
            if 300 <= value <= 300000:
                return value
            return None

        budget_min = _to_number(min_raw, min_unit)
        budget_max = _to_number(max_raw, max_unit)
        if budget_min is not None and budget_max is not None:
            if budget_min > budget_max:
                budget_min, budget_max = budget_max, budget_min
            return "range", budget_min, budget_max

    lowered = _normalize_text(text)
    numeric_values = _extract_budget_candidates(text)
    if numeric_values:
        return "numeric", None, max(numeric_values)
    if any(token in lowered for token in ["РЅРµРґРѕСЂРѕРі", "РґРµС€РµРІ", "Р±СЋРґР¶РµС‚", "СЌРєРѕРЅРѕРј"]):
        return "budget", None, 3500.0
    if any(token in lowered for token in ["СЃСЂРµРґРЅ", "РѕРїС‚РёРјР°Р»"]):
        return "mid", None, 6000.0
    if any(token in lowered for token in ["РїСЂРµРјРёСѓРј", "РґРѕСЂРѕРі", "СЂРѕСЃРєРѕС€", "Р»СЋРєСЃ"]):
        return "premium", None, 12000.0
    return None, None, None


def _budget_from_text(text: str) -> tuple[str | None, float | None]:
    lowered = _normalize_text(text)
    numeric_values = _extract_budget_candidates(text)
    if numeric_values:
        return "numeric", max(numeric_values)
    if any(token in lowered for token in ["недорог", "дешев", "бюджет", "эконом"]):
        return "budget", 3500.0
    if any(token in lowered for token in ["средн", "оптимал"]):
        return "mid", 6000.0
    if any(token in lowered for token in ["премиум", "дорог", "роскош", "люкс"]):
        return "premium", 12000.0
    return None, None


def _detect_intents(messages: list[AssistantMessageIn]) -> dict[str, bool]:
    last_user_text = _normalize_text(_last_user_message(messages))

    def has_any(variants: list[str]) -> bool:
        return any(variant in last_user_text for variant in variants)

    return {
        "compare": has_any(["сравни", "сравнить", "сравнение", "что лучше", "чем отличается"]),
        "cheaper": has_any(["дешевле", "подешевле", "более дешев", "не такое дорого", "эконом"]),
        "brighter": has_any(["ярче", "поярче", "более ярк", "насыщенн"]),
        "alternative": has_any(["ещё", "еще", "другой", "другие", "альтернати", "вариант"]),
    }


def _extract_budget_range(text: str) -> tuple[str | None, float | None, float | None]:
    lowered = _normalize_text(text)
    range_match = re.search(
        r"(?:от|с)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?\s*(?:до|-|–|—)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?",
        lowered,
    )
    if range_match:
        min_raw, min_unit, max_raw, max_unit = range_match.groups()

        def _to_number(raw: str, unit: str | None) -> float | None:
            try:
                value = float(raw.replace(" ", ""))
            except ValueError:
                return None
            if unit in {"тыс", "тысяча", "тысячи", "тысяч", "k"}:
                value *= 1000
            if 300 <= value <= 300000:
                return value
            return None

        budget_min = _to_number(min_raw, min_unit)
        budget_max = _to_number(max_raw, max_unit)
        if budget_min is not None and budget_max is not None:
            if budget_min > budget_max:
                budget_min, budget_max = budget_max, budget_min
            return "range", budget_min, budget_max

    min_match = re.search(
        r"(?:от|с)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?(?!\s*(?:до|-|–|—))",
        lowered,
    )
    if min_match:
        raw_value, unit = min_match.groups()
        try:
            value = float(raw_value.replace(" ", ""))
        except ValueError:
            value = None
        if value is not None:
            if unit in {"тыс", "тысяча", "тысячи", "тысяч", "k"}:
                value *= 1000
            if 300 <= value <= 300000:
                return "min", value, None

    max_match = re.search(
        r"(?:до|не\s+дороже|не\s+выше|максимум|макс(?:имум)?|в\s+пределах|в\s+районе|примерно|около|за)\s*(\d[\d\s]{1,8})(?:\s*(руб|р|₽|тыс|тысяч[аи]?|k))?",
        lowered,
    )
    if max_match:
        raw_value, unit = max_match.groups()
        try:
            value = float(raw_value.replace(" ", ""))
        except ValueError:
            value = None
        if value is not None:
            if unit in {"тыс", "тысяча", "тысячи", "тысяч", "k"}:
                value *= 1000
            if 300 <= value <= 300000:
                return "numeric", None, value

    budget_text, budget_max = _budget_from_text(text)
    return budget_text, None, budget_max


def _is_smalltalk_message(messages: list[AssistantMessageIn]) -> bool:
    last_user_text = _normalize_text(_last_user_message(messages))
    if not last_user_text:
        return False

    exact_matches = {
        "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер",
        "доброе утро", "hi", "hello", "hey",
    }
    if last_user_text in exact_matches:
        return True

    smalltalk_markers = [
        "что ты умеешь", "помоги выбрать", "помоги подобрать", "можешь помочь",
        "нужна помощь", "посоветуй букет", "хочу консультацию",
    ]
    has_request_markers = any(
        marker in last_user_text
        for marker in ["букет", "цвет", "роз", "тюльпан", "хризант", "пион", "маме", "девуш", "жене", "коллеге"]
    )
    return any(marker in last_user_text for marker in smalltalk_markers) and not has_request_markers


def _build_smalltalk_reply(messages: list[AssistantMessageIn]) -> str:
    last_user_text = _normalize_text(_last_user_message(messages))
    if any(token in last_user_text for token in ["что ты умеешь", "помоги", "консультац"]):
        return (
            "Я помогу подобрать букет по поводу, получателю, стилю и бюджету. "
            "Например: 'подбери букет маме на день рождения до 5000'."
        )
    return (
        "Здравствуйте! Я помогу подобрать букет по получателю, поводу, стилю и бюджету. "
        "Напишите, для кого букет и на какую сумму ориентироваться."
    )


def _should_prefer_grounded_reply() -> bool:
    model_name = _normalize_text(OLLAMA_REPLY_MODEL)
    return "1b" in model_name or "3b" in model_name


def _reply_looks_unreliable(reply: str, *, budget_max: float | None) -> bool:
    normalized = _normalize_text(reply)
    latin_words = re.findall(r"\b[a-zA-Z]{3,}\b", reply)
    if latin_words:
        return True
    if budget_max is None and ("любой бюджет" in normalized or "в любой бюджет" in normalized):
        return True
    if "не могу" in normalized and "однако" in normalized:
        return True
    return False


def _extract_criteria_fallback(messages: list[AssistantMessageIn]) -> dict:
    conversation = " ".join(message.content for message in messages)
    last_user_text = _last_user_message(messages)
    lowered = _normalize_text(conversation)
    intents = _detect_intents(messages)

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

    budget_text, budget_min, budget_max = _extract_budget_range(last_user_text or conversation)
    needs_budget = budget_max is None and budget_min is None and budget_text is None and not any(intents.values())

    return {
        "style": style,
        "recipient": recipient,
        "budget_text": budget_text,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "intents": intents,
        "needs_budget": needs_budget,
        "clarification_question": (
            "Подскажите, пожалуйста, в каком бюджете подобрать варианты?"
            if needs_budget
            else None
        ),
        "search_summary": (last_user_text or conversation).strip(),
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
    intents = _detect_intents(messages)
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
    budget_min = parsed.get("budget_min")
    budget_max = parsed.get("budget_max")
    if budget_min is not None:
        try:
            budget_min = float(budget_min)
        except (TypeError, ValueError):
            budget_min = None
    if budget_max is not None:
        try:
            budget_max = float(budget_max)
        except (TypeError, ValueError):
            budget_max = None

    if (budget_min is None and budget_max is None) and budget_text:
        _, inferred_budget_min, inferred_budget_max = _extract_budget_range(str(budget_text))
        budget_min = inferred_budget_min
        budget_max = inferred_budget_max

    needs_budget = bool(parsed.get("needs_budget")) and budget_max is None and budget_min is None and not budget_text and not any(intents.values())
    if budget_max is None and budget_min is None and not budget_text and not any(intents.values()):
        needs_budget = True

    return {
        "style": parsed.get("style"),
        "recipient": parsed.get("recipient"),
        "budget_text": budget_text,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "intents": intents,
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

    has_enough_signal = bool(
        (fallback.get("budget_max") is not None or fallback.get("budget_min") is not None)
        and (fallback.get("style") or fallback.get("recipient"))
    )
    if has_enough_signal:
        return fallback

    try:
        parsed = _extract_criteria_with_ollama(messages)
    except HTTPException:
        return fallback

    return {
        "style": parsed.get("style") or fallback.get("style"),
        "recipient": parsed.get("recipient") or fallback.get("recipient"),
        "budget_text": fallback.get("budget_text") or parsed.get("budget_text"),
        "budget_min": fallback.get("budget_min") if fallback.get("budget_min") is not None else parsed.get("budget_min"),
        "budget_max": fallback.get("budget_max") if fallback.get("budget_max") is not None else parsed.get("budget_max"),
        "intents": fallback.get("intents") or {},
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


def _format_price_rub(value: float) -> str:
    rounded = int(round(value))
    return f"{rounded:,}".replace(",", " ") + " ₽"


def _match_reason(*, style: str | None, recipient: str | None, budget_min: float | None, budget_max: float | None, price: float) -> str:
    parts: list[str] = []
    if style:
        parts.append(f"РїРѕРґС…РѕРґРёС‚ РїРѕ СЃС‚РёР»СЋ: {style}")
    if recipient:
        parts.append(f"СѓРјРµСЃС‚РЅРѕ РґР»СЏ: {recipient}")
    in_min = budget_min is None or price >= budget_min
    in_max = budget_max is None or price <= budget_max
    if in_min and in_max and (budget_min is not None or budget_max is not None):
        parts.append("РІРїРёСЃС‹РІР°РµС‚СЃСЏ РІ Р±СЋРґР¶РµС‚")
    elif budget_min is not None and price < budget_min:
        parts.append("РЅРµРјРЅРѕРіРѕ РЅРёР¶Рµ Р±СЋРґР¶РµС‚Р°")
    elif budget_max is not None and price > budget_max:
        parts.append("СЃР»РµРіРєР° РІС‹С€Рµ Р±СЋРґР¶РµС‚Р°")
    return ", ".join(parts) if parts else "РїРѕРґРѕР±СЂР°РЅ РїРѕ РІР°С€РµРјСѓ Р·Р°РїСЂРѕСЃСѓ"


def _build_grounded_assistant_reply(
    *,
    criteria: dict,
    products: list[AssistantProductOut],
) -> str:
    if not products:
        return (
            "Сейчас не нашёл подходящих букетов по этим условиям. "
            "Могу подобрать варианты, если немного расширим бюджет или изменим стиль."
        )

    style = criteria.get("style")
    recipient = criteria.get("recipient")
    budget_max = criteria.get("budget_max")

    intro_parts: list[str] = []
    if recipient:
        intro_parts.append(f"для {recipient}")
    if style:
        intro_parts.append(f"в стиле \"{style}\"")
    if budget_max is not None:
        intro_parts.append(f"до {_format_price_rub(float(budget_max))}")

    intro = "Подобрал варианты"
    if intro_parts:
        intro += " " + ", ".join(intro_parts)
    intro += "."

    lines = [intro]
    for index, product in enumerate(products[:3], start=1):
        line = f"{index}. {product.name} — {_format_price_rub(product.price)}."
        if product.category:
            line += f" Категория: {product.category}."
        if product.description:
            line += f" {product.description.strip().rstrip('.')}."
        if product.match_reason:
            line += f" {product.match_reason.strip().rstrip('.')}."
        lines.append(line)

    lines.append("Если хотите, могу сузить выбор по стилю, поводу или точному бюджету.")
    return "\n".join(lines)


def _score_keyword_hits(text: str, keywords: list[str], weight: float) -> float:
    score = 0.0
    for keyword in keywords:
        if keyword and keyword in text:
            score += weight
    return score


def _build_product_search_text(row: FlowerModel) -> tuple[str, str, str, str]:
    name_text = _normalize_text(row.name)
    category_text = _normalize_text(row.category)
    description_text = _normalize_text(row.description)
    combined = " ".join(part for part in [name_text, category_text, description_text] if part)
    return name_text, category_text, description_text, combined


def _choose_diverse_products(
    ranked: list[tuple[float, FlowerModel]],
    *,
    limit: int,
    compare_mode: bool,
) -> list[FlowerModel]:
    if not ranked:
        return []

    selected: list[FlowerModel] = []
    seen_signatures: set[str] = set()
    target_limit = max(limit, 2) if compare_mode else limit

    for _, row in ranked:
        first_word = _normalize_text(row.name).split(" ")[0] if row.name else str(row.id)
        signature = f"{_normalize_text(row.category)}|{first_word}"
        if compare_mode and signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        selected.append(row)
        if len(selected) >= target_limit:
            break

    if len(selected) < target_limit:
        existing_ids = {row.id for row in selected}
        for _, row in ranked:
            if row.id in existing_ids:
                continue
            selected.append(row)
            existing_ids.add(row.id)
            if len(selected) >= target_limit:
                break

    return selected[:target_limit]


def search_products(
    *,
    db: Session,
    search_summary: str,
    style: str | None,
    recipient: str | None,
    budget_max: float | None,
    intents: dict[str, bool] | None,
    limit: int,
) -> list[AssistantProductOut]:
    rows = db.query(FlowerModel).order_by(FlowerModel.price.asc(), FlowerModel.id.asc()).all()
    if not rows:
        return []

    intents = intents or {}
    candidates: list[tuple[float, FlowerModel]] = []
    style_keywords = STYLE_KEYWORDS.get(_normalize_text(style), [])
    recipient_keywords = RECIPIENT_KEYWORDS.get(_normalize_text(recipient), [])
    query_tokens = _tokenize_search_text(search_summary)
    compare_mode = bool(intents.get("compare"))
    cheaper_mode = bool(intents.get("cheaper"))
    brighter_mode = bool(intents.get("brighter"))

    bright_keywords = ["ярк", "насыщ", "оранж", "крас", "yellow", "orange", "red", "mix", "микс", "сочн"]
    soft_keywords = ["неж", "white", "pink", "pastel", "пастел", "класс", "спокойн"]

    for row in rows:
        name_text, category_text, description_text, combined_text = _build_product_search_text(row)
        price = float(row.price)
        score = 0.0

        score += _score_keyword_hits(name_text, style_keywords, 4.5)
        score += _score_keyword_hits(category_text, style_keywords, 3.5)
        score += _score_keyword_hits(description_text, style_keywords, 2.5)
        score += _score_keyword_hits(name_text, recipient_keywords, 3.5)
        score += _score_keyword_hits(category_text, recipient_keywords, 2.0)
        score += _score_keyword_hits(description_text, recipient_keywords, 2.0)

        for token in query_tokens:
            if token in name_text:
                score += 4.0
            elif token in category_text:
                score += 2.8
            elif token in description_text:
                score += 2.2

        if brighter_mode:
            score += _score_keyword_hits(combined_text, bright_keywords, 1.5)
            score -= _score_keyword_hits(combined_text, soft_keywords, 0.8)

        if budget_max is not None:
            if price <= budget_max:
                score += 4.0 + max(0.0, (budget_max - price) / max(budget_max, 1)) * (1.6 if cheaper_mode else 1.0)
            else:
                score -= 6.0 + ((price - budget_max) / max(budget_max, 1)) * 7.0
        else:
            score += 1.0

        if cheaper_mode:
            score += max(0.0, 25000.0 - min(price, 25000.0)) / 2500.0

        if intents.get("alternative"):
            score += 0.3

        candidates.append((score, row))

    within_budget = [item for item in candidates if budget_max is None or float(item[1].price) <= budget_max]
    ranked = within_budget or candidates
    ranked.sort(key=lambda item: (-item[0], float(item[1].price), item[1].id))
    selected_rows = _choose_diverse_products(ranked, limit=limit, compare_mode=compare_mode)

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
        for row in selected_rows
    ]


def _match_reason(*, style: str | None, recipient: str | None, budget_min: float | None, budget_max: float | None, price: float) -> str:
    parts: list[str] = []
    if style:
        parts.append(f"РїРѕРґС…РѕРґРёС‚ РїРѕ СЃС‚РёР»СЋ: {style}")
    if recipient:
        parts.append(f"СѓРјРµСЃС‚РЅРѕ РґР»СЏ: {recipient}")
    in_min = budget_min is None or price >= budget_min
    in_max = budget_max is None or price <= budget_max
    if in_min and in_max and (budget_min is not None or budget_max is not None):
        parts.append("РІРїРёСЃС‹РІР°РµС‚СЃСЏ РІ Р±СЋРґР¶РµС‚")
    elif budget_min is not None and price < budget_min:
        parts.append("РЅРµРјРЅРѕРіРѕ РЅРёР¶Рµ Р±СЋРґР¶РµС‚Р°")
    elif budget_max is not None and price > budget_max:
        parts.append("СЃР»РµРіРєР° РІС‹С€Рµ Р±СЋРґР¶РµС‚Р°")
    return ", ".join(parts) if parts else "РїРѕРґРѕР±СЂР°РЅ РїРѕ РІР°С€РµРјСѓ Р·Р°РїСЂРѕСЃСѓ"


def _build_grounded_assistant_reply(
    *,
    criteria: dict,
    products: list[AssistantProductOut],
) -> str:
    if not products:
        return (
            "РЎРµР№С‡Р°СЃ РЅРµ РЅР°С€С‘Р» РїРѕРґС…РѕРґСЏС‰РёС… Р±СѓРєРµС‚РѕРІ РїРѕ СЌС‚РёРј СѓСЃР»РѕРІРёСЏРј. "
            "РњРѕРіСѓ РїРѕРґРѕР±СЂР°С‚СЊ РІР°СЂРёР°РЅС‚С‹, РµСЃР»Рё РЅРµРјРЅРѕРіРѕ СЂР°СЃС€РёСЂРёРј Р±СЋРґР¶РµС‚ РёР»Рё РёР·РјРµРЅРёРј СЃС‚РёР»СЊ."
        )

    style = criteria.get("style")
    recipient = criteria.get("recipient")
    budget_min = criteria.get("budget_min")
    budget_max = criteria.get("budget_max")

    intro_parts: list[str] = []
    if recipient:
        intro_parts.append(f"РґР»СЏ {recipient}")
    if style:
        intro_parts.append(f"РІ СЃС‚РёР»Рµ \"{style}\"")
    if budget_min is not None and budget_max is not None:
        intro_parts.append(f"РѕС‚ {_format_price_rub(float(budget_min))} РґРѕ {_format_price_rub(float(budget_max))}")
    elif budget_min is not None:
        intro_parts.append(f"РѕС‚ {_format_price_rub(float(budget_min))}")
    elif budget_max is not None:
        intro_parts.append(f"РґРѕ {_format_price_rub(float(budget_max))}")

    intro = "РџРѕРґРѕР±СЂР°Р» РІР°СЂРёР°РЅС‚С‹"
    if intro_parts:
        intro += " " + ", ".join(intro_parts)
    intro += "."

    lines = [intro]
    for index, product in enumerate(products[:3], start=1):
        line = f"{index}. {product.name} вЂ” {_format_price_rub(product.price)}."
        if product.category:
            line += f" РљР°С‚РµРіРѕСЂРёСЏ: {product.category}."
        if product.description:
            line += f" {product.description.strip().rstrip('.')}."
        if product.match_reason:
            line += f" {product.match_reason.strip().rstrip('.')}."
        lines.append(line)

    lines.append("Р•СЃР»Рё С…РѕС‚РёС‚Рµ, РјРѕРіСѓ СЃСѓР·РёС‚СЊ РІС‹Р±РѕСЂ РїРѕ СЃС‚РёР»СЋ, РїРѕРІРѕРґСѓ РёР»Рё С‚РѕС‡РЅРѕРјСѓ Р±СЋРґР¶РµС‚Сѓ.")
    return "\n".join(lines)


def search_products(
    *,
    db: Session,
    search_summary: str,
    style: str | None,
    recipient: str | None,
    budget_min: float | None,
    budget_max: float | None,
    intents: dict[str, bool] | None,
    limit: int,
) -> list[AssistantProductOut]:
    rows = db.query(FlowerModel).order_by(FlowerModel.price.asc(), FlowerModel.id.asc()).all()
    if not rows:
        return []

    intents = intents or {}
    candidates: list[tuple[float, FlowerModel]] = []
    style_keywords = STYLE_KEYWORDS.get(_normalize_text(style), [])
    recipient_keywords = RECIPIENT_KEYWORDS.get(_normalize_text(recipient), [])
    query_tokens = _tokenize_search_text(search_summary)
    compare_mode = bool(intents.get("compare"))
    cheaper_mode = bool(intents.get("cheaper"))
    brighter_mode = bool(intents.get("brighter"))

    bright_keywords = ["СЏСЂРє", "РЅР°СЃС‹С‰", "РѕСЂР°РЅР¶", "РєСЂР°СЃ", "yellow", "orange", "red", "mix", "РјРёРєСЃ", "СЃРѕС‡РЅ"]
    soft_keywords = ["РЅРµР¶", "white", "pink", "pastel", "РїР°СЃС‚РµР»", "РєР»Р°СЃСЃ", "СЃРїРѕРєРѕР№РЅ"]

    for row in rows:
        name_text, category_text, description_text, combined_text = _build_product_search_text(row)
        price = float(row.price)
        score = 0.0

        score += _score_keyword_hits(name_text, style_keywords, 4.5)
        score += _score_keyword_hits(category_text, style_keywords, 3.5)
        score += _score_keyword_hits(description_text, style_keywords, 2.5)
        score += _score_keyword_hits(name_text, recipient_keywords, 3.5)
        score += _score_keyword_hits(category_text, recipient_keywords, 2.0)
        score += _score_keyword_hits(description_text, recipient_keywords, 2.0)

        for token in query_tokens:
            if token in name_text:
                score += 4.0
            elif token in category_text:
                score += 2.8
            elif token in description_text:
                score += 2.2

        if brighter_mode:
            score += _score_keyword_hits(combined_text, bright_keywords, 1.5)
            score -= _score_keyword_hits(combined_text, soft_keywords, 0.8)

        in_min = budget_min is None or price >= budget_min
        in_max = budget_max is None or price <= budget_max
        if in_min and in_max:
            score += 4.0
            if budget_min is not None and budget_max is not None:
                midpoint = (budget_min + budget_max) / 2
                span = max((budget_max - budget_min) / 2, 1.0)
                score += max(0.0, 1.5 - abs(price - midpoint) / span)
            elif budget_max is not None:
                score += max(0.0, (budget_max - price) / max(budget_max, 1)) * (1.6 if cheaper_mode else 1.0)
            elif budget_min is not None:
                score += max(0.0, min(price - budget_min, budget_min) / max(budget_min, 1))
        else:
            if budget_min is not None and price < budget_min:
                score -= 5.0 + ((budget_min - price) / max(budget_min, 1)) * 6.0
            if budget_max is not None and price > budget_max:
                score -= 6.0 + ((price - budget_max) / max(budget_max, 1)) * 7.0
            if budget_min is None and budget_max is None:
                score += 1.0

        if cheaper_mode:
            score += max(0.0, 25000.0 - min(price, 25000.0)) / 2500.0

        if intents.get("alternative"):
            score += 0.3

        candidates.append((score, row))

    within_budget = [
        item
        for item in candidates
        if (budget_min is None or float(item[1].price) >= budget_min)
        and (budget_max is None or float(item[1].price) <= budget_max)
    ]
    has_hard_budget = budget_min is not None or budget_max is not None
    ranked = within_budget if has_hard_budget else (within_budget or candidates)
    if has_hard_budget and not ranked:
        return []
    ranked.sort(key=lambda item: (-item[0], float(item[1].price), item[1].id))
    selected_rows = _choose_diverse_products(ranked, limit=limit, compare_mode=compare_mode)

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
                budget_min=budget_min,
                budget_max=budget_max,
                price=float(row.price),
            ),
        )
        for row in selected_rows
    ]


def _match_reason(*, style: str | None, recipient: str | None, budget_min: float | None, budget_max: float | None, price: float) -> str:
    parts: list[str] = []
    if style:
        parts.append(f"подходит по стилю: {style}")
    if recipient:
        parts.append(f"уместно для: {recipient}")
    in_min = budget_min is None or price >= budget_min
    in_max = budget_max is None or price <= budget_max
    if in_min and in_max and (budget_min is not None or budget_max is not None):
        parts.append("вписывается в бюджет")
    elif budget_min is not None and price < budget_min:
        parts.append("немного ниже бюджета")
    elif budget_max is not None and price > budget_max:
        parts.append("слегка выше бюджета")
    return ", ".join(parts) if parts else "подобран по вашему запросу"


def _build_grounded_assistant_reply(
    *,
    criteria: dict,
    products: list[AssistantProductOut],
) -> str:
    if not products:
        return (
            "Сейчас не нашёл подходящих букетов по этим условиям. "
            "Могу подобрать варианты, если немного расширим бюджет или изменим стиль."
        )

    style = criteria.get("style")
    recipient = criteria.get("recipient")
    budget_min = criteria.get("budget_min")
    budget_max = criteria.get("budget_max")

    intro_parts: list[str] = []
    if recipient:
        intro_parts.append(f"для {recipient}")
    if style:
        intro_parts.append(f"в стиле \"{style}\"")
    if budget_min is not None and budget_max is not None:
        intro_parts.append(f"от {_format_price_rub(float(budget_min))} до {_format_price_rub(float(budget_max))}")
    elif budget_min is not None:
        intro_parts.append(f"от {_format_price_rub(float(budget_min))}")
    elif budget_max is not None:
        intro_parts.append(f"до {_format_price_rub(float(budget_max))}")

    intro = "Подобрал варианты"
    if intro_parts:
        intro += " " + ", ".join(intro_parts)
    intro += "."

    lines = [intro]
    for index, product in enumerate(products[:3], start=1):
        line = f"{index}. {product.name} — {_format_price_rub(product.price)}."
        if product.category:
            line += f" Категория: {product.category}."
        if product.description:
            line += f" {product.description.strip().rstrip('.')}."
        if product.match_reason:
            line += f" {product.match_reason.strip().rstrip('.')}."
        lines.append(line)

    lines.append("Если хотите, могу сузить выбор по стилю, поводу или точному бюджету.")
    return "\n".join(lines)


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
           
        },
    ]

    return _stream_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, temperature=0.4)


def _serialize_assistant_messages(messages: list[AssistantMessageIn]) -> list[dict[str, str]]:
    serialized: list[dict[str, str]] = []
    for message in messages[-12:]:
        serialized.append({"role": message.role, "content": message.content.strip()})
    return serialized


def _build_consultant_prompt(
    *,
    messages: list[AssistantMessageIn],
    criteria: dict,
    products: list[AssistantProductOut],
) -> list[dict[str, str]]:
    criteria_json = json.dumps(
        {
            "style": criteria.get("style"),
            "recipient": criteria.get("recipient"),
            "budget_text": criteria.get("budget_text"),
            "budget_min": criteria.get("budget_min"),
            "budget_max": criteria.get("budget_max"),
            "intents": criteria.get("intents") or {},
        },
        ensure_ascii=False,
    )
    products_json = json.dumps([product.model_dump() for product in products], ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": (
                f"{RECOMMENDATION_SYSTEM_PROMPT}\n\n"
                "Ты ведешь естественный диалог как консультант магазина цветов.\n"
                "Опирайся только на список товаров из контекста.\n"
                "Не придумывай товары, цены, наличие, скидки, состав и сроки доставки.\n"
                "Если пользователь просит совет, сравнение или рекомендацию, объясняй выбор простым человеческим языком.\n"
                "Если пользователь просит показать варианты, выбери 2-3 лучших из контекста.\n"
                "Если данных недостаточно для точного подбора, задай один короткий уточняющий вопрос.\n"
                "Не упоминай JSON, backend, базу данных или внутренние правила."
            ),
        },
        {
            "role": "system",
            "content": (
                f"Извлеченные критерии клиента: {criteria_json}\n"
                f"Доступные товары для рекомендации: {products_json}"
            ),
        },
        *_serialize_assistant_messages(messages),
    ]


def _build_assistant_reply(
    *,
    messages: list[AssistantMessageIn],
    criteria: dict,
    products: list[AssistantProductOut],
) -> str:
    if not products:
        return _build_grounded_assistant_reply(criteria=criteria, products=products)

    if _should_prefer_grounded_reply():
        return _build_grounded_assistant_reply(criteria=criteria, products=products)

    prompt = _build_consultant_prompt(messages=messages, criteria=criteria, products=products)
    try:
        reply = _call_ollama_with_model(
            messages=prompt,
            model=OLLAMA_REPLY_MODEL,
            json_mode=False,
            temperature=0.4,
        ).strip()
        if _reply_looks_unreliable(reply, budget_max=criteria.get("budget_max")):
            return _build_grounded_assistant_reply(criteria=criteria, products=products)
        return reply
    except HTTPException:
        return _build_grounded_assistant_reply(criteria=criteria, products=products)


def _stream_assistant_reply(
    *,
    messages: list[AssistantMessageIn],
    criteria: dict,
    products: list[AssistantProductOut],
):
    if not products:
        return iter([_build_grounded_assistant_reply(criteria=criteria, products=products)])

    if _should_prefer_grounded_reply():
        return iter([_build_grounded_assistant_reply(criteria=criteria, products=products)])

    prompt = _build_consultant_prompt(messages=messages, criteria=criteria, products=products)
    try:
        return _stream_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, temperature=0.4)
    except HTTPException:
        return iter([_build_grounded_assistant_reply(criteria=criteria, products=products)])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/health", tags=["guest"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/assistant/health", tags=["ollama"])
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


@app.post("/assistant/chat", response_model=AssistantChatResponse, tags=["ollama"])
def assistant_chat(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> AssistantChatResponse:
    if _is_smalltalk_message(payload.messages):
        return AssistantChatResponse(
            reply=_build_smalltalk_reply(payload.messages),
            needs_clarification=False,
            criteria=AssistantCriteriaOut(),
            products=[],
            source=f"grounded:{OLLAMA_REPLY_MODEL}",
        )

    criteria = _extract_criteria(payload.messages)

    criteria_out = AssistantCriteriaOut(
        style=criteria.get("style"),
        recipient=criteria.get("recipient"),
        budget_text=criteria.get("budget_text"),
        budget_min=criteria.get("budget_min"),
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
            search_summary=criteria.get("search_summary") or "",
            style=criteria.get("style"),
            recipient=criteria.get("recipient"),
            budget_min=criteria.get("budget_min"),
            budget_max=criteria.get("budget_max"),
            intents=criteria.get("intents"),
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

    reply = _build_assistant_reply(messages=payload.messages, criteria=criteria, products=products)

    return AssistantChatResponse(
        reply=reply,
        needs_clarification=False,
        criteria=criteria_out,
        products=products,
        source=f"ollama:{OLLAMA_REPLY_MODEL}",
    )


@app.post("/assistant/chat/stream", tags=["ollama"])
def assistant_chat_stream(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    def event_stream():
        if _is_smalltalk_message(payload.messages):
            yield _sse_event(
                {
                    "type": "done",
                    "reply": _build_smalltalk_reply(payload.messages),
                    "criteria": AssistantCriteriaOut().model_dump(),
                    "products": [],
                    "needs_clarification": False,
                    "source": f"grounded:{OLLAMA_REPLY_MODEL}",
                }
            )
            return

        criteria = _extract_criteria(payload.messages)
        criteria_out = AssistantCriteriaOut(
            style=criteria.get("style"),
            recipient=criteria.get("recipient"),
            budget_text=criteria.get("budget_text"),
            budget_min=criteria.get("budget_min"),
            budget_max=criteria.get("budget_max"),
        )

        if criteria.get("needs_budget"):
            reply = criteria.get("clarification_question")
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
                search_summary=criteria.get("search_summary") or "",
                style=criteria.get("style"),
                recipient=criteria.get("recipient"),
                budget_min=criteria.get("budget_min"),
                budget_max=criteria.get("budget_max"),
                intents=criteria.get("intents"),
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
            reply = _build_assistant_reply(messages=payload.messages, criteria=criteria, products=products)
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
        for chunk in _stream_assistant_reply(messages=payload.messages, criteria=criteria, products=products):
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


@app.post("/auth/register", response_model=UserOut, tags=["guest"])
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


@app.post("/auth/login", response_model=TokenOut, tags=["guest"])
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if user is None or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = _create_access_token(sub=user.username, role=user.role.value)
    return TokenOut(access_token=token)


@app.get("/me", response_model=UserOut, tags=["user"])
def me(current_user: UserModel = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, username=current_user.username, role=current_user.role)


@app.get("/flowers", response_model=list[FlowerOut], tags=["guest"])
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


@app.get("/flowers/{flower_id}", response_model=FlowerOut, tags=["guest"])
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


@app.post("/admin/flowers", response_model=FlowerOut, tags=["admin"])
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


@app.patch("/admin/flowers/{flower_id}", response_model=FlowerOut, tags=["admin"])
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


@app.delete("/admin/flowers/{flower_id}", tags=["admin"])
def admin_delete_flower(
    flower_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin),
) -> dict:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")

    has_orders = (
        db.query(OrderItemModel.id)
        .filter(OrderItemModel.flower_id == flower_id)
        .first()
        is not None
    )
    if has_orders:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete flower that is already used in orders",
        )

    before = {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "price": float(row.price),
        "image_url": row.image_url,
    }

    db.query(CartItemModel).filter(CartItemModel.flower_id == flower_id).delete(synchronize_session=False)
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


@app.get("/cart", response_model=list[CartItemOut], tags=["user"])
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


@app.post("/cart/items", response_model=CartItemOut, tags=["user"])
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


@app.patch("/cart/items/{item_id}", response_model=CartItemOut, tags=["user"])
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


@app.delete("/cart/items/{item_id}", tags=["user"])
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


@app.post("/orders/from-cart", response_model=OrderOut, tags=["user"])
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


@app.get("/me/orders", response_model=list[OrderOut], tags=["user"])
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


@app.get("/orders/{order_id}", response_model=OrderOut, tags=["user"])
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


@app.get("/admin/orders", response_model=list[OrderOut], tags=["admin"])
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


@app.patch("/admin/orders/{order_id}/status", response_model=OrderOut, tags=["admin"])
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


@app.delete("/admin/orders/{order_id}", tags=["admin"])
def admin_delete_order(
    order_id: int,
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
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

    before = {
        "id": order.id,
        "status": order.status.value,
        "delivery_address": order.delivery_address,
        "payment_method": order.payment_method,
        "user_id": order.user_id,
        "items": [
            {
                "flower_id": it.flower.id if it.flower else None,
                "flower_name": it.flower.name if it.flower else None,
                "qty": it.qty,
                "unit_price": float(it.unit_price),
            }
            for it in order.items
        ],
    }

    db.delete(order)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete",
        entity="order",
        entity_id=order_id,
        before=before,
    )
    return {"deleted": True}


@app.delete("/admin/orders", tags=["admin"])
def admin_delete_all_orders(
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    order_count = db.query(OrderModel).count()
    if order_count == 0:
        return {"deleted": True, "orders": 0, "order_items": 0}

    order_item_count = db.query(OrderItemModel).count()
    db.query(OrderItemModel).delete(synchronize_session=False)
    db.query(OrderModel).delete(synchronize_session=False)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete_all",
        entity="order",
        meta={"orders": order_count, "order_items": order_item_count},
    )
    return {"deleted": True, "orders": order_count, "order_items": order_item_count}


@app.get("/admin/users", response_model=list[AdminUserOut], tags=["admin"])
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


@app.get("/admin/users/{user_id}", response_model=UserOut, tags=["admin"])
def admin_get_user(user_id: int, _: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    user = db.query(UserModel).filter(UserModel.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=user.id, username=user.username, role=user.role)


@app.get("/admin/audit", response_model=list[AuditLogOut], tags=["admin"])
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


@app.get("/admin/audit/{audit_id}", response_model=AuditLogOut, tags=["admin"])
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


@app.delete("/admin/users/{user_id}", tags=["admin"])
def admin_delete_user(user_id: int, admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    user = db.query(UserModel).filter(UserModel.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete the current admin")
    before = {"id": user.id, "username": user.username, "role": user.role.value}

    user_order_ids = [
        row[0]
        for row in db.query(OrderModel.id).filter(OrderModel.user_id == user.id).all()
    ]
    if user_order_ids:
        db.query(OrderItemModel).filter(OrderItemModel.order_id.in_(user_order_ids)).delete(
            synchronize_session=False
        )
        db.query(OrderModel).filter(OrderModel.id.in_(user_order_ids)).delete(synchronize_session=False)
    db.query(CartItemModel).filter(CartItemModel.user_id == user.id).delete(synchronize_session=False)
    db.query(AuditLogModel).filter(AuditLogModel.actor_user_id == user.id).update(
        {AuditLogModel.actor_user_id: None},
        synchronize_session=False,
    )
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


@app.delete("/admin/users", tags=["admin"])
def admin_delete_all_users(
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    users_to_delete = db.query(UserModel).filter(UserModel.id != admin.id).all()
    if not users_to_delete:
        return {"deleted": True, "users": 0, "orders": 0, "cart_items": 0}

    user_ids = [user.id for user in users_to_delete]
    order_ids = [
        row[0]
        for row in db.query(OrderModel.id).filter(OrderModel.user_id.in_(user_ids)).all()
    ]
    order_count = len(order_ids)
    cart_count = db.query(CartItemModel).filter(CartItemModel.user_id.in_(user_ids)).count()

    if order_ids:
        db.query(OrderItemModel).filter(OrderItemModel.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.query(OrderModel).filter(OrderModel.id.in_(order_ids)).delete(synchronize_session=False)
    db.query(CartItemModel).filter(CartItemModel.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.query(AuditLogModel).filter(AuditLogModel.actor_user_id.in_(user_ids)).update(
        {AuditLogModel.actor_user_id: None},
        synchronize_session=False,
    )
    db.query(UserModel).filter(UserModel.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete_all",
        entity="user",
        meta={"users": len(user_ids), "orders": order_count, "cart_items": cart_count},
    )
    return {"deleted": True, "users": len(user_ids), "orders": order_count, "cart_items": cart_count}


@app.delete("/admin/flowers", tags=["admin"])
def admin_delete_all_flowers(
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    flower_count = db.query(FlowerModel).count()
    if flower_count == 0:
        return {"deleted": True, "flowers": 0, "orders": 0, "cart_items": 0}

    order_count = db.query(OrderModel).count()
    cart_count = db.query(CartItemModel).count()
    order_item_count = db.query(OrderItemModel).count()

    db.query(CartItemModel).delete(synchronize_session=False)
    db.query(OrderItemModel).delete(synchronize_session=False)
    db.query(OrderModel).delete(synchronize_session=False)
    db.query(FlowerModel).delete(synchronize_session=False)
    db.commit()
    _audit(
        db=db,
        actor=admin,
        action="delete_all",
        entity="flower",
        meta={
            "flowers": flower_count,
            "orders": order_count,
            "order_items": order_item_count,
            "cart_items": cart_count,
        },
    )
    return {
        "deleted": True,
        "flowers": flower_count,
        "orders": order_count,
        "order_items": order_item_count,
        "cart_items": cart_count,
    }
