import { useEffect, useState } from "react";
import { Activity, ArrowUpRight, Ban, Clock3, Database, ShieldAlert, UploadCloud } from "lucide-react";

import EventsTable from "../components/EventsTable";
import StatCard from "../components/StatCard";
import { checkBackendHealth, getDashboardData } from "../services/api";

const emptyData = { totalEvents: 0, highSeverity: 0, blockedEvents: 0, activeSources: 0, events: [] };

function Dashboard() {
  const [data, setData] = useState(emptyData);
  const [status, setStatus] = useState({ loading: true, connected: false, error: "" });

  const loadDashboard = async () => {
    setStatus({ loading: true, connected: false, error: "" });
    try {
      const [dashboard, health] = await Promise.all([getDashboardData(), checkBackendHealth()]);
      setData(dashboard);
      setStatus({ loading: false, connected: health.connected, error: health.connected ? "" : "Database health check failed." });
    } catch {
      setData(emptyData);
      setStatus({ loading: false, connected: false, error: "The API is unavailable. Connect the backend to load live events." });
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(loadDashboard, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="page dashboard-page">
      <div className="page-header dashboard-header">
        <div>
          <p className="eyebrow">Operations overview</p>
          <h1>Security command center</h1>
          <p>Live visibility into normalized events and connected log sources.</p>
        </div>
        <button className="primary-button" onClick={loadDashboard} disabled={status.loading}>
          <Activity size={17} /> {status.loading ? "Refreshing..." : "Refresh data"}
        </button>
      </div>

      {!status.loading && status.error && <div className="connection-error"><strong>Live data unavailable</strong><p>{status.error}</p></div>}

      <section className="stats-grid" aria-label="Live event summary">
        <StatCard title="Total events" value={data.totalEvents} icon={<Activity size={20} />} color="#60a5fa" trendText="from the event store" />
        <StatCard title="High severity" value={data.highSeverity} icon={<ShieldAlert size={20} />} color="#fb7185" trendText="classified HIGH" />
        <StatCard title="Blocked events" value={data.blockedEvents} icon={<Ban size={20} />} color="#fbbf24" trendText="action BLOCKED" />
        <StatCard title="Active sources" value={data.activeSources} icon={<Database size={20} />} color="#34d399" trendText="unique source IPs" />
      </section>

      <section className="dashboard-grid">
        <div className="panel recent-events-panel">
          <div className="panel-header">
            <div><p className="eyebrow">Event stream</p><h2>Recent events</h2></div>
            <a className="text-link" href="/events">Open explorer <ArrowUpRight size={15} /></a>
          </div>
          <EventsTable events={data.events.slice(0, 5)} />
        </div>

        <div className="dashboard-side-column">
          <div className="panel quick-action-panel">
            <div className="panel-header"><div><p className="eyebrow">Workflow</p><h2>Actions</h2></div></div>
            <a className="action-tile" href="/upload"><span className="action-icon blue"><UploadCloud size={19} /></span><span><strong>Upload logs</strong><small>Process a supported file</small></span><ArrowUpRight size={16} /></a>
            <a className="action-tile" href="/events"><span className="action-icon amber"><Clock3 size={19} /></span><span><strong>Review events</strong><small>Filter the live event store</small></span><ArrowUpRight size={16} /></a>
          </div>
          <div className={`panel health-panel ${status.connected ? "is-healthy" : "is-offline"}`}>
            <div className="health-orbit"><span></span><Database size={25} /></div>
            <div><p className="eyebrow">Backend status</p><h2>{status.connected ? "Connected" : status.loading ? "Checking..." : "Offline"}</h2><p>{status.connected ? "API and database health checks are responding." : "No live health response is available."}</p></div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
