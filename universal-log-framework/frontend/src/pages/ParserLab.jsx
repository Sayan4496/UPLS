import { useEffect, useState } from "react";
import { Braces, CheckCircle2, Code2, Plus, RotateCcw, Sparkles, X } from "lucide-react";

import { getParserPlugins, previewParserLab } from "../services/api";

const exampleLog = `<134>Sep 6 10:30:00 server sshd[123]:\nFailed password for root`;

function ParserLab() {
  const [rawLog, setRawLog] = useState(exampleLog);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [plugins, setPlugins] = useState(null);
  const [pluginsError, setPluginsError] = useState("");
  const [showAddParser, setShowAddParser] = useState(false);
  const [showExample, setShowExample] = useState(false);

  useEffect(() => {
    if (!rawLog.trim()) {
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      try {
        setLoading(true);
        setError("");
        setPreview(await previewParserLab(rawLog));
      } catch {
        setError("The parser preview is unavailable. Check the backend connection.");
        setPreview(null);
      } finally {
        setLoading(false);
      }
    }, 350);

    return () => window.clearTimeout(timer);
  }, [rawLog]);

  useEffect(() => {
    let active = true;
    getParserPlugins()
      .then((data) => active && setPlugins(data.plugins || []))
      .catch(() => active && setPluginsError("Parser registry is unavailable."));
    return () => { active = false; };
  }, []);

  const reset = () => setRawLog("");

  return (
    <div className="page parser-lab-page">
      <div className="page-header parser-lab-header">
        <div>
          <p className="eyebrow">Interactive parsing workbench</p>
          <h1>Parser Lab</h1>
          <p>Paste a log and watch detection, parsing, and normalization happen in real time.</p>
        </div>
        <button className="secondary-button" onClick={reset}><RotateCcw size={16} /> Clear lab</button>
      </div>

      <section className="parser-lab-input panel">
        <div className="panel-header"><div><p className="eyebrow">Input</p><h2>Paste a log entry</h2></div><span className="lab-live-status"><span /> Live preview</span></div>
        <textarea value={rawLog} onChange={(event) => setRawLog(event.target.value)} placeholder="Paste Syslog, CEF, JSON, CSV, or another supported log format..." spellCheck="false" />
        <div className="parser-lab-input-footer"><span>{rawLog.length.toLocaleString()} characters</span><span>{loading ? "Analyzing..." : "Updates automatically"}</span></div>
      </section>

      {error && <div className="connection-error"><strong>Parser Lab unavailable</strong><p>{error}</p></div>}
      <section className="panel parser-registry-panel">
        <div className="panel-header"><div><p className="eyebrow">Parser registry</p><h2>Registered parsers</h2></div><div className="parser-registry-actions"><span className="data-chip">{plugins ? `${plugins.length} registered` : "Loading..."}</span><button className="secondary-button" type="button" onClick={() => { setShowAddParser(true); setShowExample(false); }}><Plus size={15} /> Add Parser</button></div></div>
        {pluginsError && <div className="connection-error"><strong>Registry unavailable</strong><p>{pluginsError}</p></div>}
        {!pluginsError && plugins?.length === 0 && <div className="chart-empty">No parser metadata returned.</div>}
        {plugins?.length > 0 && <div className="parser-registry-grid">{plugins.map((plugin) => <div className="parser-registry-row" key={plugin.name}><div><strong>{plugin.name}</strong><span>{plugin.formats?.join(", ") || "Unknown format"}</span></div><div><span>{plugin.version || "Unknown version"}</span><small>{plugin.manifest?.source || plugin.manifest?.type || "Metadata not provided"}</small></div></div>)}</div>}
      </section>
      {showAddParser && <ParserOnboardingModal showExample={showExample} onClose={() => setShowAddParser(false)} onToggleExample={() => setShowExample((visible) => !visible)} />}
      {preview?.error && <div className="empty-state parser-lab-empty"><Sparkles size={24} /><h3>{preview.error}</h3><p>Paste a supported log format above to inspect it.</p></div>}

      {rawLog.trim() && preview && !preview.error && <>
        <section className="parser-lab-grid">
          <EvidencePanel title="Raw" eyebrow="Preserved input" icon={<Code2 size={17} />} className="raw-panel"><pre>{preview.raw_log}</pre></EvidencePanel>
          <section className="panel parser-result-card"><div className="panel-header"><div><p className="eyebrow">Detection result</p><h2>Parser</h2></div><CheckCircle2 className="parser-success-icon" size={20} /></div><div className="parser-confidence"><strong>{Math.round((preview.parser.confidence || 0) * 100)}%</strong><span>confidence</span></div><div className="parser-meta-list"><div><span>Parser</span><strong>{preview.parser.name}</strong></div><div><span>Format</span><strong>{preview.parser.source_format}</strong></div><div><span>Fallback</span><strong>{preview.parser.fallback_used ? "Used" : "No"}</strong></div></div></section>
        </section>

        <section className="parser-lab-grid parser-lab-output-grid">
          <EvidencePanel title="Normalized output" eyebrow="Universal schema" icon={<Braces size={17} />} className="normalized-panel"><pre>{JSON.stringify(preview.normalized, null, 2)}</pre></EvidencePanel>
          <section className="panel attributes-panel"><div className="panel-header"><div><p className="eyebrow">Structured fields</p><h2>Extracted attributes</h2></div></div><div className="attribute-list">{Object.entries(preview.attributes || {}).length ? Object.entries(preview.attributes).map(([key, value]) => <div className="attribute-row" key={key}><code>{key}</code><strong>{String(value)}</strong></div>) : <div className="chart-empty">No additional attributes extracted.</div>}</div></section>
        </section>

        <section className="panel parsed-data-panel"><div className="panel-header"><div><p className="eyebrow">Parser payload</p><h2>Parsed data</h2></div></div><pre>{JSON.stringify(preview.parsed_data, null, 2)}</pre></section>
      </>}
    </div>
  );
}

function EvidencePanel({ title, eyebrow, icon, className = "", children }) {
  return <section className={`panel parser-evidence-panel ${className}`}><div className="panel-header"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div><span className="panel-icon">{icon}</span></div>{children}</section>;
}

function ParserOnboardingModal({ showExample, onClose, onToggleExample }) {
  return <div className="parser-onboarding-backdrop" role="presentation" onClick={onClose}><section className="panel parser-onboarding-panel" role="dialog" aria-modal="true" aria-labelledby="add-parser-title" onClick={(event) => event.stopPropagation()}><div className="panel-header"><div><p className="eyebrow">Registry onboarding</p><h2 id="add-parser-title">Add a Custom Parser</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close Add a Custom Parser"><X size={18} /></button></div><p className="parser-onboarding-notice">Runtime parser upload is not enabled in this deployment.</p><p>To add a parser through the existing filesystem plugin contract:</p><pre className="parser-onboarding-tree">backend/parsers/custom/&lt;parser-name&gt;/{"\n"}├── __init__.py{"\n"}├── parser.py{"\n"}└── manifest.yaml</pre><ol className="parser-onboarding-steps"><li>Create the parser folder.</li><li>Implement the existing <code>BaseParser</code> contract.</li><li>Add <code>manifest.yaml</code> metadata.</li><li>Restart the ULPF services.</li><li>The parser registry automatically discovers it.</li></ol>{showExample && <div className="parser-onboarding-example"><p className="eyebrow">Example manifest</p><pre>name: MyParser{"\n"}version: 1.0.0{"\n"}supported_formats:{"\n"}  - MYFORMAT</pre></div>}<div className="parser-onboarding-actions"><button className="secondary-button" type="button" onClick={onClose}>Close</button><button className="primary-button" type="button" onClick={onToggleExample}>{showExample ? "Hide Example" : "View Example"}</button></div></section></div>;
}

export default ParserLab;
