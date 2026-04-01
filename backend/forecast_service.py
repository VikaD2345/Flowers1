from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_PATH = (
    PROJECT_ROOT / "synthetic_orders.csv"
    if (PROJECT_ROOT / "synthetic_orders.csv").exists()
    else BACKEND_DIR / "synthetic_orders.csv"
)
MODEL_PATH = BACKEND_DIR / "xgboost_model.joblib"
LAGS = (1, 7, 14, 28)
ROLL_WINDOWS = (7, 14)


@dataclass
class ForecastRow:
    date: str
    forecast: int
    purchase_plan: int


def _load_orders(csv_path: Path = DATA_PATH) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Synthetic orders file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_columns = {"order_id", "order_date", "quantity", "category", "status"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"synthetic_orders.csv is missing columns: {sorted(missing)}")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    if "unit_price" in df.columns:
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    if "discount_pct" in df.columns:
        df["discount_pct"] = pd.to_numeric(df["discount_pct"], errors="coerce").fillna(0)
    if "stock_left" in df.columns:
        df["stock_left"] = pd.to_numeric(df["stock_left"], errors="coerce").fillna(0)
    if "is_vip" in df.columns:
        df["is_vip"] = pd.to_numeric(df["is_vip"], errors="coerce").fillna(0)
    df = df.dropna(subset=["order_date"])
    return df


def build_daily_demand(csv_path: Path = DATA_PATH) -> pd.DataFrame:
    df = _load_orders(csv_path)
    daily = (
        df.groupby(df["order_date"].dt.normalize(), as_index=False)["quantity"]
        .sum()
        .rename(columns={"order_date": "ds", "quantity": "y"})
        .sort_values("ds")
    )
    daily["ds"] = pd.to_datetime(daily["ds"])
    daily["y"] = daily["y"].astype(float)
    return daily


def _build_category_profiles(csv_path: Path = DATA_PATH) -> dict[str, dict[str, float]]:
    df = _load_orders(csv_path).copy()
    df["category"] = df["category"].fillna("unknown").astype(str)
    if "unit_price" not in df.columns:
        df["unit_price"] = 0.0
    if "discount_pct" not in df.columns:
        df["discount_pct"] = 0.0
    if "stock_left" not in df.columns:
        df["stock_left"] = 0.0
    if "is_vip" not in df.columns:
        df["is_vip"] = 0.0

    profiles: dict[str, dict[str, float]] = {}
    for category, part in df.groupby("category"):
        profiles[str(category)] = {
            "avg_price": float(part["unit_price"].mean()),
            "avg_discount": float(part["discount_pct"].mean()),
            "avg_stock": float(part["stock_left"].mean()),
            "vip_rate": float(part["is_vip"].mean()),
            "avg_qty": float(part["quantity"].mean()),
        }
    return profiles


def _build_category_profiles_until(csv_path: Path, end_date: pd.Timestamp) -> dict[str, dict[str, float]]:
    df = _load_orders(csv_path).copy()
    df = df[df["order_date"] <= end_date].copy()
    if df.empty:
        return {}
    df["category"] = df["category"].fillna("unknown").astype(str)
    if "unit_price" not in df.columns:
        df["unit_price"] = 0.0
    if "discount_pct" not in df.columns:
        df["discount_pct"] = 0.0
    if "stock_left" not in df.columns:
        df["stock_left"] = 0.0
    if "is_vip" not in df.columns:
        df["is_vip"] = 0.0
    profiles: dict[str, dict[str, float]] = {}
    for category, part in df.groupby("category"):
        profiles[str(category)] = {
            "avg_price": float(part["unit_price"].mean()),
            "avg_discount": float(part["discount_pct"].mean()),
            "avg_stock": float(part["stock_left"].mean()),
            "vip_rate": float(part["is_vip"].mean()),
            "avg_qty": float(part["quantity"].mean()),
        }
    return profiles


def _build_daily_demand_by_category(csv_path: Path = DATA_PATH) -> dict[str, pd.DataFrame]:
    df = _load_orders(csv_path).copy()
    df["category"] = df["category"].fillna("unknown").astype(str)
    grouped = (
        df.groupby([df["order_date"].dt.normalize(), "category"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"order_date": "ds", "quantity": "y"})
    )
    if grouped.empty:
        return {}

    min_ds = pd.to_datetime(grouped["ds"]).min()
    max_ds = pd.to_datetime(grouped["ds"]).max()
    full_dates = pd.date_range(min_ds, max_ds, freq="D")

    result: dict[str, pd.DataFrame] = {}
    for category, part in grouped.groupby("category"):
        by_day = part.set_index("ds").sort_index()[["y"]]
        by_day.index = pd.to_datetime(by_day.index)
        # Keep continuous daily history per category.
        by_day = by_day.reindex(full_dates, fill_value=0.0)
        out = by_day.reset_index().rename(columns={"index": "ds"})
        out["y"] = out["y"].astype(float)
        result[str(category)] = out
    return result


def _clip_outliers_iqr(daily: pd.DataFrame) -> pd.DataFrame:
    cleaned = daily.copy()
    q1 = cleaned["y"].quantile(0.25)
    q3 = cleaned["y"].quantile(0.75)
    iqr = q3 - q1
    if not np.isfinite(iqr) or iqr <= 0:
        return cleaned

    lower = max(0.0, float(q1 - 1.5 * iqr))
    upper = float(q3 + 1.5 * iqr)
    cleaned["y"] = cleaned["y"].clip(lower=lower, upper=upper)
    return cleaned


def _build_xgb_model() -> XGBRegressor:
    return XGBRegressor(objective="reg:squarederror", random_state=42)


def _date_features(ts: pd.Timestamp) -> dict[str, float]:
    month = float(ts.month)
    day_of_year = float(ts.dayofyear)
    day_of_week = float(ts.dayofweek)
    is_weekend = float(day_of_week >= 5)
    # Seasonal peaks often correlate with fixed dates/periods.
    is_valentine = float(ts.month == 2 and ts.day == 14)
    is_womens_day = float(ts.month == 3 and ts.day == 8)
    is_new_year_period = float((ts.month == 12 and ts.day >= 25) or (ts.month == 1 and ts.day <= 8))
    return {
        "is_weekend": is_weekend,
        "month_sin": float(np.sin(2.0 * np.pi * month / 12.0)),
        "month_cos": float(np.cos(2.0 * np.pi * month / 12.0)),
        "doy_sin": float(np.sin(2.0 * np.pi * day_of_year / 365.25)),
        "doy_cos": float(np.cos(2.0 * np.pi * day_of_year / 365.25)),
        "dow_sin": float(np.sin(2.0 * np.pi * day_of_week / 7.0)),
        "dow_cos": float(np.cos(2.0 * np.pi * day_of_week / 7.0)),
        "is_valentine": is_valentine,
        "is_womens_day": is_womens_day,
        "is_new_year_period": is_new_year_period,
    }


def _build_feature_row(ts: pd.Timestamp, history: list[float], context: dict[str, float] | None = None) -> dict[str, float]:
    row = _date_features(ts)
    for lag in LAGS:
        row[f"lag_{lag}"] = float(history[-lag])
    for window in ROLL_WINDOWS:
        row[f"roll_mean_{window}"] = float(np.mean(history[-window:]))
    if context:
        row["ctx_avg_price"] = float(context.get("avg_price", 0.0))
        row["ctx_avg_discount"] = float(context.get("avg_discount", 0.0))
        row["ctx_avg_stock"] = float(context.get("avg_stock", 0.0))
        row["ctx_vip_rate"] = float(context.get("vip_rate", 0.0))
        row["ctx_avg_qty"] = float(context.get("avg_qty", 0.0))
    return row


def _build_supervised_frame(
    daily: pd.DataFrame,
    context: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    max_back = max(max(LAGS), max(ROLL_WINDOWS))
    records: list[dict[str, float]] = []

    y_values = daily["y"].astype(float).tolist()
    ds_values = pd.to_datetime(daily["ds"]).tolist()
    for i in range(max_back, len(daily)):
        history = y_values[:i]
        row = _build_feature_row(pd.Timestamp(ds_values[i]), history, context)
        row["y"] = float(y_values[i])
        records.append(row)

    if not records:
        raise ValueError("Not enough history to create supervised training dataset.")

    frame = pd.DataFrame(records)
    feature_columns = [col for col in frame.columns if col != "y"]
    return frame, feature_columns


def _fit_xgb_artifact(daily: pd.DataFrame, context: dict[str, float] | None = None) -> dict:
    frame, feature_columns = _build_supervised_frame(daily, context)
    n = len(frame)
    if n < 40:
        # Fallback for tiny datasets where tuning split is unstable.
        model = _build_xgb_model()
        model.set_params(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
        )
        model.fit(frame[feature_columns], frame["y"])
        best_params = model.get_params()
    else:
        val_size = max(14, min(45, n // 5))
        train_frame = frame.iloc[:-val_size].copy()
        val_frame = frame.iloc[-val_size:].copy()

        candidates = [
            {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9},
            {"n_estimators": 500, "max_depth": 5, "learning_rate": 0.04, "subsample": 0.9, "colsample_bytree": 0.85},
            {"n_estimators": 700, "max_depth": 6, "learning_rate": 0.03, "subsample": 0.85, "colsample_bytree": 0.9},
            {"n_estimators": 450, "max_depth": 4, "learning_rate": 0.06, "subsample": 1.0, "colsample_bytree": 0.9},
        ]

        best_score = float("inf")
        best_params = candidates[0]
        for params in candidates:
            candidate_model = _build_xgb_model()
            candidate_model.set_params(**params)
            candidate_model.fit(train_frame[feature_columns], train_frame["y"])

            y_true = val_frame["y"].astype(float).to_numpy()
            y_pred = np.clip(
                candidate_model.predict(val_frame[feature_columns]).astype(float),
                0,
                None,
            )
            denom = np.where(y_true == 0, np.nan, y_true)
            mape = float(np.nanmean(np.abs((y_true - y_pred) / denom)) * 100.0)
            if np.isfinite(mape) and mape < best_score:
                best_score = mape
                best_params = params

        model = _build_xgb_model()
        model.set_params(**best_params)
        model.fit(frame[feature_columns], frame["y"])

    return {
        "kind": "xgb",
        "model": model,
        "feature_columns": feature_columns,
        "best_params": best_params,
        "context": context or {},
        "history_ds": [pd.Timestamp(ds).date().isoformat() for ds in pd.to_datetime(daily["ds"]).tolist()],
        "history_y": [float(v) for v in daily["y"].astype(float).tolist()],
    }


def _fit_single_series_artifact(daily: pd.DataFrame, context: dict[str, float] | None = None) -> dict:
    cleaned = _clip_outliers_iqr(daily)
    if len(cleaned) >= max(max(LAGS), max(ROLL_WINDOWS)) + 12:
        return _fit_xgb_artifact(cleaned, context)

    history_ds = [pd.Timestamp(ds).date().isoformat() for ds in pd.to_datetime(cleaned["ds"]).tolist()]
    history_y = [float(v) for v in cleaned["y"].astype(float).tolist()]
    baseline = float(np.mean(history_y)) if history_y else 0.0
    return {
        "kind": "naive",
        "baseline": baseline,
        "context": context or {},
        "history_ds": history_ds,
        "history_y": history_y,
    }


def _predict_series_range(
    artifact: dict,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, float]:
    if end_date < start_date:
        return {}

    history_y: list[float] = [float(v) for v in artifact.get("history_y", [])]
    history_ds = pd.to_datetime(artifact.get("history_ds", []))
    if len(history_y) == 0:
        return {}

    kind = artifact.get("kind", "naive")
    context: dict[str, float] = artifact.get("context", {})
    generated: dict[str, float] = {}

    if kind == "naive":
        value = max(0.0, float(artifact.get("baseline", float(np.mean(history_y)))))
        current_date = start_date
        while current_date <= end_date:
            generated[current_date.date().isoformat()] = value
            current_date += pd.Timedelta(days=1)
        return generated

    model: XGBRegressor = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]
    min_back = max(max(LAGS), max(ROLL_WINDOWS))
    if len(history_y) < min_back:
        value = max(0.0, float(np.mean(history_y)))
        current_date = start_date
        while current_date <= end_date:
            generated[current_date.date().isoformat()] = value
            current_date += pd.Timedelta(days=1)
        return generated

    last_date = pd.Timestamp(history_ds[-1]).normalize()
    current_date = last_date + pd.Timedelta(days=1)
    while current_date <= end_date:
        row = _build_feature_row(current_date, history_y, context)
        x = pd.DataFrame([row])[feature_columns]
        yhat = max(0.0, float(model.predict(x)[0]))
        history_y.append(yhat)
        if current_date >= start_date:
            generated[current_date.date().isoformat()] = yhat
        current_date += pd.Timedelta(days=1)
    return generated


def _mape_percent(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.where(y_true == 0, np.nan, y_true)
    return float(np.nanmean(np.abs((y_true - y_pred) / denom)) * 100.0)


def _aggregate_category_predictions(
    categories: dict[str, dict],
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, float]:
    summed: dict[str, float] = {}
    for category_artifact in categories.values():
        history_ds = pd.to_datetime(category_artifact.get("history_ds", []))
        if len(history_ds) == 0:
            continue
        series_end = max(end_date, pd.Timestamp(history_ds[-1]).normalize())
        series_pred = _predict_series_range(category_artifact, start_date=start_date, end_date=series_end)
        for ds, val in series_pred.items():
            if ds >= start_date.date().isoformat() and ds <= end_date.date().isoformat():
                summed[ds] = summed.get(ds, 0.0) + float(val)
    return summed


def train_and_save_model(
    *,
    csv_path: Path = DATA_PATH,
    model_path: Path = MODEL_PATH,
) -> Path:
    total_history = _clip_outliers_iqr(build_daily_demand(csv_path))
    by_category = _build_daily_demand_by_category(csv_path)
    category_profiles = _build_category_profiles(csv_path)

    val_days = int(min(30, max(14, len(total_history) // 6)))
    train_total = total_history.iloc[:-val_days].copy()
    val_total = total_history.iloc[-val_days:].copy()
    val_start = pd.Timestamp(val_total.iloc[0]["ds"]).normalize()
    val_end = pd.Timestamp(val_total.iloc[-1]["ds"]).normalize()
    train_end = val_start - pd.Timedelta(days=1)
    y_true = val_total["y"].astype(float).to_numpy()
    val_keys = [pd.Timestamp(ds).date().isoformat() for ds in pd.to_datetime(val_total["ds"]).tolist()]

    # Evaluate global strategy
    fallback_for_val = _fit_single_series_artifact(train_total, context={"avg_qty": float(train_total["y"].mean())})
    global_pred_map = _predict_series_range(fallback_for_val, start_date=val_start, end_date=val_end)
    yhat_global = np.array([global_pred_map.get(k, 0.0) for k in val_keys], dtype=float)
    mape_global = _mape_percent(y_true, yhat_global)

    # Evaluate category strategy
    categories_for_val: dict[str, dict] = {}
    for category, series in by_category.items():
        train_series = series[series["ds"] <= train_end].copy()
        if not train_series.empty:
            categories_for_val[category] = _fit_single_series_artifact(
                train_series,
                context=category_profiles.get(category, {}),
            )
    category_pred_map = _aggregate_category_predictions(categories_for_val, start_date=val_start, end_date=val_end)
    yhat_category = np.array([category_pred_map.get(k, 0.0) for k in val_keys], dtype=float)
    mape_category = _mape_percent(y_true, yhat_category)
    strategy = "global" if mape_global <= mape_category else "category"

    fallback = _fit_single_series_artifact(total_history, context={"avg_qty": float(total_history["y"].mean())})
    category_artifacts = {
        category: _fit_single_series_artifact(series, context=category_profiles.get(category, {}))
        for category, series in by_category.items()
    }

    artifact = {
        "kind": "multi_category",
        "strategy": strategy,
        "validation_mape_global": mape_global,
        "validation_mape_category": mape_category,
        "categories": category_artifacts,
        "fallback": fallback,
    }
    joblib.dump(artifact, model_path)
    return model_path


def load_model(model_path: Path = MODEL_PATH) -> dict:
    if not model_path.exists():
        raise FileNotFoundError(f"Forecast model not found: {model_path}")
    return joblib.load(model_path)


def ensure_model(model_path: Path = MODEL_PATH, csv_path: Path = DATA_PATH) -> dict:
    if not model_path.exists():
        train_and_save_model(csv_path=csv_path, model_path=model_path)
    return load_model(model_path)


def forecast_demand(
    *,
    days: int = 30,
    safety_stock: float = 0.15,
    model_path: Path = MODEL_PATH,
    csv_path: Path = DATA_PATH,
) -> list[ForecastRow]:
    if days < 1:
        raise ValueError("days must be >= 1")
    if safety_stock < 0:
        raise ValueError("safety_stock must be >= 0")

    artifact = ensure_model(model_path=model_path, csv_path=csv_path)
    if artifact.get("kind") != "multi_category":
        # Backward compatibility with older single-series model files.
        artifact = {"kind": "multi_category", "categories": {"_all_": artifact}, "fallback": artifact}

    start_date = pd.Timestamp.now().normalize()
    target_end = start_date + pd.Timedelta(days=days - 1)
    categories: dict[str, dict] = artifact.get("categories", {})
    if not categories:
        categories = {"_fallback_": artifact["fallback"]}
    strategy = artifact.get("strategy", "global")

    if strategy == "category":
        daily_sum = _aggregate_category_predictions(categories, start_date=start_date, end_date=target_end)
    else:
        daily_sum = _predict_series_range(artifact["fallback"], start_date=start_date, end_date=target_end)

    rows: list[ForecastRow] = []
    for offset in range(days):
        ds = (start_date + pd.Timedelta(days=offset)).date().isoformat()
        demand = max(0, int(round(daily_sum.get(ds, 0.0))))
        purchase_plan = max(demand, int(round(demand * (1 + safety_stock))))
        rows.append(
            ForecastRow(
                date=ds,
                forecast=demand,
                purchase_plan=purchase_plan,
            )
        )
    return rows


def model_health(model_path: Path = MODEL_PATH) -> dict[str, bool]:
    return {"model_loaded": model_path.exists()}


def evaluate_holdout_metrics(
    *,
    csv_path: Path = DATA_PATH,
    test_days: int = 30,
) -> dict[str, float | int]:
    if test_days < 1:
        raise ValueError("test_days must be >= 1")

    daily = _clip_outliers_iqr(build_daily_demand(csv_path))
    if len(daily) < 8:
        raise ValueError("Not enough history rows to evaluate (need at least 8 days).")

    test_days = int(min(test_days, max(1, len(daily) // 2)))
    test = daily.iloc[-test_days:].copy()
    train_end = pd.Timestamp(test["ds"].min()) - pd.Timedelta(days=1)

    # Global strategy on holdout split
    train_total = daily[daily["ds"] <= train_end].copy()
    global_artifact = _fit_single_series_artifact(train_total, context={"avg_qty": float(train_total["y"].mean())})
    test_start = pd.Timestamp(test["ds"].min()).normalize()
    test_end = pd.Timestamp(test["ds"].max()).normalize()
    test_keys = [pd.Timestamp(ds).date().isoformat() for ds in pd.to_datetime(test["ds"]).tolist()]
    global_pred_map = _predict_series_range(global_artifact, start_date=test_start, end_date=test_end)
    yhat_global = np.array([global_pred_map.get(k, 0.0) for k in test_keys], dtype=float)

    # Category strategy on holdout split
    by_category = _build_daily_demand_by_category(csv_path)
    split_profiles = _build_category_profiles_until(csv_path, train_end)
    split_categories: dict[str, dict] = {}
    for category, series in by_category.items():
        train_series = series[series["ds"] <= train_end].copy()
        if not train_series.empty:
            split_categories[category] = _fit_single_series_artifact(
                train_series,
                context=split_profiles.get(category, {}),
            )
    category_pred_map = _aggregate_category_predictions(split_categories, start_date=test_start, end_date=test_end)
    yhat_category = np.array([category_pred_map.get(k, 0.0) for k in test_keys], dtype=float)

    y = test["y"].astype(float).to_numpy()
    mape_global = _mape_percent(y, yhat_global)
    mape_category = _mape_percent(y, yhat_category)
    yhat = yhat_global if mape_global <= mape_category else yhat_category

    mae = float(np.mean(np.abs(y - yhat)))
    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))

    mape = _mape_percent(y, yhat)
    accuracy = float(max(0.0, 1.0 - (mape / 100.0)))

    return {
        "rows": int(len(daily)),
        "train_rows": int(len(daily) - test_days),
        "test_rows": int(len(test)),
        "test_days": int(test_days),
        "mae": mae,
        "rmse": rmse,
        "mape_percent": mape,
        "accuracy": accuracy,
    }
