import { useState } from "react";
import { useAppStore } from "../store/useAppStore";

const DEMO_ACCOUNTS = [
  { username: "analyst", label: "Security Analyst", domains: "Cyber" },
  { username: "clinician", label: "Clinical Provider", domains: "Health" },
  { username: "officer", label: "Compliance Officer", domains: "FinTech" },
  { username: "governor", label: "Governance Board", domains: "All domains" },
];

export function Login() {
  const login = useAppStore((s) => s.login);
  const loading = useAppStore((s) => s.loading);
  const authError = useAppStore((s) => s.authError);
  const [username, setUsername] = useState("governor");
  const [password, setPassword] = useState("demo");

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-mark">◆</span>
          <div>
            <h1>Aegis IOC</h1>
            <p>Tri-Domain Institutional Operations Center</p>
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            login(username, password);
          }}
        >
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {authError && <div className="login-error">{authError}</div>}
          <button type="submit" disabled={loading}>
            {loading ? "Authenticating…" : "Sign In"}
          </button>
        </form>

        <div className="demo-accounts">
          <span className="demo-title">Demo roles (password: demo)</span>
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.username}
              className="demo-chip"
              onClick={() => {
                setUsername(a.username);
                setPassword("demo");
              }}
            >
              <strong>{a.label}</strong>
              <span>{a.domains}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
