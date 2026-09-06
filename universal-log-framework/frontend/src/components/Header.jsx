import { useState } from "react";
import { Bell, Menu, Search, Sun, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

function Header({ onMenuClick }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [isLight, setIsLight] = useState(() => localStorage.getItem("ulps-theme") === "light");

  const toggleTheme = () => {
    const nextTheme = isLight ? "dark" : "light";
    setIsLight(!isLight);
    localStorage.setItem("ulps-theme", nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  };

  const submitSearch = (event) => {
    event.preventDefault();
    const value = query.trim();
    navigate(value ? `/events?search=${encodeURIComponent(value)}` : "/events");
  };

  return (
    <header className="header">
      <button className="mobile-menu-button" aria-label="Open navigation" onClick={onMenuClick}>
        <Menu size={20} />
      </button>

      <form className="header-search" onSubmit={submitSearch}>
        <Search size={19} />
        <input
          type="search"
          placeholder="Search events, IP addresses, or keywords..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search events"
        />
      </form>

      <div className="header-actions">
        <button className="header-icon-button" aria-label="Toggle theme" onClick={toggleTheme}>
          <Sun size={19} />
        </button>

        <div className="notification-wrap">
          <button className="header-icon-button notification-button" aria-label="Show notifications" onClick={() => setShowNotifications(!showNotifications)}>
            <Bell size={19} />
            <span className="notification-dot"></span>
          </button>
          {showNotifications && (
            <div className="notification-popover">
              <strong>Notifications</strong>
              <p>Live alerts are provided by the event stream.</p>
              <button onClick={() => setShowNotifications(false)}><X size={14} /> Dismiss</button>
            </div>
          )}
        </div>

      </div>
    </header>
  );
}

export default Header;
