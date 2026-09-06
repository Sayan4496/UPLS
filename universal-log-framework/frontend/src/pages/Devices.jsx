import { useEffect, useState } from "react";
import { RefreshCw, Server, WifiOff } from "lucide-react";

import { getEvents } from "../services/api";

function Devices() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadSources = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await getEvents({ page: 1, limit: 100 });
      const sourceMap = new Map();
      (response.events || []).forEach((event) => {
        const key = event.source_ip || event.vendor || event.device_type;
        if (key && !sourceMap.has(key)) sourceMap.set(key, { key, vendor: event.vendor, type: event.device_type, events: 1 });
        else if (key) sourceMap.get(key).events += 1;
      });
      setSources([...sourceMap.values()]);
    } catch {
      setSources([]);
      setError("Sources cannot be listed until the events API responds.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(loadSources, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="page">
      <div className="page-header"><div><p className="eyebrow">Observed infrastructure</p><h1>Log sources</h1><p>Unique sources derived from the latest events returned by the API.</p></div><button className="secondary-button" onClick={loadSources} disabled={loading}><RefreshCw size={16} /> Refresh</button></div>
      {error && <div className="connection-error"><strong>Source inventory unavailable</strong><p>{error}</p></div>}
      {loading ? <div className="loading-state"><div className="loader" /> Reading event sources...</div> : sources.length ? <div className="source-grid">{sources.map((source) => <article className="source-card" key={source.key}><div className="source-card-icon"><Server size={20} /></div><div><p className="eyebrow">Observed source</p><h2>{source.key}</h2><p>{source.vendor || source.type || "Metadata not provided"}</p></div><span className="data-chip">{source.events} events</span></article>)}</div> : <div className="empty-state panel"><WifiOff size={25} /><h3>No sources observed</h3><p>Upload and process a log file to populate this inventory.</p></div>}
    </div>
  );
}

export default Devices;
