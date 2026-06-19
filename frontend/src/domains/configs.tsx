import type { ColDef, ICellRendererParams, ValueGetterParams } from "ag-grid-community";
import type { DomainKey, TickerItem } from "../store/useAppStore";

type Row = Record<string, any>;
type Severity = TickerItem["severity"];

export interface ActionDescriptor {
  label: string;
  scope: string;
  intent: "danger" | "warn" | "primary";
  path: (row: Row) => string;
  body: (row: Row, fullName: string) => unknown;
}

export interface DomainConfig {
  key: DomainKey;
  title: string;
  subtitle: string;
  idField: string;
  listPath: string;
  columns: ColDef[];
  severityOf: (row: Row) => Severity;
  tickerLabel: (row: Row) => string;
  tickerDetail: (row: Row) => string;
  actions: ActionDescriptor[];
}

const severityColors: Record<Severity, string> = {
  LOW: "#16a34a",
  MEDIUM: "#d97706",
  HIGH: "#ea580c",
  CRITICAL: "#dc2626",
};

function ScoreBar({ value }: { value: number }) {
  const pct = Math.round(value * 1000) / 10;
  const color = value > 0.85 ? "#dc2626" : value > 0.6 ? "#d97706" : "#16a34a";
  return (
    <div style={{ display: "flex", alignItems: "center", height: "100%", gap: 8 }}>
      <span style={{ fontWeight: 700, color, width: 52, fontVariantNumeric: "tabular-nums" }}>{pct}%</span>
      <div style={{ flexGrow: 1, background: "#dbe9f6", height: 6, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ background: color, width: `${pct}%`, height: "100%" }} />
      </div>
    </div>
  );
}

// Light-theme readable severity chips (dark text on a tinted background).
function severityCellStyle(value: string) {
  const map: Record<string, any> = {
    CRITICAL: { color: "#991b1b", backgroundColor: "#fee2e2", fontWeight: 700 },
    HIGH: { color: "#9a3412", backgroundColor: "#ffedd5", fontWeight: 700 },
    MODERATE: { color: "#92400e", backgroundColor: "#fef3c7", fontWeight: 700 },
    MEDIUM: { color: "#92400e", backgroundColor: "#fef3c7", fontWeight: 700 },
    NONE: { color: "#166534", backgroundColor: "#dcfce7" },
    LOW: { color: "#166534", backgroundColor: "#dcfce7" },
  };
  return map[value] ?? {};
}

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);

// ----------------------------------------------------------------------------
// Cyber
// ----------------------------------------------------------------------------
const cyber: DomainConfig = {
  key: "cyber",
  title: "Aegis Threat — Cyber Threat Tower",
  subtitle: "Infrastructure threat intelligence & autonomous remediation",
  idField: "alert_id",
  listPath: "/cyber/alerts",
  columns: [
    { field: "timestamp", headerName: "Timestamp (UTC)", width: 200, sort: "desc" },
    { field: "alert_id", headerName: "Alert ID", width: 150 },
    { field: "target_identifier", headerName: "Target Host", width: 130 },
    { field: "source_ip", headerName: "Source IP", width: 130 },
    { field: "ml_inference.classification", headerName: "Threat Classification", width: 220, filter: true },
    {
      field: "ml_inference.anomaly_score",
      headerName: "Anomaly Score",
      width: 170,
      cellRenderer: (p: ICellRendererParams) => <ScoreBar value={p.value ?? 0} />,
    },
    { field: "severity", headerName: "Severity", width: 110, cellStyle: (p) => severityCellStyle(p.value) },
    { field: "autonomous_remediation.recommended_action", headerName: "Recommended", width: 150 },
    { field: "status", headerName: "Status", width: 150 },
  ],
  severityOf: (r) => (r.severity as Severity) ?? "LOW",
  tickerLabel: (r) => r.ml_inference?.classification ?? "Anomaly",
  tickerDetail: (r) => `${r.source_ip} → ${r.target_identifier}:${r.destination_port}`,
  actions: [
    {
      label: "Isolate Host",
      scope: "cyber:remediate",
      intent: "danger",
      path: (r) => `/cyber/alerts/${r.alert_id}/remediate`,
      body: () => ({ action: "ISOLATE_HOST" }),
    },
    {
      label: "Block Source IP",
      scope: "cyber:remediate",
      intent: "warn",
      path: (r) => `/cyber/alerts/${r.alert_id}/remediate`,
      body: () => ({ action: "BLOCK_IP" }),
    },
    {
      label: "Invalidate Sessions",
      scope: "cyber:remediate",
      intent: "primary",
      path: (r) => `/cyber/alerts/${r.alert_id}/remediate`,
      body: () => ({ action: "INVALIDATE_SESSIONS" }),
    },
  ],
};

// ----------------------------------------------------------------------------
// Health
// ----------------------------------------------------------------------------
const health: DomainConfig = {
  key: "health",
  title: "Aegis Clinical — Clinical Support Hub",
  subtitle: "Medication reconciliation & contraindication decision support",
  idField: "reconciliation_id",
  listPath: "/health/clinical/reports",
  columns: [
    {
      headerName: "Verify",
      field: "human_verified",
      width: 80,
      pinned: "left",
      cellRenderer: (p: ICellRendererParams) => (p.value ? "✔" : "—"),
    },
    { field: "patient_id", headerName: "Patient", width: 150 },
    { field: "proposed_action.medication_display", headerName: "Proposed Rx", width: 160 },
    {
      headerName: "Interacting Compound",
      width: 200,
      valueGetter: (p: ValueGetterParams) => {
        const cds = p.data?.clinical_decision_support;
        if (!cds?.contraindication_detected) return "None";
        return `Conflict: ${cds.interacting_medication}`;
      },
    },
    {
      field: "clinical_decision_support.severity_index",
      headerName: "Risk Level",
      width: 140,
      cellStyle: (p) => severityCellStyle(p.value),
    },
    { field: "status", headerName: "Status", width: 170 },
    { field: "evaluation_timestamp", headerName: "Evaluated (UTC)", width: 200, sort: "desc" },
  ],
  severityOf: (r) => {
    const s = r.clinical_decision_support?.severity_index;
    if (s === "CRITICAL") return "CRITICAL";
    if (s === "MODERATE") return "MEDIUM";
    return "LOW";
  },
  tickerLabel: (r) => `${r.proposed_action?.medication_display ?? "Rx"} → ${r.patient_id}`,
  tickerDetail: (r) =>
    r.clinical_decision_support?.contraindication_detected
      ? `${r.clinical_decision_support.severity_index}: ${r.clinical_decision_support.fda_adverse_event_summary?.primary_co_manifestation_consequence}`
      : "No contraindication",
  actions: [
    {
      label: "Acknowledge & Sign Override",
      scope: "clinical:write",
      intent: "danger",
      path: (r) => `/health/clinical/reports/${r.reconciliation_id}/override`,
      body: (_r, fullName) => ({ acknowledge_override: true, clinician_signature: fullName }),
    },
  ],
};

// ----------------------------------------------------------------------------
// FinTech
// ----------------------------------------------------------------------------
const fintech: DomainConfig = {
  key: "fintech",
  title: "Aegis Ledger — FinTech Transaction Radar",
  subtitle: "AML / sanctions screening & fraud risk scoring",
  idField: "assessment_id",
  listPath: "/fintech/assessments",
  columns: [
    { field: "associated_transaction_id", headerName: "Transaction ID", width: 160 },
    { field: "originating_account", headerName: "Origin", width: 150 },
    { field: "destination_account", headerName: "Destination", width: 160 },
    { field: "beneficiary_jurisdiction_country", headerName: "Jx", width: 70 },
    {
      field: "amount",
      headerName: "Amount (USD)",
      width: 150,
      valueFormatter: (p) => (p.value != null ? currency(p.value) : ""),
      cellStyle: { textAlign: "right", fontFamily: "monospace" },
    },
    {
      field: "compliance_decision.risk_score",
      headerName: "Fraud Risk",
      width: 160,
      cellRenderer: (p: ICellRendererParams) => <ScoreBar value={p.value ?? 0} />,
    },
    { field: "compliance_decision.action_protocol", headerName: "Action", width: 220 },
    { field: "status", headerName: "Status", width: 140 },
  ],
  severityOf: (r) => {
    const s = r.compliance_decision?.risk_score ?? 0;
    if (s > 0.85) return "CRITICAL";
    if (s > 0.7) return "HIGH";
    if (s > 0.4) return "MEDIUM";
    return "LOW";
  },
  tickerLabel: (r) => r.compliance_decision?.action_protocol ?? "Transaction",
  tickerDetail: (r) => `${currency(r.amount ?? 0)} → ${r.beneficiary_jurisdiction_country}`,
  actions: [
    {
      label: "Release Hold",
      scope: "fintech:transact",
      intent: "primary",
      path: (r) => `/fintech/assessments/${r.assessment_id}/action`,
      body: () => ({ action: "RELEASE_HOLD" }),
    },
    {
      label: "Freeze Beneficiary Assets",
      scope: "fintech:transact",
      intent: "danger",
      path: (r) => `/fintech/assessments/${r.assessment_id}/action`,
      body: () => ({ action: "FREEZE_ASSETS" }),
    },
    {
      label: "File SAR",
      scope: "fintech:transact",
      intent: "warn",
      path: (r) => `/fintech/assessments/${r.assessment_id}/action`,
      body: () => ({ action: "FILE_SAR" }),
    },
  ],
};

export const DOMAIN_CONFIGS: Record<DomainKey, DomainConfig> = { cyber, health, fintech };
export { severityColors };
