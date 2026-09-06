import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import {
  LayoutDashboard,
  List,
  Upload,
  BarChart3,
  Monitor,
  FileText,
  Settings,
  Shield,
  Server,
  Database
} from "lucide-react";
import { checkBackendHealth } from "../services/api";


function Sidebar({ navOpen, onClose }) {
  const [health, setHealth] = useState({ loading: true, connected: false });

  useEffect(() => {
    let active = true;
    checkBackendHealth().then((result) => {
      if (active) setHealth({ loading: false, connected: result.connected });
    });
    return () => { active = false; };
  }, []);

  const navigation = [

    {
      name: "Dashboard",
      path: "/",
      icon: LayoutDashboard
    },

    {
      name: "Events",
      path: "/events",
      icon: List
    },

    {
      name: "Log Upload",
      path: "/upload",
      icon: Upload
    },

    {
      name: "Analytics",
      path: "/analytics",
      icon: BarChart3
    },

    {
      name: "Devices",
      path: "/devices",
      icon: Monitor
    },

    {
      name: "Reports",
      path: "/reports",
      icon: FileText
    },

    {
      name: "Settings",
      path: "/settings",
      icon: Settings
    }

  ];


  return (

    <>
      {navOpen && (
        <button className="nav-scrim" aria-label="Close navigation" onClick={onClose} />
      )}

      <aside className={`sidebar${navOpen ? " is-open" : ""}`} aria-label="Primary navigation">

      <div className="sidebar-brand">

        <div className="brand-icon">

          <Shield size={24} />

        </div>

        <div>

          <h1>ULPS</h1>

          <span>Log Intelligence</span>

        </div>

      </div>


      <nav className="sidebar-nav">

        {navigation.map((item) => {

          const Icon = item.icon;

          return (

            <NavLink

              key={item.path}

              to={item.path}

              className={({ isActive }) =>
                isActive
                  ? "nav-item active"
                  : "nav-item"
              }

              onClick={onClose}

            >

              <Icon size={20} />

              <span>{item.name}</span>

            </NavLink>

          );

        })}

      </nav>


      <div className="sidebar-status">

        <h3>System Status</h3>


        <div className="status-online">

          <span className="status-dot"></span>

          <span>System Monitoring</span>

        </div>


        <div className="system-info">

          <Server size={16} />

          <div>

            <span>Backend API</span>

            <strong>{health.loading ? "Checking..." : health.connected ? "Connected" : "Unavailable"}</strong>

          </div>

        </div>


        <div className="system-info">

          <Database size={16} />

          <div>

            <span>Database</span>

            <strong>{health.loading ? "Checking..." : health.connected ? "Connected" : "Unavailable"}</strong>

          </div>

        </div>

      </div>


      <div className="sidebar-footer">

        <span>Universal Log Framework</span>

        <small>v1.0.0</small>

      </div>

      </aside>
    </>

  );

}


export default Sidebar;