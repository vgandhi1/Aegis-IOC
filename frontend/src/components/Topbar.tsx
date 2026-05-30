import { useAppStore, type DomainKey } from "../store/useAppStore";
import { DOMAIN_CONFIGS } from "../domains/configs";

const TAB_LABELS: Record<DomainKey, string> = {
  cyber: "Aegis Threat",
  health: "Aegis Clinical",
  fintech: "Aegis Ledger",
};

export function Topbar() {
  const identity = useAppStore((s) => s.identity);
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const logout = useAppStore((s) => s.logout);

  if (!identity) return null;
  const tabs = identity.tabs.filter((t): t is DomainKey => t in DOMAIN_CONFIGS);

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="brand-mark">◆</span>
        <span className="brand-name">Aegis IOC</span>
      </div>

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </nav>

      <div className="topbar-user">
        <div className="user-meta">
          <span className="user-name">{identity.full_name}</span>
          <span className="user-role">{identity.role.replace(/_/g, " ")}</span>
        </div>
        <button className="logout" onClick={logout}>
          Sign Out
        </button>
      </div>
    </header>
  );
}
