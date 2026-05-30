import { Login } from "./auth/Login";
import { Topbar } from "./components/Topbar";
import { DomainWorkspace } from "./components/DomainWorkspace";
import { useAppStore } from "./store/useAppStore";

export default function App() {
  const token = useAppStore((s) => s.token);
  const activeTab = useAppStore((s) => s.activeTab);

  if (!token) return <Login />;

  return (
    <div className="app-shell">
      <Topbar />
      <main className="app-main">
        {activeTab ? (
          <DomainWorkspace key={activeTab} domain={activeTab} />
        ) : (
          <div className="empty-hint centered">No accessible modules for this role.</div>
        )}
      </main>
    </div>
  );
}
