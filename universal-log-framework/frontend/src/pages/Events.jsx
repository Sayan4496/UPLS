import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, SlidersHorizontal, X } from "lucide-react";

import { getEvent, getEvents } from "../services/api";
import EventsTable from "../components/EventsTable";

  const initialFilters = {
    search: "",
    severity: "",
    source_format: "",
    host: "",
    source_ip: "",
    destination_ip: "",
    event_type: "",
    parser: "",
    date_from: "",
    date_to: ""
  };

  const displayJson = (value) => JSON.stringify(value ?? {}, null, 2);

function Events() {
    const [searchParams] = useSearchParams();
    const [filters, setFilters] = useState({ ...initialFilters, search: searchParams.get("search") || "" });
    const [events, setEvents] = useState([]);
    const [page, setPage] = useState(1);
    const [totalEvents, setTotalEvents] = useState(0);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [selectedEvent, setSelectedEvent] = useState(null);

    const loadEvents = async (requestedPage = 1, activeFilters = filters) => {
      try {
        setLoading(true);
        setError("");
        const data = await getEvents({ ...activeFilters, page: requestedPage, limit: 50 });
        setEvents(data.events || []);
        setPage(data.page || requestedPage);
        setTotalEvents(data.total_events || 0);
        setTotalPages(data.total_pages || 1);
      } catch {
        setEvents([]);
        setError("Unable to connect to the backend server.");
      } finally {
        setLoading(false);
      }
    };

    useEffect(() => {
      const timer = window.setTimeout(() => loadEvents(1), 0);
      return () => window.clearTimeout(timer);
    }, []);

    const updateFilter = (name, value) => {
      const nextFilters = { ...filters, [name]: value };
      setFilters(nextFilters);
      window.clearTimeout(window.logExplorerTimer);
      window.logExplorerTimer = window.setTimeout(() => loadEvents(1, nextFilters), 350);
    };

    const setLastSevenDays = () => {
      const date = new Date();
      const end = new Date(date);
      end.setDate(end.getDate() + 1);
      date.setDate(date.getDate() - 7);
      const nextFilters = { ...filters, date_from: date.toISOString(), date_to: end.toISOString() };
      setFilters(nextFilters);
      loadEvents(1, nextFilters);
    };

    const clearFilters = () => {
      setFilters(initialFilters);
      loadEvents(1, initialFilters);
    };

    const openEvent = async (event) => {
      try {
        setSelectedEvent(await getEvent(event.id));
      } catch {
        setError("Unable to load the selected log evidence.");
      }
    };

    const selectedEventType = selectedEvent?.universal_event?.event?.type || selectedEvent?.event?.event_type || "Unknown event";
    const selectedEventFormat = selectedEvent?.universal_event?.log?.source_format || selectedEvent?.parser_information?.source_format || "Unknown format";

    return (
      <div className="page log-explorer-page">
        <div className="page-header">
          <div><p className="eyebrow">Investigate with context</p><h1>Search logs</h1><p>Filter, inspect, and trace every event back to the original payload.</p></div>
          <button className="secondary-button" onClick={() => loadEvents(page)} disabled={loading}><SlidersHorizontal size={16} /> Refresh results</button>
        </div>

        <section className="panel explorer-filters" aria-label="Log filters">
          <div className="explorer-search"><Search size={18} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Search failed login, message, IP, event type..." /></div>
          <div className="filter-grid">
            <label>Severity<select value={filters.severity} onChange={(event) => updateFilter("severity", event.target.value)}><option value="">Any severity</option><option>INFO</option><option>DEBUG</option><option>LOW</option><option>MEDIUM</option><option>WARNING</option><option>HIGH</option><option>ERROR</option><option>CRITICAL</option></select></label>
            <label>Source type<input value={filters.source_format} onChange={(event) => updateFilter("source_format", event.target.value)} placeholder="Syslog, CEF..." /></label>
            <label>Host<input value={filters.host} onChange={(event) => updateFilter("host", event.target.value)} placeholder="Firewall-01" /></label>
            <label>Source IP<input value={filters.source_ip} onChange={(event) => updateFilter("source_ip", event.target.value)} placeholder="10.0.0.1" /></label>
            <label>Destination IP<input value={filters.destination_ip} onChange={(event) => updateFilter("destination_ip", event.target.value)} placeholder="10.0.0.20" /></label>
            <label>Event type<input value={filters.event_type} onChange={(event) => updateFilter("event_type", event.target.value)} placeholder="LoginFailure" /></label>
            <label>Parser<input value={filters.parser} onChange={(event) => updateFilter("parser", event.target.value)} placeholder="syslog_parser" /></label>
            <label>Date from<input type="date" value={filters.date_from.slice(0, 10)} onChange={(event) => updateFilter("date_from", event.target.value)} /></label>
            <label>Date to<input type="date" value={filters.date_to.slice(0, 10)} onChange={(event) => updateFilter("date_to", event.target.value)} /></label>
          </div>
          <div className="filter-actions"><button className="filter-chip" onClick={setLastSevenDays}>Last 7 days</button><button className="text-button" onClick={clearFilters}><X size={14} /> Clear filters</button><span className="events-summary">{totalEvents.toLocaleString()} matching logs</span></div>
        </section>

        {error && <div className="connection-error"><strong>Explorer unavailable</strong><p>{error}</p></div>}
        {loading && <div className="loading-state"><div className="loader" /> Searching logs...</div>}
        {!loading && !error && <EventsTable events={events} onSelect={openEvent} />}
        {!loading && !error && totalPages > 1 && <div className="events-pagination"><button onClick={() => loadEvents(page - 1)} disabled={page <= 1}>Previous</button><span>Page {page} of {totalPages}</span><button onClick={() => loadEvents(page + 1)} disabled={page >= totalPages}>Next</button></div>}

        {selectedEvent && <div className="log-detail-backdrop" role="presentation" onClick={() => setSelectedEvent(null)}><aside className="log-detail-panel" role="dialog" aria-modal="true" aria-label="Log evidence" onClick={(event) => event.stopPropagation()}><div className="panel-header"><div><p className="eyebrow">Evidence chain</p><h2>Log details</h2></div><button className="icon-button" onClick={() => setSelectedEvent(null)} aria-label="Close details"><X size={18} /></button></div><div className="detail-summary"><span>{selectedEventType}</span><span>{selectedEventFormat}</span></div><EvidenceBlock title="Raw log" value={selectedEvent.raw_log} /><EvidenceBlock title="Parsed data" value={selectedEvent.parsed_data} /><EvidenceBlock title="Normalized data" value={selectedEvent.normalized_data} /><EvidenceBlock title="Universal event" value={selectedEvent.universal_event} /><EvidenceBlock title="Parser information" value={selectedEvent.parser_information} /></aside></div>}
      </div>
    );
}

function EvidenceBlock({ title, value }) {
  return <section className="evidence-block"><h3>{title}</h3><pre>{typeof value === "string" ? value : displayJson(value)}</pre></section>;
}

export default Events;