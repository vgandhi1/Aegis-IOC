import { useState } from "react";
import { api } from "../api/client";
import { useAppStore, type DomainKey } from "../store/useAppStore";
import { DOMAIN_CONFIGS, type ActionDescriptor } from "../domains/configs";

function aiNarrative(domain: DomainKey, row: Record<string, any>): { summary: string; citation?: string } {
  if (domain === "cyber") {
    return {
      summary:
        row.triage ??
        `Tier-1 classifier flagged "${row.ml_inference?.classification}" at ${(
          (row.ml_inference?.anomaly_score ?? 0) * 100
        ).toFixed(1)}% anomaly confidence. MITRE: ${row.ml_inference?.mitre_attack_mapping?.technique}.`,
      citation: row.ml_inference?.mitre_attack_mapping
        ? `${row.ml_inference.mitre_attack_mapping.tactic} / ${row.ml_inference.mitre_attack_mapping.sub_technique}`
        : undefined,
    };
  }
  if (domain === "health") {
    const cds = row.clinical_decision_support;
    if (!cds?.contraindication_detected)
      return { summary: "No contraindication detected against the patient's active medications." };
    return {
      summary: `${cds.severity_index}: co-administration with ${cds.interacting_medication} is associated with ${cds.fda_adverse_event_summary?.primary_co_manifestation_consequence} (odds ratio ${cds.fda_adverse_event_summary?.odds_ratio_increase}× across ${cds.fda_adverse_event_summary?.total_matching_case_reports?.toLocaleString()} reports).`,
      citation: cds.evidence_grounding?.peer_reviewed_guideline_citation,
    };
  }
  const g = row.nlp_compliance_grounding;
  return {
    summary: g?.contextual_summary ?? "No compliance summary available.",
    citation: g?.sanction_list_hits?.[0]
      ? `${g.sanction_list_hits[0].list_name}: ${g.sanction_list_hits[0].matched_term} (${(
          g.sanction_list_hits[0].confidence_match_score * 100
        ).toFixed(1)}% match)`
      : undefined,
  };
}

export function ContextPanel({ domain }: { domain: DomainKey }) {
  const config = DOMAIN_CONFIGS[domain];
  const row = useAppStore((s) => s.selected[domain]);
  const token = useAppStore((s) => s.token);
  const identity = useAppStore((s) => s.identity);
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!row) {
    return (
      <aside className="pane pane-right">
        <div className="pane-header">Investigation</div>
        <div className="empty-hint">Select a row to inspect details, AI grounding, and actions.</div>
      </aside>
    );
  }

  const narrative = aiNarrative(domain, row);
  const availableActions = config.actions.filter((a) => identity?.scopes.includes(a.scope));

  const runAction = async (action: ActionDescriptor) => {
    if (!token) return;
    setBusy(action.label);
    setFeedback(null);
    try {
      const res: any = await api.post(action.path(row), action.body(row, identity?.full_name ?? "operator"), token);
      setFeedback(`${action.label}: ${res.status ?? "done"}`);
    } catch (err: any) {
      setFeedback(`Failed: ${err?.message ?? "error"}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <aside className="pane pane-right">
      <div className="pane-header">Investigation Node</div>

      <section className="ctx-block">
        <h4>AI Assessment</h4>
        <p className="ctx-summary">{narrative.summary}</p>
        {narrative.citation && (
          <p className="ctx-citation">
            <span>Grounding</span> {narrative.citation}
          </p>
        )}
      </section>

      {availableActions.length > 0 && (
        <section className="ctx-block">
          <h4>Action Overrides</h4>
          <div className="ctx-actions">
            {availableActions.map((a) => (
              <button
                key={a.label}
                className={`action-btn action-${a.intent}`}
                disabled={busy !== null}
                onClick={() => runAction(a)}
              >
                {busy === a.label ? "Working…" : a.label}
              </button>
            ))}
          </div>
          {feedback && <div className="ctx-feedback">{feedback}</div>}
        </section>
      )}

      <section className="ctx-block">
        <h4>Raw Record</h4>
        <pre className="ctx-json">{JSON.stringify(row, null, 2)}</pre>
      </section>
    </aside>
  );
}
