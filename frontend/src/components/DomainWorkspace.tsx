import { useEffect, useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import type { GetRowIdParams, GridReadyEvent, RowClickedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { api } from "../api/client";
import { subscribeStream } from "../api/ws";
import { useAppStore, type DomainKey, type TickerItem } from "../store/useAppStore";
import { DOMAIN_CONFIGS } from "../domains/configs";
import { ActivityTicker } from "./ActivityTicker";
import { ContextPanel } from "./ContextPanel";

export function DomainWorkspace({ domain }: { domain: DomainKey }) {
  const config = DOMAIN_CONFIGS[domain];
  const token = useAppStore((s) => s.token);
  const rows = useAppStore((s) => s.data[domain]);
  const upsert = useAppStore((s) => s.upsert);
  const pushTicker = useAppStore((s) => s.pushTicker);
  const selectRow = useAppStore((s) => s.selectRow);
  const gridRef = useRef<AgGridReact>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    api
      .list<Record<string, any>>(config.listPath, token)
      .then((initial) => {
        if (!cancelled) upsert(domain, config.idField, initial);
      })
      .catch(() => undefined);

    const dispose = subscribeStream(domain, token, (msg) => {
      if (cancelled || !msg.batch?.length) return;
      const rows = msg.batch.filter((r) => r && r[config.idField] !== undefined);
      upsert(domain, config.idField, rows);
      if (!msg.snapshot) {
        const items: TickerItem[] = rows.map((r) => ({
          id: `${r[config.idField]}-${r._event ?? "new"}`,
          domain,
          label: config.tickerLabel(r),
          detail: config.tickerDetail(r),
          severity: config.severityOf(r),
          ts: Date.now(),
        }));
        pushTicker(items);
      }
    });

    return () => {
      cancelled = true;
      dispose();
    };
  }, [domain, token, config, upsert, pushTicker]);

  const defaultColDef = useMemo(
    () => ({ resizable: true, sortable: true, filter: true, suppressHeaderMenuButton: true }),
    [],
  );

  const getRowId = useMemo(() => (p: GetRowIdParams) => String(p.data[config.idField]), [config.idField]);

  return (
    <div className="workspace">
      <ActivityTicker domain={domain} />

      <section className="pane pane-center">
        <div className="pane-header">
          <div>
            <span className="pane-title">{config.title}</span>
            <span className="pane-subtitle">{config.subtitle}</span>
          </div>
          <span className="pane-count">{rows.length} records</span>
        </div>
        <div className="ag-theme-quartz-dark grid-host">
          <AgGridReact
            ref={gridRef}
            rowData={rows}
            columnDefs={config.columns}
            defaultColDef={defaultColDef}
            getRowId={getRowId}
            animateRows
            rowSelection={{ mode: "singleRow", checkboxes: false, enableClickSelection: true }}
            onRowClicked={(e: RowClickedEvent) => selectRow(domain, e.data)}
            onGridReady={(e: GridReadyEvent) => e.api.sizeColumnsToFit()}
          />
        </div>
      </section>

      <ContextPanel domain={domain} />
    </div>
  );
}
