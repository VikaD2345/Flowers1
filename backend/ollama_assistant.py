import json
import os
import re
from typing import Any, Iterable
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import FlowerModel
from prompts import CRITERIA_EXTRACTION_SYSTEM_PROMPT, RECOMMENDATION_SYSTEM_PROMPT


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_REPLY_MODEL = os.getenv("OLLAMA_REPLY_MODEL", OLLAMA_MODEL)
OLLAMA_EXTRACTION_MODEL = os.getenv("OLLAMA_EXTRACTION_MODEL", OLLAMA_REPLY_MODEL)
OLLAMA_EXTRACT_WITH_LLM = os.getenv("OLLAMA_EXTRACT_WITH_LLM", "true").lower() == "true"
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))

DEFAULT_BUDGET_QUESTION = "Подскажите, пожалуйста, в каком бюджете подобрать варианты?"

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


def _message_attr(message: Any, attr: str) -> str:
    if isinstance(message, dict):
        return str(message.get(attr, "")).strip()
    return str(getattr(message, attr, "")).strip()


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _last_user_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        if _message_attr(message, "role") == "user":
            return _message_attr(message, "content")
    return ""


def _serialize_messages(messages: list[Any]) -> list[dict[str, str]]:
    return [
        {"role": _message_attr(message, "role"), "content": _message_attr(message, "content")}
        for message in messages[-12:]
    ]


def _tokenize_search_text(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", _normalize_text(text))
    stopwords = {
        "для", "под", "подбери", "подобрать", "покажи", "показать", "хочу", "нужен", "нужно", "надо",
        "мне", "нам", "это", "этот", "эта", "есть", "что", "какой", "какие", "как", "или", "еще",
        "ещё", "то", "на", "к", "ко", "по", "из", "в", "во", "с", "со", "до", "от", "и", "а", "но",
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


def _detect_intents(messages: list[Any]) -> dict[str, bool]:
    last_user_text = _normalize_text(_last_user_message(messages))

    def has_any(variants: list[str]) -> bool:
        return any(variant in last_user_text for variant in variants)

    return {
        "compare": has_any(["сравни", "сравнить", "сравнение", "что лучше", "чем отличается"]),
        "cheaper": has_any(["дешевле", "подешевле", "более дешев", "не такое дорого", "эконом"]),
        "brighter": has_any(["ярче", "поярче", "более ярк", "насыщенн"]),
        "alternative": has_any(["ещё", "еще", "другой", "другие", "альтернати", "вариант"]),
    }


def is_smalltalk_message(messages: list[Any]) -> bool:
    last_user_text = _normalize_text(_last_user_message(messages))
    if not last_user_text:
        return False
    if last_user_text in {"привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", "доброе утро", "hi", "hello", "hey"}:
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


def build_smalltalk_reply(messages: list[Any]) -> str:
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


def _call_ollama(*, messages: list[dict[str, str]], model: str, json_mode: bool = False, temperature: float = 0.2) -> str:
    payload: dict[str, Any] = {
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
        raise HTTPException(status_code=503, detail=f"Ollama is unavailable at {OLLAMA_BASE_URL}: {exc.reason}") from exc

    try:
        payload = json.loads(raw)
        return str(payload["message"]["content"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Invalid response from Ollama") from exc


def _stream_ollama(*, messages: list[dict[str, str]], model: str, temperature: float = 0.2) -> Iterable[str]:
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
                content = (chunk.get("message") or {}).get("content") or ""
                if content:
                    yield str(content)
                if chunk.get("done"):
                    break
    except urllib_error.URLError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama is unavailable at {OLLAMA_BASE_URL}: {exc.reason}") from exc


def extract_criteria(messages: list[Any]) -> dict[str, Any]:
    conversation = " ".join(_message_attr(message, "content") for message in messages)
    last_user_text = _last_user_message(messages)
    lowered = _normalize_text(conversation)
    intents = _detect_intents(messages)

    style = next((candidate for candidate in STYLE_KEYWORDS if candidate in lowered), None)
    recipient = next((candidate for candidate in RECIPIENT_KEYWORDS if candidate in lowered), None)
    budget_text, budget_min, budget_max = _extract_budget_range(last_user_text or conversation)
    fallback = {
        "style": style,
        "recipient": recipient,
        "budget_text": budget_text,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "intents": intents,
        "needs_budget": budget_max is None and budget_min is None and budget_text is None and not any(intents.values()),
        "clarification_question": DEFAULT_BUDGET_QUESTION if budget_max is None and budget_min is None and budget_text is None and not any(intents.values()) else None,
        "search_summary": (last_user_text or conversation).strip(),
    }
    if not OLLAMA_EXTRACT_WITH_LLM:
        return fallback

    has_enough_signal = bool((fallback.get("budget_max") is not None or fallback.get("budget_min") is not None) and (fallback.get("style") or fallback.get("recipient")))
    if has_enough_signal:
        return fallback

    prompt = [
        {"role": "system", "content": CRITERIA_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(f"{_message_attr(item, 'role')}: {_message_attr(item, 'content')}" for item in messages)},
    ]
    try:
        content = _call_ollama(messages=prompt, model=OLLAMA_EXTRACTION_MODEL, json_mode=True, temperature=0)
        parsed = json.loads(content)
    except (HTTPException, json.JSONDecodeError):
        return fallback

    budget_min = parsed.get("budget_min")
    budget_max = parsed.get("budget_max")
    try:
        budget_min = float(budget_min) if budget_min is not None else None
    except (TypeError, ValueError):
        budget_min = None
    try:
        budget_max = float(budget_max) if budget_max is not None else None
    except (TypeError, ValueError):
        budget_max = None
    if budget_min is None and budget_max is None and parsed.get("budget_text"):
        _, budget_min, budget_max = _extract_budget_range(str(parsed["budget_text"]))

    return {
        "style": parsed.get("style") or fallback.get("style"),
        "recipient": parsed.get("recipient") or fallback.get("recipient"),
        "budget_text": fallback.get("budget_text") or parsed.get("budget_text"),
        "budget_min": fallback.get("budget_min") if fallback.get("budget_min") is not None else budget_min,
        "budget_max": fallback.get("budget_max") if fallback.get("budget_max") is not None else budget_max,
        "intents": fallback.get("intents") or {},
        "needs_budget": parsed.get("needs_budget", fallback.get("needs_budget")),
        "clarification_question": parsed.get("clarification_question") or fallback.get("clarification_question"),
        "search_summary": parsed.get("search_summary") or fallback.get("search_summary"),
    }


def _score_keyword_hits(text: str, keywords: list[str], weight: float) -> float:
    return sum(weight for keyword in keywords if keyword and keyword in text)


def _format_price_rub(value: float) -> str:
    rounded = int(round(value))
    return f"{rounded:,}".replace(",", " ") + " ₽"


def _build_product_search_text(row: FlowerModel) -> tuple[str, str, str, str]:
    name_text = _normalize_text(row.name)
    category_text = _normalize_text(row.category)
    description_text = _normalize_text(row.description)
    combined = " ".join(part for part in [name_text, category_text, description_text] if part)
    return name_text, category_text, description_text, combined


def _choose_diverse_products(ranked: list[tuple[float, FlowerModel]], *, limit: int, compare_mode: bool) -> list[FlowerModel]:
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
) -> list[dict[str, Any]]:
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
        item for item in candidates
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
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "category": row.category,
            "price": float(row.price),
            "image_url": row.image_url,
            "match_reason": _match_reason(
                style=style,
                recipient=recipient,
                budget_min=budget_min,
                budget_max=budget_max,
                price=float(row.price),
            ),
        }
        for row in selected_rows
    ]


def build_grounded_assistant_reply(*, criteria: dict[str, Any], products: list[dict[str, Any]]) -> str:
    if not products:
        return "Сейчас не нашёл подходящих букетов по этим условиям. Могу подобрать варианты, если немного расширим бюджет или изменим стиль."

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
        line = f"{index}. {product['name']} — {_format_price_rub(float(product['price']))}."
        if product.get("category"):
            line += f" Категория: {product['category']}."
        if product.get("description"):
            line += f" {str(product['description']).strip().rstrip('.')}."
        if product.get("match_reason"):
            line += f" {str(product['match_reason']).strip().rstrip('.')}."
        lines.append(line)
    lines.append("Если хотите, могу сузить выбор по стилю, поводу или точному бюджету.")
    return "\n".join(lines)


def _should_prefer_grounded_reply() -> bool:
    model_name = _normalize_text(OLLAMA_REPLY_MODEL)
    return "1b" in model_name or "3b" in model_name


def _reply_looks_unreliable(reply: str, *, budget_max: float | None) -> bool:
    normalized = _normalize_text(reply)
    if re.findall(r"\b[a-zA-Z]{3,}\b", reply):
        return True
    if budget_max is None and ("любой бюджет" in normalized or "в любой бюджет" in normalized):
        return True
    if "не могу" in normalized and "однако" in normalized:
        return True
    return False


def build_assistant_reply(*, messages: list[Any], criteria: dict[str, Any], products: list[dict[str, Any]]) -> str:
    if not products or _should_prefer_grounded_reply():
        return build_grounded_assistant_reply(criteria=criteria, products=products)

    prompt = _build_consultant_prompt(messages=messages, criteria=criteria, products=products)
    try:
        reply = _call_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, json_mode=False, temperature=0.4).strip()
        if _reply_looks_unreliable(reply, budget_max=criteria.get("budget_max")):
            return build_grounded_assistant_reply(criteria=criteria, products=products)
        return reply
    except HTTPException:
        return build_grounded_assistant_reply(criteria=criteria, products=products)


def stream_assistant_reply(*, messages: list[Any], criteria: dict[str, Any], products: list[dict[str, Any]]) -> Iterable[str]:
    if not products or _should_prefer_grounded_reply():
        return iter([build_grounded_assistant_reply(criteria=criteria, products=products)])
    prompt = _build_consultant_prompt(messages=messages, criteria=criteria, products=products)
    try:
        return _stream_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, temperature=0.4)
    except HTTPException:
        return iter([build_grounded_assistant_reply(criteria=criteria, products=products)])


def assistant_health_check() -> dict[str, str]:
    prompt = [
        {"role": "system", "content": "Ответь одним словом ok."},
        {"role": "user", "content": "ping"},
    ]
    reply = _call_ollama(messages=prompt, model=OLLAMA_REPLY_MODEL, json_mode=False, temperature=0).strip()
    return {
        "status": "ok",
        "provider": "ollama",
        "model": OLLAMA_REPLY_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "reply": reply,
    }
