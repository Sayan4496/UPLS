function EventsTable({ events = [], onSelect }) {
  if (!events.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">⌕</div>
        <h3>No events found</h3>
        <p>No security events match your current search.</p>
      </div>
    );
  }

  return (
    <div className="events-table-wrapper">
      <table className="events-table">

        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Source Type</th>
            <th>Host</th>
            <th>Source IP</th>
            <th>Destination</th>
            <th>Event Type</th>
            <th>Severity</th>
            <th>Action</th>
            <th>Message</th>
          </tr>
        </thead>

        <tbody>

          {events.map((event) => (

            <tr key={event.id} onClick={() => onSelect?.(event)} className="event-row-clickable">

              <td className="timestamp">
                {event.event_timestamp
                  ? new Date(event.event_timestamp).toLocaleString(
                    undefined,
                    {
                      timeZone: "UTC",
                      year: "numeric",
                      month: "numeric",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                      second: "2-digit"
                    }
                  ) + " UTC"
                  : event.normalized_at
                    ? `${new Date(event.normalized_at).toLocaleString(
                      undefined,
                      {
                        timeZone: "UTC",
                        year: "numeric",
                        month: "numeric",
                        day: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                        second: "2-digit"
                      }
                    )} UTC (ingested)`
                    : "No source timestamp"}
              </td>

              <td>{event.source_format || "UNKNOWN"}</td>

              <td>{event.device_type || event.vendor || event.parsed_log?.host || "N/A"}</td>

              <td>
                <span className="ip-address">
                  {event.source_ip || "N/A"}
                </span>
              </td>

              <td>
                <span className="ip-address">
                  {event.destination_ip || "N/A"}
                </span>
              </td>

              <td>
                <span className="event-type">
                  {event.event_type || "UNKNOWN"}
                </span>
              </td>

              <td>
                <SeverityBadge severity={event.severity} />
              </td>

              <td>
                <ActionBadge action={event.action} />
              </td>

              <td className="event-message">
                {event.message || "No message"}
              </td>

            </tr>

          ))}

        </tbody>

      </table>
    </div>
  );
}


function SeverityBadge({ severity }) {

  const value = severity?.toLowerCase() || "unknown";

  return (
    <span className={`severity-badge ${value}`}>
      {severity || "UNKNOWN"}
    </span>
  );
}


function ActionBadge({ action }) {

  const value = action?.toLowerCase() || "unknown";

  return (
    <span className={`action-badge ${value}`}>
      {action || "UNKNOWN"}
    </span>
  );
}


export default EventsTable;