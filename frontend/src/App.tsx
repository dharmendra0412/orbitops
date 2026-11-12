import { useEffect, useState } from "react";
import { Activity, Atom, CheckCircle2, Copy, Database, FileCheck2, Gauge, Layers3, LoaderCircle, ShieldCheck, Satellite, UploadCloud, Calculator } from "lucide-react";

type ApiStatus = "checking" | "online" | "offline";
type UploadState = "idle" | "uploading" | "success" | "error";
type UploadResult = { file_name: string; media_type: string; file_size_bytes: number; checksum_sha256: string; storage_status: string };
type ModelState = "idle" | "calculating" | "success" | "error";
type EngineeringOutput = { value: number; unit: string; credibility: string };
type PropulsionResult = {
  delta_v: EngineeringOutput;
  initial_mass: EngineeringOutput;
  mass_ratio: EngineeringOutput;
  model_version: string;
  equation_id: string;
  assumptions: string[];
  limitations: string[];
  equation_reference: string;
};
const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

type PowerResult = {
  supply_energy: EngineeringOutput;
  load_energy: EngineeringOutput;
  energy_margin: EngineeringOutput;
  margin_fraction: EngineeringOutput;
  model_version: string;
  equation_id: string;
  assumptions: string[];
  limitations: string[];
};

const workstreams = [
  { icon: Database, title: "Scientific data", detail: "Dataset manifests, source traceability and SHA-256 upload inspection", state: "Manifest + checksum API live", ready: true },
  { icon: Atom, title: "Physics models", detail: "Versioned ideal propulsion equation with explicit assumptions and limitations", state: "Ideal rocket model · UNVALIDATED", ready: false },
  { icon: Gauge, title: "Engineering analysis", detail: "Mass, trajectory, power, thermal and communications budgets", state: "Not yet released", ready: false },
  { icon: FileCheck2, title: "Verification & validation", detail: "Test vectors, independent references and uncertainty evidence", state: "Evidence required", ready: false },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function engineeringInput(valueId: string, name: string, value: number, unit: string, dimension: string) {
  return {
    value_id: valueId,
    name,
    value,
    unit,
    dimension,
    provenance: "illustrative",
    assumption_note: "Entered in ORBITOPS UI; user-supplied and not source-verified.",
    intended_use: "Preliminary ideal rocket-equation exploration only.",
    credibility: "unvalidated",
  };
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [dryMass, setDryMass] = useState("");
  const [propellantMass, setPropellantMass] = useState("");
  const [specificImpulse, setSpecificImpulse] = useState("");
  const [modelState, setModelState] = useState<ModelState>("idle");
  const [modelResult, setModelResult] = useState<PropulsionResult | null>(null);
  const [modelError, setModelError] = useState("");
  const [supplyPower, setSupplyPower] = useState("");
  const [loadPower, setLoadPower] = useState("");
  const [durationHours, setDurationHours] = useState("");
  const [powerState, setPowerState] = useState<ModelState>("idle");
  const [powerResult, setPowerResult] = useState<PowerResult | null>(null);
  const [powerError, setPowerError] = useState("");

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

  async function calculateIdealDeltaV() {
    const dry = Number(dryMass);
    const propellant = Number(propellantMass);
    const isp = Number(specificImpulse);
    if (![dry, propellant, isp].every((value) => Number.isFinite(value) && value > 0)) {
      setModelError("Enter positive numeric values for all three inputs.");
      setModelState("error");
      return;
    }

    const request = {
      dry_mass: engineeringInput("ui.dry-mass", "Dry mass", dry, "kg", "mass"),
      propellant_mass: engineeringInput("ui.propellant-mass", "Propellant mass", propellant, "kg", "mass"),
      specific_impulse: engineeringInput("ui.specific-impulse", "Specific impulse", isp, "s", "time"),
      intended_use: "Preliminary ideal rocket-equation exploration only; not a mission design result.",
    };

    setModelState("calculating");
    setModelError("");
    setModelResult(null);
    try {
      const response = await fetch(apiBase + "/api/v1/models/propulsion/ideal-delta-v", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Model calculation failed");
      }
      setModelResult(payload as PropulsionResult);
      setModelState("success");
    } catch (error) {
      setModelError(error instanceof Error ? error.message : "Unexpected model error");
      setModelState("error");
    }
  }

  async function calculateEnergyBalance() {
    const supply = Number(supplyPower);
    const load = Number(loadPower);
    const duration = Number(durationHours);
    if (!Number.isFinite(supply) || supply < 0 || !Number.isFinite(load) || load <= 0 || !Number.isFinite(duration) || duration <= 0) {
      setPowerError("Enter a non-negative supply power and positive load power and duration.");
      setPowerState("error");
      return;
    }

    const request = {
      supply_power: engineeringInput("ui.supply-power", "Average supply power", supply, "W", "power"),
      load_power: engineeringInput("ui.load-power", "Average load power", load, "W", "power"),
      duration: engineeringInput("ui.duration", "Interval duration", duration, "h", "time"),
      intended_use: "Preliminary constant-power energy bookkeeping only; not a mission power-system design.",
    };

    setPowerState("calculating");
    setPowerError("");
    setPowerResult(null);
    try {
      const response = await fetch(apiBase + "/api/v1/models/power/simple-energy-balance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Power model calculation failed");
      }
      setPowerResult(payload as PowerResult);
      setPowerState("success");
    } catch (error) {
      setPowerError(error instanceof Error ? error.message : "Unexpected power model error");
      setPowerState("error");
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

      <section className="model-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><Calculator size={20} /></span>
          <div><div className="eyebrow">PROPULSION MODEL · V0.1.0</div><h2>Ideal rocket-equation explorer</h2></div>
        </div>
        <p className="ingestion-copy">Estimate ideal delta-v from dry mass, propellant mass and specific impulse. All values entered here are tagged as illustrative and unvalidated; provide your own sourced inputs in the API for a traceable engineering record.</p>
        <div className="model-form">
          <label className="model-field">Dry mass <span>kg</span>
            <input type="number" min="0.000001" step="any" placeholder="Enter dry mass" value={dryMass} onChange={(event) => setDryMass(event.target.value)} />
          </label>
          <label className="model-field">Propellant mass <span>kg</span>
            <input type="number" min="0.000001" step="any" placeholder="Enter propellant mass" value={propellantMass} onChange={(event) => setPropellantMass(event.target.value)} />
          </label>
          <label className="model-field">Specific impulse <span>s</span>
            <input type="number" min="0.000001" step="any" placeholder="Enter Isp" value={specificImpulse} onChange={(event) => setSpecificImpulse(event.target.value)} />
          </label>
        </div>
        <button className="inspect-button model-button" type="button" onClick={calculateIdealDeltaV} disabled={apiStatus !== "online" || modelState === "calculating"}>
          {modelState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <Calculator size={16} />}
          {modelState === "calculating" ? "Calculating..." : "Calculate ideal delta-v"}
        </button>
        {modelError && <p className="inline-error">{modelError}</p>}
        {apiStatus === "offline" && <p className="inline-warning">Connect the ORBITOPS API to run the model.</p>}
        {modelResult && modelState === "success" && (
          <div className="model-result">
            <div className="result-heading"><CheckCircle2 size={17} /> Calculation complete · UNVALIDATED</div>
            <div className="model-metrics">
              <div><dt>Ideal delta-v</dt><dd>{modelResult.delta_v.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>m/s</small></dd></div>
              <div><dt>Initial mass</dt><dd>{modelResult.initial_mass.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>kg</small></dd></div>
              <div><dt>Mass ratio</dt><dd>{modelResult.mass_ratio.value.toLocaleString(undefined, { maximumFractionDigits: 4 })}</dd></div>
            </div>
            <div className="model-meta">Equation {modelResult.equation_id} · Model {modelResult.model_version}</div>
            <div className="model-assumptions">
              <strong>Assumptions</strong>
              <ul>{modelResult.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
              <strong>Limitations</strong>
              <ul>{modelResult.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <a className="api-docs-link" href={modelResult.equation_reference} target="_blank" rel="noreferrer">NASA equation reference ↗</a>
          </div>
        )}
      </section>

      <section className="model-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><Activity size={20} /></span>
          <div><div className="eyebrow">POWER MODEL · V0.1.0</div><h2>Constant-power energy balance</h2></div>
        </div>
        <p className="ingestion-copy">Compare average supply and load power over a fixed interval. This simple energy bookkeeping model does not represent batteries, eclipse periods, transient loads or power-system losses.</p>
        <div className="model-form">
          <label className="model-field">Average supply power <span>W</span>
            <input type="number" min="0" step="any" placeholder="Enter supply power" value={supplyPower} onChange={(event) => setSupplyPower(event.target.value)} />
          </label>
          <label className="model-field">Average load power <span>W</span>
            <input type="number" min="0.000001" step="any" placeholder="Enter load power" value={loadPower} onChange={(event) => setLoadPower(event.target.value)} />
          </label>
          <label className="model-field">Analysis duration <span>hours</span>
            <input type="number" min="0.000001" step="any" placeholder="Enter duration" value={durationHours} onChange={(event) => setDurationHours(event.target.value)} />
          </label>
        </div>
        <button className="inspect-button model-button" type="button" onClick={calculateEnergyBalance} disabled={apiStatus !== "online" || powerState === "calculating"}>
          {powerState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <Calculator size={16} />}
          {powerState === "calculating" ? "Calculating..." : "Calculate energy balance"}
        </button>
        {powerError && <p className="inline-error">{powerError}</p>}
        {apiStatus === "offline" && <p className="inline-warning">Connect the ORBITOPS API to run the model.</p>}
        {powerResult && powerState === "success" && (
          <div className="model-result">
            <div className="result-heading"><CheckCircle2 size={17} /> Calculation complete · UNVALIDATED</div>
            <div className="model-metrics">
              <div><dt>Supply energy</dt><dd>{powerResult.supply_energy.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>Wh</small></dd></div>
              <div><dt>Load energy</dt><dd>{powerResult.load_energy.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>Wh</small></dd></div>
              <div><dt>Energy margin</dt><dd>{powerResult.energy_margin.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} <small>Wh</small></dd></div>
            </div>
            <div className="model-meta">Margin fraction {(powerResult.margin_fraction.value * 100).toFixed(2)}% · Equation {powerResult.equation_id} · Model {powerResult.model_version}</div>
            <div className="model-assumptions">
              <strong>Assumptions</strong>
              <ul>{powerResult.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
              <strong>Limitations</strong>
              <ul>{powerResult.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
        )}
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
