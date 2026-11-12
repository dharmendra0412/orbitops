import { useEffect, useState } from "react";
import {
  Activity,
  Atom,
  Database,
  FileCheck2,
  Gauge,
  Layers3,
  ShieldCheck,
  Satellite,
} from "lucide-react";

type ApiStatus = "checking" | "online" | "offline";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const workstreams = [
  {
    icon: Database,
    title: "Scientific data",
    detail: "Source products, coordinate frames, transformations and provenance",
    state: "Foundation pending",
  },
  {
    icon: Atom,
    title: "Physics models",
    detail: "Explicit equations, assumptions, units and model versioning",
    state: "Not yet released",
  },
  {
    icon: Gauge,
    title: "Engineering analysis",
    detail: "Mass, trajectory, power, thermal and communications budgets",
    state: "Not yet released",
  },
  {
    icon: FileCheck2,
    title: "Verification & validation",
    detail: "Test vectors, independent references and uncertainty evidence",
    state: "Evidence required",
  },
];

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${apiBase}/api/v1/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        setApiStatus("online");
      })
      .catch(() => {
        if (!controller.signal.aborted) setApiStatus("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ORBITOPS home">
          <span className="brand-mark"><Satellite size={20} /></span>
          <span>ORBIT<span className="brand-accent">OPS</span></span>
        </a>
        <div className="topbar-right">
          <span className="environment-label">ENGINEERING WORKSPACE</span>
          <span className={`api-indicator ${apiStatus}`}>
            <span className="status-dot" />
            API {apiStatus}
          </span>
        </div>
      </header>

      <section className="hero">
        <div className="eyebrow"><Activity size={14} /> MISSION ENGINEERING PLATFORM</div>
        <h1>Design with evidence.<br /><span>Operate with confidence.</span></h1>
        <p className="hero-copy">
          A traceable engineering workspace for lunar mission analysis.
          Every result will be tied to its data, equations, assumptions and validation evidence.
        </p>
        <div className="hero-meta">
          <span><ShieldCheck size={15} /> Evidence-first engineering</span>
          <span><Layers3 size={15} /> Versioned models and datasets</span>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <div className="eyebrow">ENGINEERING WORKSTREAMS</div>
          <h2>System foundation</h2>
        </div>
        <span className="stage-pill">FOUNDATION · 0.1.0</span>
      </section>

      <section className="workstream-grid" aria-label="Engineering workstreams">
        {workstreams.map(({ icon: Icon, title, detail, state }, index) => (
          <article className="workstream-card" key={title}>
            <div className="card-top">
              <span className="card-icon"><Icon size={19} /></span>
              <span className="card-index">0{index + 1}</span>
            </div>
            <h3>{title}</h3>
            <p>{detail}</p>
            <div className="card-state"><span />{state}</div>
          </article>
        ))}
      </section>

      <section className="integrity-note">
        <div className="integrity-icon"><ShieldCheck size={20} /></div>
        <div>
          <h3>Scientific integrity is a release requirement</h3>
          <p>
            No placeholder measurements, invented hardware specifications or unvalidated
            model outputs will be presented as engineering facts. Capabilities will be
            enabled only when their evidence and acceptance criteria are in place.
          </p>
        </div>
      </section>

      <footer>
        <span>ORBITOPS · ENGINEERING-GRADE LUNAR MISSION ANALYSIS</span>
        <span>EARLY FOUNDATION BUILD · NOT FOR FLIGHT OR OPERATIONAL USE</span>
      </footer>
    </main>
  );
}
