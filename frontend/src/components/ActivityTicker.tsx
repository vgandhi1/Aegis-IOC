import { useAppStore, type DomainKey } from "../store/useAppStore";
import { severityColors } from "../domains/configs";

export function ActivityTicker({ domain }: { domain: DomainKey }) {
  const ticker = useAppStore((s) => s.ticker.filter((t) => t.domain === domain));

  return (
    <aside className="pane pane-left">
      <div className="pane-header">
        <span>Live Activity</span>
        <span className="pane-count">{ticker.length}</span>
      </div>
      <div className="ticker-stream">
        {ticker.length === 0 && <div className="empty-hint">Waiting for live events…</div>}
        {ticker.map((item) => (
          <div
            key={item.id}
            className="ticker-item"
            style={{ borderLeftColor: severityColors[item.severity] }}
          >
            <div className="ticker-top">
              <span className="ticker-label">{item.label}</span>
              <span className="ticker-sev" style={{ color: severityColors[item.severity] }}>
                {item.severity}
              </span>
            </div>
            <div className="ticker-detail">{item.detail}</div>
            <div className="ticker-time">{new Date(item.ts).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>
    </aside>
  );
}
