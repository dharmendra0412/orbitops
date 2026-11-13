import { useEffect, useState } from "react";
import { Activity, Atom, CheckCircle2, Copy, Database, FileCheck2, Gauge, Layers3, LoaderCircle, ShieldCheck, Satellite, UploadCloud, Calculator } from "lucide-react";

type ApiStatus = "checking" | "online" | "offline";
type UploadState = "idle" | "uploading" | "success" | "error";
type UploadResult = { file_name: string; media_type: string; file_size_bytes: number; checksum_sha256: string; storage_status: string };
type ModelState = "idle" | "calculating" | "success" | "error";
type MissionRequirement = { requirement_id: string; title: string; statement: string; category: string; verification_method: string; acceptance_criteria: string; source_reference?: string };
type MissionProjectDraft = { name: string; summary: string; target_body: string; mission_archetype: string; primary_objective: string; intended_users: string[]; requirements: MissionRequirement[] };
type MissionProjectSummary = { project_id: string; name: string; target_body: string; mission_archetype: string; latest_revision: number; updated_at: string };
type MissionProjectRecord = { project_id: string; name: string; target_body: string; mission_archetype: string; latest_revision: number; revision: { revision_number: number; draft: MissionProjectDraft } };
type VerificationRecord = { verification_id: string; requirement_id: string; method: string; outcome: "pass" | "fail" | "inconclusive"; performed_at: string; performed_by: string; summary: string; evidence_reference?: string };
type SpacecraftComponent = { component_id: string; name: string; subsystem: string; mass: EngineeringOutput; power_draw?: EngineeringOutput | null; power_generation?: EngineeringOutput | null; load_duty_cycle: number; generation_duty_cycle: number };
type SpacecraftRecord = { latest_revision: number; revision: { draft: { components: SpacecraftComponent[] } } };
type SpacecraftBudget = { mass: { component_mass_kg: number; margin_percent: number; margin_mass_kg: number; total_with_margin_kg: number }; power: { average_generation_w: number; average_load_w: number; net_power_w: number; assumptions: string[] } };
type TraceabilityAllocation = { allocation_id: string; requirement_id: string; component_id: string; rationale: string; allocated_by: string; recorded_at: string };
type TraceabilityRow = { requirement_id: string; requirement_title: string; requirement_statement: string; requirement_category: string; verification_method: string; allocated: boolean; allocation_count: number; allocations: TraceabilityAllocation[]; active_component_count: number; stale_component_ids: string[]; verification_record_count: number; pass_record_count: number; fail_record_count: number; inconclusive_record_count: number; verification_evidence_present: boolean };
type TraceabilityMatrix = { mission_revision: number; spacecraft_configuration_revision: number | null; requirement_count: number; allocated_requirement_count: number; unallocated_requirement_count: number; rows: TraceabilityRow[]; limitations: string[] };
type ModelGovernanceModel = { model_id: string; display_name: string; model_version: string; equation_ids: string[]; intended_scope: string; current_state: "unvalidated" | "verified" | "validated" | "review_required"; latest_verification_outcome: "pass" | "fail" | "inconclusive" | null; latest_validation_outcome: "pass" | "fail" | "inconclusive" | null; assessment_count: number };
type ModelGovernanceCatalog = { models: ModelGovernanceModel[]; limitations: string[] };
type RevisionChange = { requirement_id?: string; component_id?: string; change_type: "added" | "removed" | "modified"; baseline_title?: string | null; target_title?: string | null; baseline_name?: string | null; target_name?: string | null; changed_fields: string[] };
type RevisionImpactReport = { baseline_mission_revision: number; target_mission_revision: number; baseline_spacecraft_revision: number; target_spacecraft_revision: number; requirement_changes: RevisionChange[]; component_changes: RevisionChange[]; impacted_allocations: { allocation_id: string; requirement_id: string; component_id: string; impact_reasons: string[] }[]; added_requirement_count: number; removed_requirement_count: number; modified_requirement_count: number; added_component_count: number; removed_component_count: number; modified_component_count: number; limitations: string[] };
type MissionCatalog = {
  scope: string;
  destinations: { planet_id: string; display_name: string; planetary_class: string; feasibility_status: string }[];
  mission_archetypes: { archetype: string; display_name: string; description: string }[];
  exclusions: string[];
};
type EngineeringOutput = { value: number; unit: string; credibility: string };
type PropulsionResult = {
  run_id?: string;
  created_at?: string;
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

type ModelRunSummary = {
  run_id: string;
  model_id: string;
  model_version: string;
  equation_id: string;
  created_at: string;
  result: Record<string, unknown>;
};
type PowerResult = {
  run_id?: string;
  created_at?: string;
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
  { icon: Gauge, title: "Engineering analysis", detail: "Constant-power energy balance prototype; full subsystem budgets remain pending", state: "Power model · UNVALIDATED", ready: false },
  { icon: FileCheck2, title: "Verification & validation", detail: "Requirement-linked evidence records and verification outcomes; independent acceptance remains pending", state: "Evidence register available · acceptance pending", ready: false },
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
  const [recentRuns, setRecentRuns] = useState<ModelRunSummary[]>([]);
  const [missionCatalog, setMissionCatalog] = useState<MissionCatalog | null>(null);
  const [selectedPlanet, setSelectedPlanet] = useState("mars");
  const [selectedArchetype, setSelectedArchetype] = useState("orbiter");
  const [missionProjects, setMissionProjects] = useState<MissionProjectSummary[]>([]);
  const [projectName, setProjectName] = useState("Lunar polar lander concept");
  const [projectObjective, setProjectObjective] = useState("Characterize selected surface and subsurface properties at a candidate lunar polar site.");
  const [projectState, setProjectState] = useState<ModelState>("idle");
  const [projectError, setProjectError] = useState("");
  const [selectedProject, setSelectedProject] = useState<MissionProjectRecord | null>(null);
  const [requirementId, setRequirementId] = useState("SCI-001");
  const [requirementTitle, setRequirementTitle] = useState("Acquire surface imagery");
  const [requirementStatement, setRequirementStatement] = useState("The payload shall acquire image data from the landing site.");
  const [requirementAcceptance, setRequirementAcceptance] = useState("Image acquisition performance is evaluated against a documented payload specification.");
  const [requirementMethod, setRequirementMethod] = useState("test");
  const [verificationOutcome, setVerificationOutcome] = useState<"pass" | "fail" | "inconclusive">("inconclusive");
  const [verificationSummary, setVerificationSummary] = useState("");
  const [verificationReference, setVerificationReference] = useState("");
  const [verificationRecords, setVerificationRecords] = useState<VerificationRecord[]>([]);
  const [verificationState, setVerificationState] = useState<ModelState>("idle");
  const [spacecraftRecord, setSpacecraftRecord] = useState<SpacecraftRecord | null>(null);
  const [spacecraftBudget, setSpacecraftBudget] = useState<SpacecraftBudget | null>(null);
  const [spacecraftComponents, setSpacecraftComponents] = useState<SpacecraftComponent[]>([]);
  const [componentId, setComponentId] = useState("BUS-001");
  const [componentName, setComponentName] = useState("Spacecraft bus");
  const [componentSubsystem, setComponentSubsystem] = useState("structure");
  const [componentMass, setComponentMass] = useState("");
  const [componentDraw, setComponentDraw] = useState("");
  const [componentGeneration, setComponentGeneration] = useState("");
  const [componentLoadDuty, setComponentLoadDuty] = useState("1");
  const [componentGenerationDuty, setComponentGenerationDuty] = useState("1");
  const [massMargin, setMassMargin] = useState("20");
  const [spacecraftState, setSpacecraftState] = useState<ModelState>("idle");
  const [spacecraftError, setSpacecraftError] = useState("");
  const [traceabilityMatrix, setTraceabilityMatrix] = useState<TraceabilityMatrix | null>(null);
  const [traceabilityRequirementId, setTraceabilityRequirementId] = useState("");
  const [traceabilityComponentId, setTraceabilityComponentId] = useState("");
  const [traceabilityRationale, setTraceabilityRationale] = useState("");
  const [traceabilityState, setTraceabilityState] = useState<ModelState>("idle");
  const [traceabilityError, setTraceabilityError] = useState("");
  const [modelGovernance, setModelGovernance] = useState<ModelGovernanceCatalog | null>(null);
  const [assessmentModelId, setAssessmentModelId] = useState("propulsion.ideal-rocket-equation");
  const [assessmentKind, setAssessmentKind] = useState<"verification" | "validation">("verification");
  const [assessmentOutcome, setAssessmentOutcome] = useState<"pass" | "fail" | "inconclusive">("inconclusive");
  const [assessmentMethod, setAssessmentMethod] = useState("test");
  const [assessmentSummary, setAssessmentSummary] = useState("");
  const [assessmentReference, setAssessmentReference] = useState("");
  const [assessmentState, setAssessmentState] = useState<ModelState>("idle");
  const [assessmentError, setAssessmentError] = useState("");
  const [baselineMissionRevision, setBaselineMissionRevision] = useState("1");
  const [targetMissionRevision, setTargetMissionRevision] = useState("1");
  const [baselineSpacecraftRevision, setBaselineSpacecraftRevision] = useState("1");
  const [targetSpacecraftRevision, setTargetSpacecraftRevision] = useState("1");
  const [revisionImpact, setRevisionImpact] = useState<RevisionImpactReport | null>(null);
  const [revisionImpactState, setRevisionImpactState] = useState<ModelState>("idle");
  const [revisionImpactError, setRevisionImpactError] = useState("");

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

  useEffect(() => {
    if (apiStatus === "online") {
      void refreshRecentRuns();
      void refreshMissionProjects();
      void refreshModelGovernance();
      fetch(apiBase + "/api/v1/missions/catalog")
        .then((response) => {
          if (!response.ok) throw new Error("Mission catalogue unavailable");
          return response.json();
        })
        .then((payload: MissionCatalog) => {
          setMissionCatalog(payload);
          if (payload.destinations.length > 0) setSelectedPlanet(payload.destinations[3]?.planet_id ?? payload.destinations[0].planet_id);
          if (payload.mission_archetypes.length > 0) setSelectedArchetype(payload.mission_archetypes[1]?.archetype ?? payload.mission_archetypes[0].archetype);
        })
        .catch(() => setMissionCatalog(null));
    }
  }, [apiStatus]);


  async function refreshModelGovernance() {
    try {
      const response = await fetch(apiBase + "/api/v1/models/governance/catalog");
      if (!response.ok) throw new Error("Unable to load model governance catalogue");
      const catalog = await response.json() as ModelGovernanceCatalog;
      setModelGovernance(catalog);
      if (!catalog.models.some((model) => model.model_id === assessmentModelId) && catalog.models[0]) {
        setAssessmentModelId(catalog.models[0].model_id);
      }
    } catch (error) {
      setAssessmentError(error instanceof Error ? error.message : "Unable to load model governance status");
    }
  }

  async function createModelAssessment() {
    const model = modelGovernance?.models.find((item) => item.model_id === assessmentModelId);
    if (!model || assessmentSummary.trim().length < 10 || assessmentReference.trim().length < 5) {
      setAssessmentError("Select a registered model and provide an assessment summary and evidence reference.");
      setAssessmentState("error");
      return;
    }
    setAssessmentState("calculating");
    setAssessmentError("");
    try {
      const response = await fetch(apiBase + "/api/v1/models/governance/assessments", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_id: model.model_id, model_version: model.model_version, equation_id: model.equation_ids[0],
          kind: assessmentKind, outcome: assessmentOutcome, method: assessmentMethod,
          performed_at: new Date().toISOString(), performed_by: "Workspace user",
          summary: assessmentSummary.trim(), evidence_reference: assessmentReference.trim(),
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to save model assessment");
      setAssessmentSummary("");
      setAssessmentState("success");
      await refreshModelGovernance();
    } catch (error) {
      setAssessmentError(error instanceof Error ? error.message : "Unexpected model assessment error");
      setAssessmentState("error");
    }
  }

  async function refreshMissionProjects() {
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects?limit=20");
      if (!response.ok) return;
      setMissionProjects(await response.json() as MissionProjectSummary[]);
    } catch { /* Project list is refreshed on the next API interaction. */ }
  }

  async function refreshVerificationRecords(projectId: string) {
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + projectId + "/verification-records");
      if (response.ok) setVerificationRecords(await response.json() as VerificationRecord[]);
    } catch { /* Evidence can be refreshed when the project is reopened. */ }
  }

  async function createVerificationRecord() {
    if (!selectedProject) return;
    const requirement = selectedProject.revision.draft.requirements[0];
    if (!requirement) return;
    if (verificationSummary.trim().length < 5) {
      setProjectError("Enter a concise verification summary of at least 5 characters.");
      setVerificationState("error");
      return;
    }
    setVerificationState("calculating");
    setProjectError("");
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + selectedProject.project_id + "/verification-records", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirement_id: requirement.requirement_id, method: requirement.verification_method, outcome: verificationOutcome, performed_at: new Date().toISOString(), performed_by: "Workspace user", summary: verificationSummary.trim(), evidence_reference: verificationReference.trim() || null }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not save verification evidence");
      setVerificationSummary("");
      setVerificationState("success");
      await refreshVerificationRecords(selectedProject.project_id);
    } catch (error) {
      setProjectError(error instanceof Error ? error.message : "Unexpected verification error");
      setVerificationState("error");
    }
  }




  async function analyzeRevisionImpact() {
    if (!selectedProject) return;
    const values = [baselineMissionRevision, targetMissionRevision, baselineSpacecraftRevision, targetSpacecraftRevision].map(Number);
    if (values.some((value) => !Number.isInteger(value) || value < 1) ||
        values[1] < values[0] || values[3] < values[2]) {
      setRevisionImpactError("Enter positive revision numbers; target revisions cannot precede baseline revisions.");
      setRevisionImpactState("error");
      return;
    }
    setRevisionImpactState("calculating");
    setRevisionImpactError("");
    try {
      const params = new URLSearchParams({
        baseline_mission_revision: String(values[0]), target_mission_revision: String(values[1]),
        baseline_spacecraft_revision: String(values[2]), target_spacecraft_revision: String(values[3]),
      });
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + selectedProject.project_id + "/traceability/change-impact?" + params.toString());
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to analyze revision changes");
      setRevisionImpact(result as RevisionImpactReport);
      setRevisionImpactState("success");
    } catch (error) {
      setRevisionImpactError(error instanceof Error ? error.message : "Unexpected revision impact error");
      setRevisionImpactState("error");
    }
  }

  async function refreshTraceability(projectId: string) {
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + projectId + "/traceability/matrix");
      if (!response.ok) throw new Error("Unable to load requirement traceability matrix");
      const matrix = await response.json() as TraceabilityMatrix;
      setTraceabilityMatrix(matrix);
      const firstUnallocated = matrix.rows.find((row) => !row.allocated);
      if (firstUnallocated) setTraceabilityRequirementId(firstUnallocated.requirement_id);
      else if (matrix.rows[0]) setTraceabilityRequirementId(matrix.rows[0].requirement_id);
      setTraceabilityComponentId((current) => current || spacecraftComponents[0]?.component_id || "");
    } catch (error) {
      setTraceabilityError(error instanceof Error ? error.message : "Unable to load traceability matrix");
    }
  }

  async function createRequirementAllocation() {
    if (!selectedProject || !traceabilityRequirementId || !traceabilityComponentId || traceabilityRationale.trim().length < 5) {
      setTraceabilityError("Select a requirement and component, then enter an allocation rationale of at least 5 characters.");
      setTraceabilityState("error");
      return;
    }
    setTraceabilityState("calculating");
    setTraceabilityError("");
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + selectedProject.project_id + "/traceability/allocations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirement_id: traceabilityRequirementId, component_id: traceabilityComponentId,
          rationale: traceabilityRationale.trim(), allocated_by: "Workspace user" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to create allocation");
      setTraceabilityRationale("");
      setTraceabilityState("success");
      await refreshTraceability(selectedProject.project_id);
    } catch (error) {
      setTraceabilityError(error instanceof Error ? error.message : "Unexpected traceability error");
      setTraceabilityState("error");
    }
  }

  async function refreshSpacecraft(projectId: string) {
    try {
      const base = apiBase + "/api/v1/missions/projects/" + projectId + "/spacecraft";
      const response = await fetch(base + "/configuration");
      if (response.status === 404) {
        setSpacecraftRecord(null); setSpacecraftBudget(null); setSpacecraftComponents([]); setTraceabilityComponentId(""); return;
      }
      if (!response.ok) throw new Error("Unable to load spacecraft configuration");
      const record = await response.json() as SpacecraftRecord;
      setSpacecraftRecord(record); setSpacecraftComponents(record.revision.draft.components);
      setTraceabilityComponentId(record.revision.draft.components[0]?.component_id ?? "");
      const budgetResponse = await fetch(base + "/budgets");
      if (budgetResponse.ok) setSpacecraftBudget(await budgetResponse.json() as SpacecraftBudget);
    } catch (error) { setSpacecraftError(error instanceof Error ? error.message : "Unable to load spacecraft data"); }
  }

  function addSpacecraftComponent() {
    const mass = Number(componentMass);
    const draw = componentDraw.trim() ? Number(componentDraw) : null;
    const generation = componentGeneration.trim() ? Number(componentGeneration) : null;
    const loadDuty = Number(componentLoadDuty);
    const generationDuty = Number(componentGenerationDuty);
    if (!componentId.trim() || !componentName.trim() || !Number.isFinite(mass) || mass < 0 ||
        (draw !== null && (!Number.isFinite(draw) || draw < 0)) ||
        (generation !== null && (!Number.isFinite(generation) || generation < 0)) ||
        !Number.isFinite(loadDuty) || loadDuty < 0 || loadDuty > 1 ||
        !Number.isFinite(generationDuty) || generationDuty < 0 || generationDuty > 1) {
      setSpacecraftError("Enter a component ID/name, non-negative mass, and valid optional power values."); return;
    }
    if (spacecraftComponents.some((item) => item.component_id === componentId.trim())) {
      setSpacecraftError("Component IDs must be unique."); return;
    }
    const quantity = (id: string, name: string, value: number, unit: string, dimension: string) => ({
      value_id: id, name, value, unit, dimension, provenance: "illustrative",
      assumption_note: "User-entered preliminary value; source not independently verified.",
      intended_use: "Preliminary spacecraft configuration bookkeeping only.",
      credibility: "unvalidated", limitations: ["Not independently verified or validated."],
    });
    setSpacecraftComponents((items) => [...items, {
      component_id: componentId.trim(), name: componentName.trim(), subsystem: componentSubsystem,
      mass: quantity("mass-" + componentId.trim(), componentName.trim() + " mass", mass, "kg", "mass"),
      power_draw: draw === null ? null : quantity("draw-" + componentId.trim(), componentName.trim() + " power draw", draw, "W", "power"),
      power_generation: generation === null ? null : quantity("generation-" + componentId.trim(), componentName.trim() + " power generation", generation, "W", "power"),
      load_duty_cycle: loadDuty, generation_duty_cycle: generationDuty,
    }]);
    setComponentId(""); setComponentName(""); setComponentMass(""); setComponentDraw(""); setComponentGeneration(""); setSpacecraftError("");
  }

  async function saveSpacecraftConfiguration() {
    if (!selectedProject || spacecraftComponents.length === 0) {
      setSpacecraftError("Open a mission project and add at least one component."); setSpacecraftState("error"); return;
    }
    const margin = Number(massMargin);
    if (!Number.isFinite(margin) || margin < 0 || margin > 100) {
      setSpacecraftError("Mass margin must be between 0 and 100 percent."); setSpacecraftState("error"); return;
    }
    setSpacecraftState("calculating"); setSpacecraftError("");
    try {
      const base = apiBase + "/api/v1/missions/projects/" + selectedProject.project_id + "/spacecraft";
      const endpoint = base + (spacecraftRecord ? "/configuration/revisions" : "/configuration");
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedProject.name + " spacecraft configuration",
          description: "User-authored preliminary component configuration.",
          components: spacecraftComponents, mass_margin_percent: margin,
          assumptions: ["Component values are user-entered and not independently verified."] }) });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to save configuration");
      setSpacecraftRecord(result as SpacecraftRecord);
      setTraceabilityComponentId(spacecraftComponents[0]?.component_id ?? "");
      const budgetResponse = await fetch(base + "/budgets");
      if (budgetResponse.ok) setSpacecraftBudget(await budgetResponse.json() as SpacecraftBudget);
      setSpacecraftState("success");
      await refreshTraceability(selectedProject.project_id);
    } catch (error) {
      setSpacecraftError(error instanceof Error ? error.message : "Unexpected spacecraft error"); setSpacecraftState("error");
    }
  }

  async function createMissionProject() {
    if (projectName.trim().length < 3 || projectObjective.trim().length < 10) {
      setProjectError("Enter a mission name (at least 3 characters) and objective (at least 10 characters).");
      setProjectState("error");
      return;
    }
    const payload: MissionProjectDraft = {
      name: projectName.trim(),
      summary: "Preliminary mission definition created in ORBITOPS.",
      target_body: selectedPlanet === "moon" ? "Moon" : (missionCatalog?.destinations.find((item) => item.planet_id === selectedPlanet)?.display_name ?? selectedPlanet),
      mission_archetype: selectedArchetype,
      primary_objective: projectObjective.trim(),
      intended_users: ["students", "researchers", "engineers"],
      requirements: [{ requirement_id: requirementId.trim(), title: requirementTitle.trim(), statement: requirementStatement.trim(), category: "science", verification_method: requirementMethod, acceptance_criteria: requirementAcceptance.trim() }],
    };
    setProjectState("calculating");
    setProjectError("");
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Mission project creation failed");
      setSelectedProject(result as MissionProjectRecord);
      setVerificationRecords([]);
      setSpacecraftRecord(null);
      setSpacecraftBudget(null);
      setSpacecraftComponents([]);
      setSpacecraftError("");
      setSpacecraftState("idle");
      setProjectState("success");
      await refreshMissionProjects();
    } catch (error) {
      setProjectError(error instanceof Error ? error.message : "Unexpected mission project error");
      setProjectState("error");
    }
  }

  async function openMissionProject(projectId: string) {
    try {
      const response = await fetch(apiBase + "/api/v1/missions/projects/" + projectId);
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Unable to load mission project");
      setSelectedProject(result as MissionProjectRecord);
      await refreshVerificationRecords(projectId);
      await refreshSpacecraft(projectId);
      await refreshTraceability(projectId);
    } catch (error) {
      setProjectError(error instanceof Error ? error.message : "Unable to load mission project");
      setProjectState("error");
    }
  }

  async function refreshRecentRuns() {
    try {
      const response = await fetch(apiBase + "/api/v1/models/runs?limit=10");
      if (!response.ok) return;
      const payload = await response.json();
      setRecentRuns(payload as ModelRunSummary[]);
    } catch {
      // Run history is supplementary; calculation responses remain visible if listing fails.
    }
  }

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
      void refreshRecentRuns();
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
      void refreshRecentRuns();
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
          <span className="environment-label">MULTI-PLANETARY WORKSPACE</span>
          <span className={"api-indicator " + apiStatus}><span className="status-dot" />API {apiStatus}</span>
        </div>
      </header>

      <section className="hero">
        <div className="eyebrow"><Activity size={14} /> MISSION ENGINEERING PLATFORM</div>
        <h1>Design with evidence.<br /><span>Operate with confidence.</span></h1>
        <p className="hero-copy">A traceable engineering workspace for missions across all eight planets. Every result will be tied to its data, equations, assumptions and validation evidence.</p>
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

      <section className="model-panel mission-catalog-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><Satellite size={20} /></span>
          <div><div className="eyebrow">MISSION SCOPE · EIGHT PLANETS</div><h2>Planetary mission explorer</h2></div>
        </div>
        <p className="ingestion-copy">Choose a destination and mission archetype to define a future analysis scenario. This catalogue does not yet calculate destination-specific feasibility.</p>
        {missionCatalog ? (
          <>
            <div className="model-form">
              <label className="model-field">Destination
                <select value={selectedPlanet} onChange={(event) => setSelectedPlanet(event.target.value)}>
                  {missionCatalog.destinations.map((planet) => <option key={planet.planet_id} value={planet.planet_id}>{planet.display_name} · {planet.planetary_class.replace("_", " ")}</option>)}
                </select>
              </label>
              <label className="model-field">Mission archetype
                <select value={selectedArchetype} onChange={(event) => setSelectedArchetype(event.target.value)}>
                  {missionCatalog.mission_archetypes.map((item) => <option key={item.archetype} value={item.archetype}>{item.display_name}</option>)}
                </select>
              </label>
            </div>
            <div className="catalog-selection">
              <strong>{missionCatalog.destinations.find((planet) => planet.planet_id === selectedPlanet)?.display_name ?? "Selected planet"} · {missionCatalog.mission_archetypes.find((item) => item.archetype === selectedArchetype)?.display_name ?? "Mission"}</strong>
              <span>{missionCatalog.mission_archetypes.find((item) => item.archetype === selectedArchetype)?.description}</span>
              <small>Feasibility: NOT ASSESSED · Mission profile has not yet been created.</small>
            </div>
            <div className="planet-chip-list">
              {missionCatalog.destinations.map((planet) => <button type="button" key={planet.planet_id} className={"planet-chip " + (planet.planet_id === selectedPlanet ? "selected" : "")} onClick={() => setSelectedPlanet(planet.planet_id)}>{planet.display_name}</button>)}
            </div>
          </>
        ) : (
          <p className="run-empty">Connect the API to load the planetary mission catalogue.</p>
        )}
      </section>

      <section className="model-panel mission-catalog-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><Layers3 size={20} /></span>
          <div><div className="eyebrow">MISSION WORKSPACE · PERSISTENT PROJECTS</div><h2>Create a mission project</h2></div>
        </div>
        <p className="ingestion-copy">Record a mission objective and its current assumptions. Each saved definition becomes an immutable numbered revision. Project creation does not certify feasibility.</p>
        <div className="model-form">
          <label className="model-field">Project name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} maxLength={160} />
          </label>
          <label className="model-field">Target body
            <select value={selectedPlanet} onChange={(event) => setSelectedPlanet(event.target.value)}>
              <option value="moon">Moon</option>
              {missionCatalog?.destinations.map((body) => <option key={body.planet_id} value={body.planet_id}>{body.display_name}</option>)}
            </select>
          </label>
          <label className="model-field">Mission archetype
            <select value={selectedArchetype} onChange={(event) => setSelectedArchetype(event.target.value)}>
              {missionCatalog?.mission_archetypes.map((item) => <option key={item.archetype} value={item.archetype}>{item.display_name}</option>)}
            </select>
          </label>
        </div>
        <label className="model-field">Primary mission objective
          <textarea value={projectObjective} onChange={(event) => setProjectObjective(event.target.value)} rows={3} maxLength={4000} />
        </label>
        <div className="requirement-editor">
          <div className="eyebrow">INITIAL SCIENCE REQUIREMENT</div>
          <div className="model-form">
            <label className="model-field">Requirement ID<input value={requirementId} onChange={(event) => setRequirementId(event.target.value)} maxLength={100} /></label>
            <label className="model-field">Verification method
              <select value={requirementMethod} onChange={(event) => setRequirementMethod(event.target.value)}>
                <option value="test">Test</option><option value="analysis">Analysis</option><option value="inspection">Inspection</option><option value="demonstration">Demonstration</option><option value="to_be_defined">To be defined</option>
              </select>
            </label>
            <label className="model-field">Requirement title<input value={requirementTitle} onChange={(event) => setRequirementTitle(event.target.value)} maxLength={200} /></label>
          </div>
          <label className="model-field">Requirement statement<textarea value={requirementStatement} onChange={(event) => setRequirementStatement(event.target.value)} rows={2} maxLength={2000} /></label>
          <label className="model-field">Acceptance criteria<textarea value={requirementAcceptance} onChange={(event) => setRequirementAcceptance(event.target.value)} rows={2} maxLength={2000} /></label>
        </div>
        <button className="inspect-button model-button" type="button" onClick={createMissionProject} disabled={apiStatus !== "online" || projectState === "calculating"}>
          {projectState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <Layers3 size={16} />}
          {projectState === "calculating" ? "Creating project..." : "Create mission project"}
        </button>
        {projectError && <p className="inline-error">{projectError}</p>}
        {projectState === "success" && selectedProject && <p className="inline-warning">Project saved · Revision {selectedProject.latest_revision} · Feasibility not assessed.</p>}
        <div className="model-assumptions">
          <strong>Saved mission projects ({missionProjects.length})</strong>
          {missionProjects.length === 0 ? <p className="run-empty">No mission projects created yet.</p> : (
            <div className="run-list">
              {missionProjects.map((project) => <div className="run-row" key={project.project_id}>
                <div className="run-row-main"><strong>{project.name}</strong><span>{project.target_body} · {project.mission_archetype} · Revision {project.latest_revision}</span></div>
                <button className="planet-chip" type="button" onClick={() => openMissionProject(project.project_id)}>Open project</button>
              </div>)}
            </div>
          )}
        </div>
        {selectedProject && <div className="catalog-selection">
          <strong>{selectedProject.name} · Revision {selectedProject.latest_revision}</strong>
          <span>{selectedProject.revision.draft.primary_objective}</span>
          <small>{selectedProject.target_body} · {selectedProject.mission_archetype} · Project definition only</small>
        </div>}
        {selectedProject && <div className="requirement-editor">
          <div className="eyebrow">REQUIREMENT VERIFICATION EVIDENCE</div>
          <p className="ingestion-copy">Record an outcome against {selectedProject.revision.draft.requirements[0]?.requirement_id ?? "the selected requirement"}. Evidence entries are append-only and do not constitute independent approval.</p>
          <div className="model-form">
            <label className="model-field">Recorded outcome
              <select value={verificationOutcome} onChange={(event) => setVerificationOutcome(event.target.value as "pass" | "fail" | "inconclusive")}>
                <option value="inconclusive">Inconclusive</option><option value="pass">Pass</option><option value="fail">Fail</option>
              </select>
            </label>
            <label className="model-field">Evidence reference (optional)<input value={verificationReference} onChange={(event) => setVerificationReference(event.target.value)} placeholder="Report URL or document reference" maxLength={1000} /></label>
          </div>
          <label className="model-field">Verification summary<textarea value={verificationSummary} onChange={(event) => setVerificationSummary(event.target.value)} rows={2} maxLength={3000} placeholder="Describe the test, analysis or inspection and its result." /></label>
          <button className="inspect-button model-button" type="button" onClick={createVerificationRecord} disabled={verificationState === "calculating" || !selectedProject.revision.draft.requirements.length}>
            {verificationState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <FileCheck2 size={16} />}
            {verificationState === "calculating" ? "Saving evidence..." : "Add verification evidence"}
          </button>
          <div className="run-list">
            {verificationRecords.map((record) => <div className="run-row" key={record.verification_id}><div className="run-row-main"><strong>{record.requirement_id} · {record.outcome.toUpperCase()}</strong><span>{record.method} · {record.performed_by}</span><small>{record.summary}</small></div></div>)}
            {verificationRecords.length === 0 && <p className="run-empty">No verification evidence recorded for this project.</p>}
          </div>
        </div>}
      </section>

      {selectedProject && <section className="model-panel spacecraft-panel">
        <div className="ingestion-heading"><span className="card-icon"><Layers3 size={20} /></span><div><div className="eyebrow">SPACECRAFT ENGINEERING</div><h2>Component register & budgets</h2></div></div>
        <p className="ingestion-copy">Add user-specified spacecraft components and calculate preliminary mass and average-power totals. Values are not independently verified.</p>
        <div className="model-form">
          <label className="model-field">Component ID<input value={componentId} onChange={(e) => setComponentId(e.target.value)} maxLength={100} /></label>
          <label className="model-field">Component name<input value={componentName} onChange={(e) => setComponentName(e.target.value)} maxLength={160} /></label>
          <label className="model-field">Subsystem<select value={componentSubsystem} onChange={(e) => setComponentSubsystem(e.target.value)}><option value="structure">Structure</option><option value="propulsion">Propulsion</option><option value="power">Power</option><option value="thermal">Thermal</option><option value="avionics">Avionics</option><option value="communications">Communications</option><option value="guidance_navigation_control">GNC</option><option value="payload">Payload</option><option value="mechanisms">Mechanisms</option><option value="other">Other</option></select></label>
        </div>
        <div className="model-form">
          <label className="model-field">Mass <span>kg</span><input type="number" min="0" step="any" value={componentMass} onChange={(e) => setComponentMass(e.target.value)} /></label>
          <label className="model-field">Power draw <span>W · optional</span><input type="number" min="0" step="any" value={componentDraw} onChange={(e) => setComponentDraw(e.target.value)} /></label>
          <label className="model-field">Power generation <span>W · optional</span><input type="number" min="0" step="any" value={componentGeneration} onChange={(e) => setComponentGeneration(e.target.value)} /></label>
        </div>
        <div className="model-form">
          <label className="model-field">Load duty cycle <span>0–1</span><input type="number" min="0" max="1" step="0.01" value={componentLoadDuty} onChange={(e) => setComponentLoadDuty(e.target.value)} /></label>
          <label className="model-field">Generation duty cycle <span>0–1</span><input type="number" min="0" max="1" step="0.01" value={componentGenerationDuty} onChange={(e) => setComponentGenerationDuty(e.target.value)} /></label>
          <label className="model-field">Mass margin <span>%</span><input type="number" min="0" max="100" step="0.1" value={massMargin} onChange={(e) => setMassMargin(e.target.value)} /></label>
        </div>
        <div className="upload-controls"><button className="planet-chip" type="button" onClick={addSpacecraftComponent}>Add component</button><button className="inspect-button" type="button" onClick={saveSpacecraftConfiguration} disabled={spacecraftState === "calculating"}>{spacecraftState === "calculating" ? "Saving..." : spacecraftRecord ? "Save new revision" : "Save configuration"}</button></div>
        {spacecraftComponents.map((item) => <div className="run-row" key={item.component_id}><div className="run-row-main"><strong>{item.component_id} · {item.name}</strong><span>{item.subsystem.replace(/_/g, " ")} · {item.mass.value} kg</span><small>Draw {item.power_draw?.value ?? "—"} W · Generation {item.power_generation?.value ?? "—"} W</small></div></div>)}
        {spacecraftError && <p className="inline-error">{spacecraftError}</p>}
        {spacecraftRecord && <p className="inline-warning">Configuration revision {spacecraftRecord.latest_revision} · Preliminary values only.</p>}
        {spacecraftBudget && <div className="model-result"><div className="result-heading"><CheckCircle2 size={17} /> Preliminary budget summary</div><div className="model-metrics"><div><dt>Component mass</dt><dd>{spacecraftBudget.mass.component_mass_kg.toFixed(2)} <small>kg</small></dd></div><div><dt>Mass incl. margin</dt><dd>{spacecraftBudget.mass.total_with_margin_kg.toFixed(2)} <small>kg</small></dd></div><div><dt>Net average power</dt><dd>{spacecraftBudget.power.net_power_w.toFixed(2)} <small>W</small></dd></div></div><div className="model-meta">Average generation {spacecraftBudget.power.average_generation_w.toFixed(2)} W · Average load {spacecraftBudget.power.average_load_w.toFixed(2)} W</div><div className="model-assumptions"><strong>Limitations</strong><ul>{spacecraftBudget.power.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div></div>}
      </section>}

      {selectedProject && <section className="model-panel traceability-panel">
        <div className="ingestion-heading"><span className="card-icon"><FileCheck2 size={20} /></span><div><div className="eyebrow">SYSTEMS ENGINEERING · REQUIREMENT TRACEABILITY</div><h2>Requirement-to-subsystem matrix</h2></div></div>
        <p className="ingestion-copy">Allocate each mission requirement to one or more components in the latest spacecraft configuration. Allocations record engineering intent; they do not demonstrate compliance.</p>
        {traceabilityMatrix && <div className="model-metrics">
          <div><dt>Total requirements</dt><dd>{traceabilityMatrix.requirement_count}</dd></div>
          <div><dt>Allocated</dt><dd>{traceabilityMatrix.allocated_requirement_count}</dd></div>
          <div><dt>Unallocated</dt><dd>{traceabilityMatrix.unallocated_requirement_count}</dd></div>
        </div>}
        <div className="model-form">
          <label className="model-field">Mission requirement<select value={traceabilityRequirementId} onChange={(e) => setTraceabilityRequirementId(e.target.value)}>
            {selectedProject.revision.draft.requirements.map((item) => <option key={item.requirement_id} value={item.requirement_id}>{item.requirement_id} · {item.title}</option>)}
          </select></label>
          <label className="model-field">Spacecraft component<select value={traceabilityComponentId} onChange={(e) => setTraceabilityComponentId(e.target.value)}>
            {spacecraftComponents.map((item) => <option key={item.component_id} value={item.component_id}>{item.component_id} · {item.name}</option>)}
          </select></label>
        </div>
        <label className="model-field">Allocation rationale<textarea value={traceabilityRationale} onChange={(e) => setTraceabilityRationale(e.target.value)} placeholder="Explain why this component is assigned to the requirement." rows={2} /></label>
        <button className="inspect-button model-button" type="button" onClick={createRequirementAllocation} disabled={traceabilityState === "calculating" || !spacecraftRecord || spacecraftComponents.length === 0 || selectedProject.revision.draft.requirements.length === 0}>
          {traceabilityState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <FileCheck2 size={16} />}
          {traceabilityState === "calculating" ? "Saving allocation..." : "Allocate requirement"}
        </button>
        {traceabilityError && <p className="inline-error">{traceabilityError}</p>}
        {traceabilityMatrix && <div className="run-list">
          {traceabilityMatrix.rows.map((row) => <div className="run-row" key={row.requirement_id}>
            <div className="run-row-main">
              <strong>{row.requirement_id} · {row.requirement_title}</strong>
              <span>{row.allocated ? row.allocation_count + " allocation(s) · " + row.active_component_count + " active component(s)" : "Unallocated requirement"}</span>
              {row.allocations.map((allocation) => <small key={allocation.allocation_id}>{allocation.component_id} — {allocation.rationale}</small>)}
              {row.stale_component_ids.length > 0 && <small className="inline-warning">Stale component references: {row.stale_component_ids.join(", ")}</small>}
              <small>Verification evidence: {row.verification_record_count} record(s) · Pass {row.pass_record_count} · Fail {row.fail_record_count} · Inconclusive {row.inconclusive_record_count}</small>
            </div>
          </div>)}
        </div>}
        {traceabilityMatrix && <div className="model-assumptions"><strong>Interpretation limits</strong><ul>{traceabilityMatrix.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
      </section>}


      {selectedProject && <section className="model-panel revision-impact-panel">
        <div className="ingestion-heading"><span className="card-icon"><Activity size={20} /></span><div><div className="eyebrow">CONFIGURATION CONTROL · CHANGE IMPACT</div><h2>Revision comparison</h2></div></div>
        <p className="ingestion-copy">Compare two immutable mission and spacecraft snapshots. The report identifies changed requirements/components and allocations needing review; it does not decide whether a change is acceptable.</p>
        <div className="model-form">
          <label className="model-field">Baseline mission revision<input type="number" min="1" step="1" value={baselineMissionRevision} onChange={(e) => setBaselineMissionRevision(e.target.value)} /></label>
          <label className="model-field">Target mission revision<input type="number" min="1" step="1" value={targetMissionRevision} onChange={(e) => setTargetMissionRevision(e.target.value)} /></label>
          <label className="model-field">Baseline spacecraft revision<input type="number" min="1" step="1" value={baselineSpacecraftRevision} onChange={(e) => setBaselineSpacecraftRevision(e.target.value)} /></label>
          <label className="model-field">Target spacecraft revision<input type="number" min="1" step="1" value={targetSpacecraftRevision} onChange={(e) => setTargetSpacecraftRevision(e.target.value)} /></label>
        </div>
        <button className="inspect-button model-button" type="button" onClick={analyzeRevisionImpact} disabled={revisionImpactState === "calculating" || !spacecraftRecord}>
          {revisionImpactState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <Activity size={16} />}
          {revisionImpactState === "calculating" ? "Comparing revisions..." : "Analyze change impact"}
        </button>
        {revisionImpactError && <p className="inline-error">{revisionImpactError}</p>}
        {revisionImpact && <div className="model-result">
          <div className="result-heading"><CheckCircle2 size={17} /> Revision comparison report</div>
          <div className="model-metrics">
            <div><dt>Requirement changes</dt><dd>{revisionImpact.requirement_changes.length}</dd></div>
            <div><dt>Component changes</dt><dd>{revisionImpact.component_changes.length}</dd></div>
            <div><dt>Impacted allocations</dt><dd>{revisionImpact.impacted_allocations.length}</dd></div>
          </div>
          <div className="model-assumptions">
            <strong>Requirement changes</strong>
            {revisionImpact.requirement_changes.length ? <ul>{revisionImpact.requirement_changes.map((item) => <li key={item.requirement_id}>{item.requirement_id}: {item.change_type}{item.changed_fields.length ? " · " + item.changed_fields.join(", ") : ""}</li>)}</ul> : <p>No requirement changes in the selected revisions.</p>}
            <strong>Component changes</strong>
            {revisionImpact.component_changes.length ? <ul>{revisionImpact.component_changes.map((item) => <li key={item.component_id}>{item.component_id}: {item.change_type}{item.changed_fields.length ? " · " + item.changed_fields.join(", ") : ""}</li>)}</ul> : <p>No component changes in the selected revisions.</p>}
            <strong>Allocations requiring review</strong>
            {revisionImpact.impacted_allocations.length ? <ul>{revisionImpact.impacted_allocations.map((item) => <li key={item.allocation_id}>{item.requirement_id} → {item.component_id}: {item.impact_reasons.join(", ")}</li>)}</ul> : <p>No current allocations were flagged by this comparison.</p>}
            <strong>Limitations</strong><ul>{revisionImpact.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
        </div>}
      </section>}

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
            <div className="model-meta">Run {modelResult.run_id ?? "not recorded"} · Equation {modelResult.equation_id} · Model {modelResult.model_version}</div>
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
            <div className="model-meta">Run {powerResult.run_id ?? "not recorded"} · Margin fraction {(powerResult.margin_fraction.value * 100).toFixed(2)}% · Equation {powerResult.equation_id} · Model {powerResult.model_version}</div>
            <div className="model-assumptions">
              <strong>Assumptions</strong>
              <ul>{powerResult.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
              <strong>Limitations</strong>
              <ul>{powerResult.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
        )}
      </section>


      <section className="model-panel model-governance-panel">
        <div className="ingestion-heading"><span className="card-icon"><ShieldCheck size={20} /></span><div><div className="eyebrow">MODEL CREDIBILITY · VERIFICATION & VALIDATION</div><h2>Model governance register</h2></div></div>
        <p className="ingestion-copy">Record implementation verification and scientific validation evidence separately. Status is derived from the latest assessment of each type; evidence entries are not independent certification.</p>
        {modelGovernance && <div className="run-list">
          {modelGovernance.models.map((model) => <div className="run-row" key={model.model_id}>
            <div className="run-row-main"><strong>{model.display_name}</strong><span>{model.model_id} · v{model.model_version}</span><small>State: {model.current_state.replace(/_/g, " ")} · {model.assessment_count} assessment(s)</small><small>Verification: {model.latest_verification_outcome ?? "not assessed"} · Validation: {model.latest_validation_outcome ?? "not assessed"}</small></div>
          </div>)}
        </div>}
        <div className="model-form">
          <label className="model-field">Registered model<select value={assessmentModelId} onChange={(e) => setAssessmentModelId(e.target.value)}>{(modelGovernance?.models ?? []).map((model) => <option key={model.model_id} value={model.model_id}>{model.display_name} · v{model.model_version}</option>)}</select></label>
          <label className="model-field">Assessment type<select value={assessmentKind} onChange={(e) => setAssessmentKind(e.target.value as "verification" | "validation")}><option value="verification">Implementation verification</option><option value="validation">Scientific validation</option></select></label>
          <label className="model-field">Outcome<select value={assessmentOutcome} onChange={(e) => setAssessmentOutcome(e.target.value as "pass" | "fail" | "inconclusive")}><option value="pass">Pass</option><option value="fail">Fail</option><option value="inconclusive">Inconclusive</option></select></label>
          <label className="model-field">Method<select value={assessmentMethod} onChange={(e) => setAssessmentMethod(e.target.value)}><option value="test">Test</option><option value="analysis">Analysis</option><option value="comparison">Comparison</option><option value="inspection">Inspection</option><option value="demonstration">Demonstration</option></select></label>
        </div>
        <label className="model-field">Assessment summary<textarea rows={2} value={assessmentSummary} onChange={(e) => setAssessmentSummary(e.target.value)} placeholder="Describe scope, procedure, observed results, and limitations." /></label>
        <label className="model-field">Evidence reference<input value={assessmentReference} onChange={(e) => setAssessmentReference(e.target.value)} placeholder="Report ID, repository path, DOI, or controlled document reference" /></label>
        <button className="inspect-button model-button" type="button" onClick={createModelAssessment} disabled={!modelGovernance || assessmentState === "calculating"}>
          {assessmentState === "calculating" ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}
          {assessmentState === "calculating" ? "Recording assessment..." : "Record model assessment"}
        </button>
        {assessmentError && <p className="inline-error">{assessmentError}</p>}
        {modelGovernance && <div className="model-assumptions"><strong>Governance limits</strong><ul>{modelGovernance.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
      </section>

      <section className="model-panel run-history-panel">
        <div className="ingestion-heading">
          <span className="card-icon"><Database size={20} /></span>
          <div><div className="eyebrow">TRACEABILITY REGISTRY</div><h2>Recent model runs</h2></div>
        </div>
        <p className="ingestion-copy">Successful model calculations are saved with their inputs, outputs, equation IDs, model versions, assumptions and limitations.</p>
        {recentRuns.length === 0 ? (
          <p className="run-empty">No model runs have been recorded yet.</p>
        ) : (
          <div className="run-list">
            {recentRuns.map((run) => (
              <div className="run-row" key={run.run_id}>
                <div className="run-row-main">
                  <strong>{run.model_id}</strong>
                  <span>{run.equation_id} · v{run.model_version}</span>
                  <small>{new Date(run.created_at).toLocaleString()}</small>
                </div>
                <a href={apiBase + "/api/v1/models/runs/" + run.run_id} target="_blank" rel="noreferrer">Open snapshot ↗</a>
              </div>
            ))}
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
        <span>ORBITOPS · MULTI-PLANETARY MISSION ENGINEERING</span>
        <span>EARLY FOUNDATION BUILD · NOT FOR FLIGHT OR OPERATIONAL USE</span>
      </footer>
    </main>
  );
}
