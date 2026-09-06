import { useEffect, useState } from "react";
import { Activity, AlertTriangle, BarChart3, CheckCircle2, RefreshCw } from "lucide-react";

import StatCard from "../components/StatCard";
import { getEventStats } from "../services/api";

function Analytics() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError("");
      setStats(await getEventStats());
    } catch {
      setStats(null);
      setError("Analytics are unavailable until the events API responds.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(loadStats, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const total = stats?.total_events || 0;
  const severityRows = [
    { label: "HIGH", value: stats?.high_severity || 0, color: "#fb7185" },
    { label: "MEDIUM", value: stats?.medium_severity || 0, color: "#fbbf24" },
    { label: "LOW", value: stats?.low_severity || 0, color: "#34d399" }
  ];

  return (
    <div className="page analytics-page">
      <div className="page-header">
        <div><p className="eyebrow">Evidence, not estimates</p><h1>Security analytics</h1><p>Severity distribution calculated from the normalized event store.</p></div>
        <button className="secondary-button" onClick={loadStats} disabled={loading}><RefreshCw size={16} /> Refresh</button>
      </div>

      {error && <div className="connection-error"><strong>Analytics unavailable</strong><p>{error}</p></div>}
      <section className="stats-grid" aria-label="Severity totals">
        <StatCard title="All events" value={loading ? "..." : total} icon={<Activity size={20} />} color="#60a5fa" trendText="from normalized_events" />
        <StatCard title="High severity" value={loading ? "..." : stats?.high_severity || 0} icon={<AlertTriangle size={20} />} color="#fb7185" trendText="severity HIGH" />
        <StatCard title="Medium severity" value={loading ? "..." : stats?.medium_severity || 0} icon={<BarChart3 size={20} />} color="#fbbf24" trendText="severity MEDIUM" />
        <StatCard title="Low severity" value={loading ? "..." : stats?.low_severity || 0} icon={<CheckCircle2 size={20} />} color="#34d399" trendText="severity LOW" />
      </section>

      <section className="panel analytics-breakdown">
        <div className="panel-header"><div><p className="eyebrow">Distribution</p><h2>Severity breakdown</h2></div><span className="data-chip">{total} total records</span></div>
        {stats ? severityRows.map((row) => {
          const percentage = total ? Math.round((row.value / total) * 100) : 0;
          return <div className="severity-row" key={row.label}><div className="severity-row-label"><strong>{row.label}</strong><span>{row.value} events · {percentage}%</span></div><div className="severity-track"><span style={{ width: `${percentage}%`, background: row.color }} /></div></div>;
        }) : <div className="empty-state"><BarChart3 size={24} /><h3>No analytics data</h3><p>Connect the backend and ingest events to see the breakdown.</p></div>}
      </section>
    </div>
  );
}

export default Analytics;
