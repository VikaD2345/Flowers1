import { useEffect, useMemo, useState } from "react";
import "../admin.css";
import { adminListOrders } from "../api/adminApi";

function calcOrderTotal(order) {
  if (!order?.items?.length) return 0;
  return order.items.reduce((sum, it) => sum + Number(it.unit_price) * Number(it.qty), 0);
}

export function AdminDashboardPage() {
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminListOrders()
      .then((rows) => {
        if (!isMounted) return;
        setOrders(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err?.message ?? "Не удалось загрузить данные панели.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const metrics = useMemo(() => {
    const totals = orders.map(calcOrderTotal);
    const revenue = totals.reduce((a, b) => a + b, 0);
    const avg = totals.length ? revenue / totals.length : 0;
    const newCount = orders.filter((o) => o.status === "new").length;
    const deliveringCount = orders.filter((o) => o.status === "delivering").length;
    const doneCount = orders.filter((o) => o.status === "done").length;
    const canceledCount = orders.filter((o) => o.status === "canceled").length;

    return {
      revenue,
      avg,
      count: orders.length,
      newCount,
      deliveringCount,
      doneCount,
      canceledCount,
    };
  }, [orders]);

  return (
    <div className="adminGrid">
      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Выручка</div>
        <div className="adminMetricValue">
          {isLoading ? "..." : metrics.revenue.toFixed(2)}
        </div>
      </div>
      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Всего заказов</div>
        <div className="adminMetricValue">{isLoading ? "..." : metrics.count}</div>
      </div>
      <div className="adminCard adminCol4">
        <div className="adminMetricLabel">Средний чек</div>
        <div className="adminMetricValue">{isLoading ? "..." : metrics.avg.toFixed(2)}</div>
      </div>

      <div className="adminCard adminCol12">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Воронка заказов</div>
        {error ? (
          <div>
            <span className="adminBadge adminBadgeDanger">Ошибка</span>{" "}
            <span style={{ color: "rgba(255,255,255,0.78)" }}>{error}</span>
          </div>
        ) : (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <span className="adminBadge adminBadgeWarn">СОЗДАН: {metrics.newCount}</span>
            <span className="adminBadge">ДОСТАВЛЯЕТСЯ: {metrics.deliveringCount}</span>
            <span className="adminBadge adminBadgeOk">ЗАВЕРШЕН: {metrics.doneCount}</span>
            <span className="adminBadge adminBadgeDanger">ОТМЕНЕН: {metrics.canceledCount}</span>
          </div>
        )}

        <div style={{ marginTop: 12, color: "rgba(255,255,255,0.68)", lineHeight: 1.5 }}>
          Эта панель рассчитывается на основе текущего ответа `/admin/orders`
          и пока не использует отдельные серверные метрики.
        </div>
      </div>
    </div>
  );
}
