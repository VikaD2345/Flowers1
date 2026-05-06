from __future__ import annotations

import math
import random
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
OUTPUT_PATH = PROJECT_ROOT / "synthetic_orders.csv"

CATEGORIES = [
    ("Розы", 0.30, 2450.0),
    ("Сборные букеты", 0.24, 2750.0),
    ("Тюльпаны", 0.18, 1650.0),
    ("Хризантемы", 0.12, 1450.0),
    ("Композиции", 0.09, 3300.0),
    ("Пионы", 0.07, 3600.0),
]
BUYER_NAMES = [
    "Ольга Козлова",
    "Мария Морозова",
    "Алина Соколова",
    "Дарья Соколова",
    "Полина Попова",
    "Елена Новикова",
    "Анна Иванова",
    "Ирина Волкова",
    "Наталья Смирнова",
    "Ксения Федорова",
]
PAYMENT_METHODS = ["card", "sbp", "cash"]


def _holiday_boost(date: pd.Timestamp) -> float:
    def proximity(month: int, day: int, width: float) -> float:
        current = date.normalize()
        candidates = [
            pd.Timestamp(year=date.year - 1, month=month, day=day),
            pd.Timestamp(year=date.year, month=month, day=day),
            pd.Timestamp(year=date.year + 1, month=month, day=day),
        ]
        distance = min(abs((current - candidate).days) for candidate in candidates)
        return math.exp(-((distance / width) ** 2))

    return (
        10.0 * proximity(2, 14, 4.0)
        + 18.0 * proximity(3, 8, 5.0)
        + 12.0 * proximity(12, 31, 7.0)
    )


def _daily_demand(date: pd.Timestamp, rng: random.Random) -> int:
    doy = date.dayofyear
    dow = date.dayofweek
    year_index = date.year - 2024

    annual = 4.0 * math.sin(2.0 * math.pi * (doy - 35) / 365.25)
    weekly = [1.5, 0.5, 0.0, 0.8, 2.0, 3.5, 2.8][dow]
    payday = 1.6 if date.day <= 5 or 20 <= date.day <= 25 else 0.0
    trend = 1.2 * year_index
    noise = rng.gauss(0.0, 1.1)

    demand = 30.0 + annual + weekly + payday + trend + _holiday_boost(date) + noise
    return max(8, int(round(demand)))


def _category_weights(date: pd.Timestamp) -> list[float]:
    weights = [weight for _, weight, _ in CATEGORIES]
    if date.month == 3 and 1 <= date.day <= 12:
        weights[2] += 0.08
        weights[0] += 0.04
    if date.month == 2 and 10 <= date.day <= 16:
        weights[0] += 0.10
    if date.month == 12 and date.day >= 20:
        weights[1] += 0.05
        weights[4] += 0.04

    total = sum(weights)
    return [weight / total for weight in weights]


def _allocate_categories(total_quantity: int, weights: list[float]) -> list[int]:
    raw = [total_quantity * weight for weight in weights]
    counts = [int(math.floor(value)) for value in raw]
    remainder = total_quantity - sum(counts)
    order = sorted(range(len(raw)), key=lambda index: raw[index] - counts[index], reverse=True)
    for index in order[:remainder]:
        counts[index] += 1
    return counts


def generate_orders() -> pd.DataFrame:
    rng = random.Random(42)
    rows: list[dict[str, object]] = []
    order_id = 100001

    for date in pd.date_range("2024-01-01", "2025-12-31", freq="D"):
        daily_total = _daily_demand(date, rng)
        category_counts = _allocate_categories(daily_total, _category_weights(date))

        for (category, _, base_price), category_total in zip(CATEGORIES, category_counts):
            remaining = category_total
            while remaining > 0:
                quantity = min(remaining, rng.choices([1, 2, 3], weights=[0.72, 0.23, 0.05], k=1)[0])
                remaining -= quantity

                discount = max(0.0, min(0.22, rng.gauss(0.07, 0.025)))
                if date.day <= 5 or 20 <= date.day <= 25:
                    discount += 0.015
                status = rng.choices(["completed", "pending", "cancelled"], weights=[0.91, 0.06, 0.03], k=1)[0]

                rows.append(
                    {
                        "order_id": order_id,
                        "order_date": date.date().isoformat(),
                        "quantity": quantity,
                        "category": category,
                        "status": status,
                        "unit_price": round(base_price * rng.uniform(0.92, 1.08), 2),
                        "discount_pct": round(discount, 4),
                        "stock_left": max(4, int(round(44 - daily_total * 0.55 + rng.gauss(0.0, 3.0)))),
                        "buyer_name": rng.choice(BUYER_NAMES),
                        "is_vip": int(rng.random() < 0.16),
                        "payment_method": rng.choice(PAYMENT_METHODS),
                    }
                )
                order_id += 1

    return pd.DataFrame(rows)


def main() -> None:
    df = generate_orders()
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    daily = df.groupby("order_date")["quantity"].sum()
    print(f"Rows: {len(df)}")
    print(f"Date range: {daily.index.min()} -> {daily.index.max()}")
    print(f"Daily demand: min={daily.min()}, mean={daily.mean():.2f}, max={daily.max()}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
