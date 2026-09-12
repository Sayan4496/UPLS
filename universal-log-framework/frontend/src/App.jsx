import { useState } from "react";
import { Routes, Route } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import Dashboard from "./pages/Dashboard";
import Events from "./pages/Events";
import Upload from "./pages/Upload";
import Analytics from "./pages/Analytics";
import Devices from "./pages/Devices";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import ParserLab from "./pages/ParserLab";

import "./App.css";


function App() {
  const [navOpen, setNavOpen] = useState(false);

  return (
      <div className="app-layout">

        <Sidebar navOpen={navOpen} onClose={() => setNavOpen(false)} />

        <div className="main-layout">

          <Header onMenuClick={() => setNavOpen(true)} />

          <main className="page-content">

            <Routes>

              <Route
                path="/"
                element={<Dashboard />}
              />

              <Route
                path="/events"
                element={<Events />}
              />

              <Route
                path="/upload"
                element={<Upload />}
              />

              <Route
                path="/analytics"
                element={<Analytics />}
              />

              <Route
                path="/parser-lab"
                element={<ParserLab />}
              />

              <Route
                path="/devices"
                element={<Devices />}
              />

              <Route
                path="/reports"
                element={<Reports />}
              />

              <Route
                path="/settings"
                element={<Settings />}
              />

            </Routes>

          </main>

        </div>

      </div>

  );

}


export default App;