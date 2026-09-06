import { useEffect, useState } from "react";
import { Check, Moon, Save, Sun } from "lucide-react";

function Settings() {
  const [theme, setTheme] = useState(() => localStorage.getItem("ulps-theme") || "dark");
  const [autoRefresh, setAutoRefresh] = useState(() => localStorage.getItem("ulps-auto-refresh") === "true");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const saveSettings = () => {
    localStorage.setItem("ulps-theme", theme);
    localStorage.setItem("ulps-auto-refresh", String(autoRefresh));
    document.documentElement.dataset.theme = theme;
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2400);
  };

  return (
    <div className="page">
      <div className="page-header"><div><p className="eyebrow">Workspace preferences</p><h1>Settings</h1><p>Preferences are stored locally in this browser and do not alter server data.</p></div><button className="primary-button" onClick={saveSettings}>{saved ? <Check size={17} /> : <Save size={17} />} {saved ? "Saved" : "Save settings"}</button></div>
      <section className="settings-grid">
        <div className="panel settings-section"><div><p className="eyebrow">Appearance</p><h2>Interface theme</h2><p>Choose the visual mode for this workspace.</p></div><div className="segmented-control"><button className={theme === "dark" ? "selected" : ""} onClick={() => setTheme("dark")}><Moon size={16} /> Dark</button><button className={theme === "light" ? "selected" : ""} onClick={() => setTheme("light")}><Sun size={16} /> Light</button></div></div>
        <div className="panel settings-section"><div><p className="eyebrow">Polling</p><h2>Automatic refresh</h2><p>Keep this preference ready for screens that support polling.</p></div><button className={`switch ${autoRefresh ? "on" : ""}`} role="switch" aria-checked={autoRefresh} onClick={() => setAutoRefresh(!autoRefresh)}><span /></button></div>
      </section>
    </div>
  );
}

export default Settings;
