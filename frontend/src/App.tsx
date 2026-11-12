import { useEffect, useState } from "react";
import { Activity, Atom, CheckCircle2, Copy, Database, FileCheck2, Gauge, Layers3, LoaderCircle, ShieldCheck, Satellite, UploadCloud } from "lucide-react";

type ApiStatus = "checking" | "online" | "offline";
type UploadState = "idle" | "uploading" | "success" | "error";
type UploadResult = { file_name: string; media_type: string; file_size_bytes: number; checksum_sha256: string; storage_status: string };
const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

const workstreams = [
  { icon: Database, title: "Scientific data", detail: "Dataset manifests, source traceability and SHA-256 upload inspection", state: "Manifest + checksum API live", ready: true },
  { icon: Atom, title: "Physics models", detail: "Explicit equations, assumptions, units and model versioning", state: "Not yet released", ready: false },
  { icon: Gauge, title: "Engineering analysis", detail: "Mass, trajectory, power, thermal and communications budgets", state: "Not yet released", ready: false },
  { icon: FileCheck2, title: "Verification & validation", detail: "Test vectors, independent references and uncertainty evidence", state: "Evidence required", ready: false },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(apiBase + "/api/v1/health", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        setApiStatus("online");
      })
      .catch(() => {
        if (!controller.signal.aborted) setApiStatus("offline");
      });
    return () => controller.abort();
  }, []);

  async function inspectSelectedFile() {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);
    setUploadState("uploading");
    setUploadError("");
    setUploadResult(null);
    try {
      const response = await fetch(apiBase + "/api/v1/datasets/checksum", { method: "POST", body: formData });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Upload inspection failed");
      }
      setUploadResult(payload as UploadResult);
      setUploadState("success");
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Unexpected upload error");
      setUploadState("error");
    }
  }

  async function copyChecksum() {
    if (!uploadResult) return;
    try {
      await navigator.clipboard.writeText(uploadResult.checksum_sha256);
    } catch {
      setUploadError("Clipboard access is unavailable in this browser context.");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ORBITOPS home">
          <span className="brand-mark"><Satellite size={20} /></span>
          <span>ORBIT<span className="brand-accent">OPS</span></span>
        </a>
        <div className="topbar-right">
          <span className="environment-label">ENGINEERING WORKSPACE</span>
          <span className={"api-indicator " + apiStatus}><span className="status-dot" />API {apiStatus}</span>
        </div>
      </header>

      <section className="hero">
        <div className="eyebrow"><Activity size={14} /> MISSION ENGINEERING PLATFORM</div>
        <h1>Design with evidence.<br /><span>Operate with confidence.</span></h1>
        <p className="hero-copy">A traceable engineering workspace for lunar mission analysis. Every result will be tied to its data, equations, assumptions and validation evidence.</p>
        <div className="hero-meta">
          <span><ShieldCheck size={15} /> Evidence-first engineering</span>
          <span><Layers3 size={15} /> Versioned models and datasets</span>
        </div>
      </section>

      <section className="section-heading">
        <div><div className="eyebrow">ENGINEERING WORKSTREAMS</div><h2>System foundation</h2></div>
        <span className="stage-pill">FOUNDATION · 0.1.0</span>
      </section>

      <section className="workstream-grid" aria-label="Engineering workstreams">
        {workstreams.map(({ icon: Icon, title, detail, state, ready }, index) => (
          <article className="workstream-card" key={title}>
            <div className="card-top"><span className="card-icon"><Icon size={19} /></span><span className="card-index">0{index + 1}</span></div>
            <h3>{title}</h3><p>{detail}</p>
            <div className={"card-state " + (ready ? "ready" : "")}><span />{state}</div>
          </article>
        ))}
      </section>

      <section className="ingestion-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><UploadCloud size={20} /></span>
          <div><div className="eyebrow">DATA INTEGRITY TOOL</div><h2>Inspect a dataset file</h2></div>
        </div>
        <p className="ingestion-copy">Calculate a SHA-256 checksum and file metadata before creating a dataset manifest. Uploads are streamed, limited to 100 MiB, and are not stored by this service.</p>
        <div className="upload-controls">
          <label className="file-picker">
            <input type="file" onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null);
              setUploadResult(null);
              setUploadError("");
              setUploadState("idle");
            }} />
            <span>{selectedFile ? selectedFile.name : "Choose a dataset file"}</span>
            <small>{selectedFile ? formatBytes(selectedFile.size) : "Maximum size: 100 MiB"}</small>
          </label>
          <button className="inspect-button" type="button" onClick={inspectSelectedFile} disabled={!selectedFile || uploadState === "uploading" || apiStatus !== "online"}>
            {uploadState === "uploading" ? <LoaderCircle size={16} className="spin" /> : <Activity size={16} />}
            {uploadState === "uploading" ? "Inspecting..." : "Calculate checksum"}
          </button>
        </div>
        {apiStatus === "offline" && <p className="inline-warning">Connect the ORBITOPS API to inspect files.</p>}
        {uploadState === "error" && <p className="inline-error">{uploadError}</p>}
        {uploadState === "success" && uploadResult && (
          <div className="upload-result">
            <div className="result-heading"><CheckCircle2 size={17} /> Integrity metadata calculated</div>
            <dl>
              <div><dt>File</dt><dd>{uploadResult.file_name}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(uploadResult.file_size_bytes)}</dd></div>
              <div><dt>Media type</dt><dd>{uploadResult.media_type}</dd></div>
              <div><dt>Storage</dt><dd>Not persisted</dd></div>
            </dl>
            <div className="checksum-value"><span>{uploadResult.checksum_sha256}</span><button type="button" onClick={copyChecksum} aria-label="Copy SHA-256 checksum"><Copy size={15} /></button></div>
            {uploadError && <p className="inline-warning">{uploadError}</p>}
          </div>
        )}
        <a className="api-docs-link" href={apiBase + "/docs"} target="_blank" rel="noreferrer">Open API documentation ↗</a>
      </section>

      <section className="integrity-note">
        <div className="integrity-icon"><ShieldCheck size={20} /></div>
        <div>
          <h3>Scientific integrity is a release requirement</h3>
          <p>No placeholder measurements, invented hardware specifications or unvalidated model outputs will be presented as engineering facts. Capabilities will be enabled only when their evidence and acceptance criteria are in place.</p>
        </div>
      </section>

      <footer>
        <span>ORBITOPS · ENGINEERING-GRADE LUNAR MISSION ANALYSIS</span>
        <span>EARLY FOUNDATION BUILD · NOT FOR FLIGHT OR OPERATIONAL USE</span>
      </footer>
    </main>
  );
}
