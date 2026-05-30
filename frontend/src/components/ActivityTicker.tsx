import { useMemo } from "react";
import { useAppStore, type DomainKey } from "../store/useAppStore";
import { severityColors } from "../domains/configs";

export function ActivityTicker({ domain }: { domain: DomainKey }) {
  // Subscribe to the stable array reference, then derive with useMemo. Filtering
  // inside the selector would return a new array each render, breaking zustand's
  // snapshot caching and causing an infinite update loop.
  const allTicker = useAppStore((s) => s.ticker);
  const ticker = useMemo(() => allTicker.filter((t) => t.domain === domain), [allTicker, domain]);

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
