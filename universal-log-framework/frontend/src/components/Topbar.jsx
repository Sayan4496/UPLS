import {
  Search,
  Bell,
  Moon,
  Sun
} from "lucide-react";

function Topbar({
  search,
  setSearch,
  darkMode,
  setDarkMode
}) {

  return (

    <header className="topbar">

      <div className="search-container">

        <Search size={20} />

        <input
          type="text"
          placeholder="Search events, IP addresses, or keywords..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <kbd>Ctrl K</kbd>

      </div>


      <div className="topbar-actions">

        <button
          className="theme-toggle"
          onClick={() => setDarkMode(!darkMode)}
        >

          {darkMode ? (
            <Sun size={18} />
          ) : (
            <Moon size={18} />
          )}

        </button>


        <button className="notification-btn">

          <Bell size={20} />

          <span className="notification-dot"></span>

        </button>


        <div className="user-profile">

          <div className="avatar">

            S

          </div>

          <span>Sayan</span>

        </div>

      </div>

    </header>

  );
}

export default Topbar;