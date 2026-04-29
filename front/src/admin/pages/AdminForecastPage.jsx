import { useEffect, useState } from "react";
import "../admin.css";
import {
  adminForecastHealth,
  adminForecastList,
  adminForecastMetrics,
  adminForecastRetrain,
} from "../api/adminApi";

function formatMetric(value, digits = 2) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return num.toFixed(digits);
}

function formatPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num.toFixed(2)}%`;
}

export function AdminForecastPage() {
  const [days, setDays] = useState("30");
  const [testDays, setTestDays] = useState("30");
  const [safetyStock, setSafetyStock] = useState("0.15");

  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [forecastRows, setForecastRows] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingForecast, setIsRefreshingForecast] = useState(false);
  const [isRefreshingMetrics, setIsRefreshingMetrics] = useState(false);
  const [isRetraining, setIsRetraining] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState("");

  const loadHealth = async () => {
    const payload = await adminForecastHealth();
    setHealth(payload ?? null);
    return payload;
  };

  const loadMetrics = async (nextTestDays = testDays) => {
    setIsRefreshingMetrics(true);
    try {
      const payload = await adminForecastMetrics({ testDays: Number(nextTestDays) });
      setMetrics(payload ?? null);
      return payload;
    } finally {
      setIsRefreshingMetrics(false);
    }
  };

  const loadForecast = async (
    nextDays = days,
    nextSafetyStock = safetyStock,
    { silent = false } = {}
  ) => {
    if (!silent) {
      setIsRefreshingForecast(true);
    }
    try {
      const payload = await adminForecastList({
        days: Number(nextDays),
        safetyStock: Number(nextSafetyStock),
      });
      setForecastRows(Array.isArray(payload) ? payload : []);
      return payload;
    } finally {
      if (!silent) {
        setIsRefreshingForecast(false);
      }
    }
  };

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [healthPayload, metricsPayload, forecastPayload] = await Promise.all([
          adminForecastHealth(),
          adminForecastMetrics({ testDays: Number(testDays) }),
          adminForecastList({ days: Number(days), safetyStock: Number(safetyStock) }),
        ]);
        if (!isMounted) return;
        setHealth(healthPayload ?? null);
        setMetrics(metricsPayload ?? null);
        setForecastRows(Array.isArray(forecastPayload) ? forecastPayload : []);
      } catch (err) {
        if (!isMounted) return;
        setError(err?.message ?? "Не удалось загрузить данные прогноза XGBoost.");
      } finally {
        if (!isMounted) return;
        setIsLoading(false);
      }
    };

    bootstrap();

    return () => {
      isMounted = false;
    };
  }, []);

  const onRefreshForecast = async () => {
    setError(null);
    setSuccessMessage("");
    try {
      await loadForecast(days, safetyStock);
      await loadHealth();
    } catch (err) {
      setError(err?.message ?? "Не удалось обновить прогноз.");
    }
  };

  const onRefreshMetrics = async () => {
    setError(null);
    setSuccessMessage("");
    try {
      await loadMetrics(testDays);
      await loadHealth();
    } catch (err) {
      setError(err?.message ?? "Не удалось обновить метрики.");
    }
  };

  const onRetrain = async () => {
    setError(null);
    setSuccessMessage("");
    setIsRetraining(true);
    try {
      await adminForecastRetrain();
      await Promise.all([
        loadHealth(),
        loadMetrics(testDays),
        loadForecast(days, safetyStock, { silent: true }),
      ]);
      setSuccessMessage("Модель XGBoost успешно переобучена.");
    } catch (err) {
      setError(err?.message ?? "Не удалось переобучить модель XGBoost.");
    } finally {
      setIsRetraining(false);
    }
  };

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol12">
        <div className="adminSectionHeader">
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>Прогноз XGBoost</div>
            <div className="adminSectionText">
              Управление моделью спроса, метриками holdout и планом закупок прямо из админки.
            </div>
          </div>
          <button
            type="button"
            className="adminBtn adminBtnPrimary"
            onClick={onRetrain}
            disabled={isLoading || isRetraining}
          >
            {isRetraining ? "Переобучаем..." : "Переобучить модель"}
          </button>
        </div>

        {error ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeDanger">Ошибка</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : null}

        {successMessage ? (
          <div style={{ marginTop: 12 }}>
            <span className="adminBadge adminBadgeOk">Успех</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{successMessage}</span>
          </div>
        ) : null}
      </div>

      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Статус модели</div>
        <div className="adminMetricValue">
          {isLoading ? "..." : health?.model_loaded ? "Загружена" : "Отсутствует"}
        </div>
        <div className="adminHelp">Файл модели на сервере и готовность к прогнозу.</div>
      </div>

      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Горизонт прогноза</div>
        <div className="adminMetricValue">{isLoading ? "..." : Number(days) || 0}</div>
        <div className="adminHelp">Количество дней, которое показываем в админке.</div>
      </div>

      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Страховой запас</div>
        <div className="adminMetricValue">{isLoading ? "..." : formatPercent(Number(safetyStock) * 100)}</div>
        <div className="adminHelp">Запас, который добавляется к прогнозу закупки.</div>
      </div>

      <div className="adminCard adminCol5">
        <div className="adminSectionHeader">
          <div style={{ fontWeight: 700 }}>Метрики модели</div>
          <button
            type="button"
            className="adminBtn"
            onClick={onRefreshMetrics}
            disabled={isLoading || isRefreshingMetrics || isRetraining}
          >
            {isRefreshingMetrics ? "Обновляем..." : "Обновить метрики"}
          </button>
        </div>

        <div className="adminInlineControls">
          <div className="adminField" style={{ marginTop: 0 }}>
            <label htmlFor="forecast-test-days">Дней для теста</label>
            <input
              id="forecast-test-days"
              value={testDays}
              onChange={(e) => setTestDays(e.target.value)}
              inputMode="numeric"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="adminSectionText">Загрузка метрик...</div>
        ) : metrics ? (
          <div className="adminStatsList">
            <div className="adminStatsRow">
              <span>Всего строк</span>
              <strong>{metrics.rows}</strong>
            </div>
            <div className="adminStatsRow">
              <span>Строк для обучения</span>
              <strong>{metrics.train_rows}</strong>
            </div>
            <div className="adminStatsRow">
              <span>Строк для теста</span>
              <strong>{metrics.test_rows}</strong>
            </div>
            <div className="adminStatsRow">
              <span>MAE</span>
              <strong>{formatMetric(metrics.mae)}</strong>
            </div>
            <div className="adminStatsRow">
              <span>RMSE</span>
              <strong>{formatMetric(metrics.rmse)}</strong>
            </div>
            <div className="adminStatsRow">
              <span>MAPE</span>
              <strong>{formatPercent(metrics.mape_percent)}</strong>
            </div>
            <div className="adminStatsRow">
              <span>Accuracy</span>
              <strong>{formatPercent(metrics.accuracy)}</strong>
            </div>
          </div>
        ) : (
          <div className="adminSectionText">Метрики пока недоступны.</div>
        )}
      </div>

      <div className="adminCard adminCol7">
        <div className="adminSectionHeader">
          <div style={{ fontWeight: 700 }}>Планировщик прогноза</div>
          <button
            type="button"
            className="adminBtn"
            onClick={onRefreshForecast}
            disabled={isLoading || isRefreshingForecast || isRetraining}
          >
            {isRefreshingForecast ? "Обновляем..." : "Обновить прогноз"}
          </button>
        </div>

        <div className="adminInlineControls">
          <div className="adminField" style={{ marginTop: 0 }}>
            <label htmlFor="forecast-days">Дней</label>
            <input
              id="forecast-days"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              inputMode="numeric"
            />
          </div>
          <div className="adminField" style={{ marginTop: 0 }}>
            <label htmlFor="forecast-safety-stock">Страховой запас</label>
            <input
              id="forecast-safety-stock"
              value={safetyStock}
              onChange={(e) => setSafetyStock(e.target.value)}
              inputMode="decimal"
            />
          </div>
        </div>

        <div style={{ marginTop: 14, overflowX: "auto" }}>
          {isLoading ? (
            <div className="adminSectionText">Загрузка прогноза...</div>
          ) : (
            <table className="adminTable" aria-label="Таблица прогноза">
              <thead>
                <tr>
                  <th style={{ width: 180 }}>Дата</th>
                  <th style={{ width: 160 }}>Прогноз</th>
                  <th style={{ width: 180 }}>План закупки</th>
                </tr>
              </thead>
              <tbody>
                {forecastRows.map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.forecast}</td>
                    <td>{row.purchase_plan}</td>
                  </tr>
                ))}
                {forecastRows.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ color: "rgba(255,255,255,0.68)" }}>
                      Данные прогноза отсутствуют.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
