import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { getEvents } from "../services/api";

import EventsTable from "../components/EventsTable";


function Events() {
  const [searchParams] = useSearchParams();

  const [events, setEvents] = useState([]);

  const [page, setPage] = useState(1);

  const [totalEvents, setTotalEvents] = useState(0);

  const [totalPages, setTotalPages] = useState(1);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [search, setSearch] = useState(searchParams.get("search") || "");


  const loadEvents = async (requestedPage = page) => {

    try {

      setLoading(true);

      setError("");

      const data = await getEvents({

        page: requestedPage,

        limit: 50

      });


      setEvents(data.events || []);

      setPage(data.page || requestedPage);

      setTotalEvents(data.total_events || 0);

      setTotalPages(data.total_pages || 1);

    }

    catch (err) {

      console.error(err);

      setEvents([]);

      setError(
        "Unable to connect to the backend server."
      );

    }

    finally {

      setLoading(false);

    }

  };


  useEffect(() => {

    const timer = window.setTimeout(() => {
      loadEvents();
    }, 0);

    return () => window.clearTimeout(timer);

  }, []);


  const filteredEvents = events.filter((event) => {

    const query = search.toLowerCase();


    return (

      event.source_ip?.toLowerCase().includes(query) ||

      event.destination_ip?.toLowerCase().includes(query) ||

      event.event_type?.toLowerCase().includes(query) ||

      event.severity?.toLowerCase().includes(query) ||

      event.action?.toLowerCase().includes(query) ||

      event.message?.toLowerCase().includes(query)

    );

  });


  return (

    <div className="page">


      <div className="page-header">

        <div>

          <h1>Security Events</h1>

          <p>
            Investigate and monitor all detected network security events.
          </p>

        </div>


        <button
          className="primary-button"
          onClick={() => loadEvents()}
        >

          ↻ Refresh Events

        </button>

      </div>



      <div className="events-toolbar">


        <div className="search-container">

          <span>⌕</span>

          <input

            type="text"

            placeholder="Search IP address, event type, severity or message..."

            value={search}

            onChange={(e) => setSearch(e.target.value)}

          />

        </div>


        <div className="events-summary">

          {totalEvents} Events

        </div>


      </div>



      {loading && (

        <div className="loading-state">

          <div className="loader"></div>

          Loading security events...

        </div>

      )}


      {error && (

        <div className="connection-error">

          <div>

            <strong>Backend Connection Failed</strong>

            <p>
              {error}
            </p>

          </div>


          <button
            onClick={() => loadEvents()}
          >

            Retry Connection

          </button>

        </div>

      )}


      {!loading && !error && (

        <>
          <EventsTable
            events={filteredEvents}
          />

          {totalPages > 1 && (
            <div className="events-pagination">
              <button
                onClick={() => loadEvents(page - 1)}
                disabled={page <= 1 || loading}
              >
                Previous
              </button>

              <span>
                Page {page} of {totalPages}
              </span>

              <button
                onClick={() => loadEvents(page + 1)}
                disabled={page >= totalPages || loading}
              >
                Next
              </button>
            </div>
          )}
        </>

      )}


    </div>

  );

}


export default Events;