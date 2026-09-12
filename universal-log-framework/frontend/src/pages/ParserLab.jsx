import { useEffect, useState } from "react";
import { Braces, CheckCircle2, Code2, RotateCcw, Sparkles } from "lucide-react";

import { previewParserLab } from "../services/api";

const exampleLog = `<134>Sep 6 10:30:00 server sshd[123]:\nFailed password for root`;

function ParserLab() {
  const [rawLog, setRawLog] = useState(exampleLog);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

export default ParserLab;
