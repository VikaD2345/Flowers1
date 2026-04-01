from __future__ import annotations

from forecast_service import DATA_PATH, MODEL_PATH, build_daily_demand, train_and_save_model


def main() -> None:
    history = build_daily_demand(DATA_PATH)
    train_and_save_model(csv_path=DATA_PATH, model_path=MODEL_PATH)
    print(f"Training rows: {len(history)}")
    print(f"Date range: {history['ds'].min().date()} -> {history['ds'].max().date()}")
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
