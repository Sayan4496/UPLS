import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Database, Globe2, RefreshCw, Users } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import StatCard from "../components/StatCard";
import { getAnalyticsDashboard, getParserCoverage } from "../services/api";

const severityColors = {
  INFO: "#60a5fa",
  LOW: "#60a5fa",
  DEBUG: "#94a3b8",
  MEDIUM: "#fbbf24",
  WARNING: "#fbbf24",
  HIGH: "#fb923c",
  ERROR: "#fb7185",
  CRITICAL: "#f43f5e",
  UNKNOWN: "#64748b"
};

const statusColors = {
  Healthy: "#34d399",
  Warning: "#fbbf24",
  Error: "#fb7185"
};

const formatNumber = (value) => Number(value || 0).toLocaleString();

const formatParserName = (value) => value
  ? value
  .replace("_parser", "")
  .replaceAll("_", " ")
  .replace(/\b\w/g, (letter) => letter.toUpperCase())
  : "Unknown parser";

const formatDate = (value) => value
  ? new Date(value).toLocaleDateString(
    undefined,
    {
      timeZone: "UTC",
      month: "short",
      day: "numeric"
    }
  )
  : "No date";

function Analytics() {
  const [dashboard, setDashboard] = useState(null);
  const [parserCoverage, setParserCoverage] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError("");
      const [dashboardData, parserData] = await Promise.all([
        getAnalyticsDashboard(),
        getParserCoverage()
      ]);
      setDashboard(dashboardData);
      setParserCoverage(parserData);
    } catch {
      setDashboard(null);
      setParserCoverage(null);
      setError("Analytics are unavailable until the events API responds.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(loadAnalytics, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const summary = dashboard?.summary || {};
  const volume = dashboard?.volume || [];
  const severity = dashboard?.severity || [];
  const sourceHealth = dashboard?.source_health || [];
  const totalLogs = summary.total_logs || 0;

  return (
    <div className="page analytics-page">
      <div className="page-header">
        <div><p className="eyebrow">Operational intelligence</p><h1>Log analytics</h1><p>Understand volume, severity, parser coverage, and source health at a glance.</p></div>
        <button className="secondary-button" onClick={loadAnalytics} disabled={loading}><RefreshCw size={16} /> Refresh</button>
      </div>

      {error && <div className="connection-error"><strong>Analytics unavailable</strong><p>{error}</p></div>}
      <section className="analytics-summary-grid" aria-label="Analytics summary">
        <StatCard title="Total logs" value={loading ? "..." : formatNumber(summary.total_logs)} icon={<Activity size={20} />} color="#60a5fa" trendText="all records" />
        <StatCard title="Alerts" value={loading ? "..." : formatNumber(summary.alerts)} icon={<AlertTriangle size={20} />} color="#fb7185" trendText="error and critical" />
        <StatCard title="Source types" value={loading ? "..." : formatNumber(summary.source_types)} icon={<Database size={20} />} color="#a78bfa" trendText="detected formats" />
        <StatCard title="Unique hosts" value={loading ? "..." : formatNumber(summary.unique_hosts)} icon={<Globe2 size={20} />} color="#34d399" trendText="source addresses" />
        <StatCard title="Unique users" value={loading ? "..." : formatNumber(summary.unique_users)} icon={<Users size={20} />} color="#fbbf24" trendText="identified users" />
        <StatCard title="Date range" value={loading ? "..." : `${formatDate(summary.date_start)} → ${formatDate(summary.date_end)}`} icon={<Activity size={20} />} color="#fb923c" trendText="event timestamps" />
      </section>

      <section className="analytics-chart-grid">
        <div className="panel analytics-chart-panel analytics-chart-wide">
          <div className="panel-header"><div><p className="eyebrow">Timeline</p><h2>Log volume over time</h2></div><span className="data-chip">{formatNumber(totalLogs)} logs</span></div>
          <div className="chart-wrap">
            {volume.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={volume}><defs><linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#60a5fa" stopOpacity={0.38} /><stop offset="100%" stopColor="#60a5fa" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid stroke="rgba(145,173,205,.12)" vertical={false} /><XAxis dataKey="date" tickFormatter={formatDate} tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={42} /><Tooltip contentStyle={{ background: "#142235", border: "1px solid #2d4460", borderRadius: 8, color: "#e5e7eb" }} labelFormatter={formatDate} /><Area type="monotone" dataKey="logs" stroke="#60a5fa" strokeWidth={2.5} fill="url(#volumeFill)" /></AreaChart></ResponsiveContainer> : <div className="chart-empty">No timestamped logs yet.</div>}
          </div>
        </div>

        <div className="panel analytics-chart-panel">
          <div className="panel-header"><div><p className="eyebrow">Classification</p><h2>Severity distribution</h2></div></div>
          <div className="chart-wrap chart-wrap-compact">
            {severity.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={severity} layout="vertical" margin={{ left: 8, right: 12 }}><XAxis type="number" hide /><YAxis type="category" dataKey="label" width={66} tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: "#142235", border: "1px solid #2d4460", borderRadius: 8, color: "#e5e7eb" }} formatter={(value) => [formatNumber(value), "logs"]} /><Bar dataKey="count" radius={[0, 4, 4, 0]}>{severity.map((row, index) => <Cell key={`${row.label}-${index}`} fill={severityColors[row.label] || severityColors.UNKNOWN} />)}</Bar></BarChart></ResponsiveContainer> : <div className="chart-empty">No severity data yet.</div>}
          </div>
        </div>
      </section>

      <section className="analytics-chart-grid">
        <div className="panel analytics-chart-panel">
          <div className="panel-header"><div><p className="eyebrow">Parsing</p><h2>Parser coverage</h2></div><span className="data-chip">{formatNumber(parserCoverage?.total_events)} logs</span></div>
          <div className="coverage-list">{parserCoverage?.coverage?.length ? parserCoverage.coverage.map((row) => <div className="coverage-row" key={`${row.parser_used}-${row.source_format}`}><div className="coverage-label"><strong>{formatParserName(row.parser_used)}</strong><span>{row.percentage}%</span></div><div className="severity-track"><span style={{ width: `${row.percentage}%`, background: row.fallback_used ? "#fbbf24" : "#60a5fa" }} /></div></div>) : <div className="chart-empty">No parser data yet.</div>}</div>
        </div>

        <div className="panel analytics-chart-panel">
          <div className="panel-header"><div><p className="eyebrow">Reliability</p><h2>Source health</h2></div></div>
          <div className="health-list">{sourceHealth.length ? sourceHealth.map((row) => <div className="health-row" key={row.source}><div className="health-source"><strong>{row.source}</strong><span>{formatNumber(row.logs)} logs</span></div><div className="health-status" style={{ color: statusColors[row.status] || statusColors.Healthy }}><span className="health-dot" style={{ background: statusColors[row.status] || statusColors.Healthy }} />{row.status}</div></div>) : <div className="chart-empty">No source data yet.</div>}</div>
        </div>
      </section>

      <section className="panel analytics-chart-panel">
        <div className="panel-header"><div><p className="eyebrow">Reliability trend</p><h2>Error rate over time</h2></div><span className="data-chip">errors ÷ total logs</span></div>
        <div className="chart-wrap chart-wrap-error">
          {volume.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={volume}><CartesianGrid stroke="rgba(145,173,205,.12)" vertical={false} /><XAxis dataKey="date" tickFormatter={formatDate} tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis unit="%" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={42} /><Tooltip contentStyle={{ background: "#142235", border: "1px solid #2d4460", borderRadius: 8, color: "#e5e7eb" }} labelFormatter={formatDate} formatter={(value) => [`${value}%`, "error rate"]} /><Line type="monotone" dataKey="error_rate" stroke="#fb7185" strokeWidth={2.5} dot={{ fill: "#fb7185", r: 3 }} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer> : <div className="chart-empty">No error-rate data yet.</div>}
        </div>
      </section>
    </div>
  );
}

export default Analytics;
