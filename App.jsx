import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const NAV   = "#002B5C";
const RED   = "#E8192C";
const GREEN = "#16a34a";
const AMBER = "#d97706";

const pill = (status) => {
  const map = {
    success: { bg: "#dcfce7", color: "#15803d", label: "✓ Succès" },
    error:   { bg: "#fee2e2", color: "#b91c1c", label: "✕ Erreur" },
    running: { bg: "#fef9c3", color: "#92400e", label: "⟳ En cours" },
  };
  const s = map[status] || { bg: "#f1f5f9", color: "#475569", label: status };
  return (
    <span style={{ background: s.bg, color: s.color, borderRadius: 20, padding: "2px 10px", fontSize: 12, fontWeight: 600 }}>
      {s.label}
    </span>
  );
};

// ─── Sub-components ────────────────────────────────────────────────────────────

function Card({ title, children, style = {} }) {
  return (
    <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 20, ...style }}>
      {title && <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700, color: NAV }}>{title}</h3>}
      {children}
    </div>
  );
}

function Input({ label, value, onChange, type = "text", placeholder = "", hint = "" }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 4 }}>{label}</label>
      <input
        type={type}
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: "100%", boxSizing: "border-box", padding: "8px 12px",
          border: "1px solid #cbd5e1", borderRadius: 8, fontSize: 14,
          outline: "none", fontFamily: "inherit",
        }}
      />
      {hint && <p style={{ margin: "4px 0 0", fontSize: 12, color: "#94a3b8" }}>{hint}</p>}
    </div>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 4 }}>{label}</label>
      <select
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        style={{
          width: "100%", padding: "8px 12px", border: "1px solid #cbd5e1",
          borderRadius: 8, fontSize: 14, background: "#fff", fontFamily: "inherit",
        }}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function Btn({ children, onClick, color = NAV, disabled = false, small = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? "#94a3b8" : color,
        color: "#fff", border: "none", borderRadius: 8,
        padding: small ? "6px 14px" : "10px 22px",
        fontSize: small ? 13 : 14, fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit",
      }}
    >
      {children}
    </button>
  );
}

// ─── Pages ─────────────────────────────────────────────────────────────────────

function Dashboard({ status, onRun, running }) {
  const last = status?.last_run;
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 20 }}>
        {[
          { label: "Statut scheduler", value: status?.scheduler_running ? "🟢 Actif" : "⚫ Arrêté" },
          { label: "Site cible", value: status?.target_url ? new URL(status.target_url).hostname : "—" },
          { label: "Intervalle", value: status?.auto_run ? `${status.interval_hours}h` : "Manuel" },
          { label: "Cycles effectués", value: status?.total_runs ?? 0 },
        ].map(stat => (
          <div key={stat.label} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "16px 20px" }}>
            <p style={{ margin: 0, fontSize: 12, color: "#94a3b8", fontWeight: 600, textTransform: "uppercase", letterSpacing: .5 }}>{stat.label}</p>
            <p style={{ margin: "6px 0 0", fontSize: 20, fontWeight: 700, color: NAV }}>{stat.value}</p>
          </div>
        ))}
      </div>

      <Card title="Contrôle manuel">
        <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: 14 }}>
          Lance un cycle complet : découverte des formulaires → soumission → récupération leads → export Excel.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Btn onClick={onRun} disabled={running || !status?.target_url} color={NAV}>
            {running ? "⟳ En cours..." : "▶ Lancer le bot"}
          </Btn>
          <a href={`${API}/api/download`} target="_blank" rel="noreferrer">
            <Btn color={GREEN} small>⬇ Télécharger Excel</Btn>
          </a>
        </div>
        {!status?.target_url && (
          <p style={{ margin: "12px 0 0", fontSize: 13, color: RED }}>⚠ Configure un site cible dans l'onglet Config d'abord.</p>
        )}
      </Card>

      {last && (
        <Card title="Dernier cycle">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
            {[
              { label: "Statut",            value: pill(last.status) },
              { label: "Pages scannées",    value: last.pages_scanned ?? "—" },
              { label: "Formulaires trouvés", value: last.forms_found },
              { label: "Soumissions",       value: last.forms_submitted },
              { label: "Leads récupérés",   value: last.leads_fetched },
              { label: "Démarré",           value: last.started_at?.slice(11, 19) },
            ].map(s => (
              <div key={s.label} style={{ background: "#f8fafc", borderRadius: 8, padding: "10px 14px" }}>
                <p style={{ margin: 0, fontSize: 11, color: "#94a3b8", fontWeight: 600, textTransform: "uppercase" }}>{s.label}</p>
                <p style={{ margin: "4px 0 0", fontSize: 16, fontWeight: 700, color: "#1e293b" }}>{s.value}</p>
              </div>
            ))}
          </div>
          {last.error && (
            <div style={{ marginTop: 12, background: "#fee2e2", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#b91c1c" }}>
              <strong>Erreur:</strong> {last.error}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function ConfigPage({ cfg, onChange, onSave, saved }) {
  const backend = cfg.backend_type || "none";

  return (
    <div>
      <Card title="🌐 Site cible">
        <Input label="URL du site" value={cfg.target_url} onChange={v => onChange("target_url", v)}
          placeholder="https://example.com" hint="Le bot va scanner toutes les pages de ce site à la recherche de formulaires." />
        <Input label="Nom du projet" value={cfg.project_name} onChange={v => onChange("project_name", v)}
          placeholder="Mon Projet" />
      </Card>

      <Card title="⚙️ Scheduler">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <Select label="Mode" value={cfg.auto_run ? "auto" : "manual"}
              onChange={v => onChange("auto_run", v === "auto")}
              options={[{ value: "manual", label: "Manuel (POST /api/run)" }, { value: "auto", label: "Automatique (scheduler)" }]} />
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <Input label="Intervalle (heures)" value={cfg.interval_hours} type="number"
              onChange={v => onChange("interval_hours", parseInt(v) || 6)}
              hint="Actif seulement en mode automatique." />
          </div>
        </div>
      </Card>

      <Card title="🗄️ Backend (récupération leads)">
        <Select label="Type de backend" value={backend} onChange={v => onChange("backend_type", v)}
          options={[
            { value: "none",              label: "Aucun (soumission seulement)" },
            { value: "netlify",           label: "Netlify Forms" },
            { value: "supabase",          label: "Supabase" },
            { value: "firebase",          label: "Firebase Firestore" },
            { value: "confirmation_page", label: "Scraper page de confirmation" },
          ]} />

        {backend === "netlify" && (
          <div style={{ background: "#f8fafc", borderRadius: 8, padding: 16, marginTop: 4 }}>
            <Input label="Netlify Token" value={cfg.netlify_token} onChange={v => onChange("netlify_token", v)}
              placeholder="nfp_xxxx" hint="User Settings → Applications → New access token" />
            <Input label="Site ID" value={cfg.netlify_site_id} onChange={v => onChange("netlify_site_id", v)}
              placeholder="abc123" hint="Site Settings → General → Site ID" />
            <Input label="Nom du formulaire" value={cfg.netlify_form_name} onChange={v => onChange("netlify_form_name", v)}
              placeholder="contact" hint="Attribut name de la balise <form>" />
          </div>
        )}

        {backend === "supabase" && (
          <div style={{ background: "#f8fafc", borderRadius: 8, padding: 16, marginTop: 4 }}>
            <Input label="Supabase URL" value={cfg.supabase_url} onChange={v => onChange("supabase_url", v)}
              placeholder="https://xxx.supabase.co" />
            <Input label="Anon Key" value={cfg.supabase_key} onChange={v => onChange("supabase_key", v)}
              placeholder="eyJ..." />
            <Input label="Table" value={cfg.supabase_table} onChange={v => onChange("supabase_table", v)}
              placeholder="leads" />
          </div>
        )}

        {backend === "firebase" && (
          <div style={{ background: "#f8fafc", borderRadius: 8, padding: 16, marginTop: 4 }}>
            <Input label="Project ID" value={cfg.firebase_project} onChange={v => onChange("firebase_project", v)}
              placeholder="my-project-id" />
            <Input label="Collection" value={cfg.firebase_collection} onChange={v => onChange("firebase_collection", v)}
              placeholder="leads" />
            <Input label="API Key (optionnel)" value={cfg.firebase_api_key} onChange={v => onChange("firebase_api_key", v)}
              placeholder="AIza..." />
          </div>
        )}

        {backend === "confirmation_page" && (
          <div style={{ background: "#f8fafc", borderRadius: 8, padding: 16, marginTop: 4 }}>
            <Input label="URL de confirmation" value={cfg.confirmation_url} onChange={v => onChange("confirmation_url", v)}
              placeholder="https://example.com/merci" hint="Page affichée après soumission du formulaire." />
          </div>
        )}
      </Card>

      <Card title="📄 Export">
        <Input label="Nom du fichier Excel" value={cfg.export_filename} onChange={v => onChange("export_filename", v)}
          placeholder="leads" hint="Généré comme: leads_20240601_120000.xlsx" />
      </Card>

      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <Btn onClick={onSave} color={NAV}>💾 Sauvegarder la config</Btn>
        {saved && <span style={{ color: GREEN, fontSize: 14, fontWeight: 600 }}>✓ Sauvegardé</span>}
      </div>
    </div>
  );
}

function HistoryPage({ history }) {
  if (!history.length) return (
    <Card><p style={{ color: "#94a3b8", textAlign: "center", margin: 0 }}>Aucun cycle effectué pour l'instant. Lance le bot depuis Dashboard.</p></Card>
  );
  return (
    <div>
      {history.map(run => (
        <Card key={run.id} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {pill(run.status)}
                <span style={{ fontSize: 13, color: "#64748b" }}>{run.started_at?.slice(0, 19).replace("T", " ")}</span>
              </div>
              <p style={{ margin: "6px 0 0", fontSize: 13, color: NAV, fontWeight: 600 }}>{run.target}</p>
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
              <span>🔍 <strong>{run.forms_found}</strong> forms</span>
              <span>📤 <strong>{run.forms_submitted}</strong> soumissions</span>
              <span>📋 <strong>{run.leads_fetched}</strong> leads</span>
            </div>
          </div>
          {run.error && (
            <div style={{ marginTop: 10, background: "#fee2e2", borderRadius: 6, padding: "8px 12px", fontSize: 12, color: "#b91c1c" }}>
              {run.error}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

function LeadsPage() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/leads`)
      .then(r => r.json())
      .then(data => { setLeads(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <Card><p style={{ textAlign: "center", color: "#94a3b8" }}>Chargement...</p></Card>;
  if (!leads.length) return <Card><p style={{ textAlign: "center", color: "#94a3b8" }}>Aucun lead disponible. Configure un backend et lance le bot.</p></Card>;

  const cols = ["date", "nom", "prenom", "email", "telephone", "code_postal", "assurance", "source"];
  return (
    <Card title={`${leads.length} leads`}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: NAV }}>
              {cols.map(c => (
                <th key={c} style={{ color: "#fff", padding: "8px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>
                  {c.replace("_", " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {leads.map((lead, i) => (
              <tr key={lead.id || i} style={{ background: i % 2 === 0 ? "#f8fafc" : "#fff" }}>
                {cols.map(c => (
                  <td key={c} style={{ padding: "7px 12px", borderBottom: "1px solid #e2e8f0", color: "#1e293b", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {lead[c] || "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 14 }}>
        <a href={`${API}/api/download`} target="_blank" rel="noreferrer">
          <Btn color={GREEN} small>⬇ Télécharger Excel</Btn>
        </a>
      </div>
    </Card>
  );
}

// ─── Main App ──────────────────────────────────────────────────────────────────

const TABS = ["Dashboard", "Config", "Leads", "Historique"];

export default function App() {
  const [tab, setTab]       = useState("Dashboard");
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [cfg, setCfg]       = useState(null);
  const [saved, setSaved]   = useState(false);
  const [running, setRunning] = useState(false);

  const fetchStatus = useCallback(() => {
    fetch(`${API}/api/status`).then(r => r.json()).then(setStatus).catch(() => {});
    fetch(`${API}/api/history`).then(r => r.json()).then(setHistory).catch(() => {});
  }, []);

  const fetchConfig = useCallback(() => {
    fetch(`${API}/api/config`).then(r => r.json()).then(setCfg).catch(() => {});
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchConfig();
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, [fetchStatus, fetchConfig]);

  const handleRun = async () => {
    setRunning(true);
    await fetch(`${API}/api/run`, { method: "POST" });
    setTimeout(() => { fetchStatus(); setRunning(false); }, 3000);
  };

  const handleConfigChange = (key, val) => {
    setCfg(prev => ({ ...prev, [key]: val }));
    setSaved(false);
  };

  const handleSave = async () => {
    await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    setSaved(true);
    fetchStatus();
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f1f5f9", fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{ background: NAV, padding: "0 32px", display: "flex", alignItems: "center", gap: 32 }}>
        <div style={{ padding: "16px 0", color: "#fff" }}>
          <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: -.3 }}>🤖 Universal Form Bot</span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              background: tab === t ? "rgba(255,255,255,.15)" : "transparent",
              color: tab === t ? "#fff" : "rgba(255,255,255,.6)",
              border: "none", padding: "20px 16px", fontSize: 14, fontWeight: 600,
              cursor: "pointer", fontFamily: "inherit", borderBottom: tab === t ? `2px solid ${RED}` : "2px solid transparent",
            }}>
              {t}
            </button>
          ))}
        </div>
        {status?.scheduler_running && (
          <div style={{ marginLeft: "auto", color: "#86efac", fontSize: 13, fontWeight: 600 }}>
            ● Scheduler actif · {status.interval_hours}h
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "28px 24px" }}>
        {tab === "Dashboard"   && <Dashboard status={status} onRun={handleRun} running={running} />}
        {tab === "Config"      && cfg && <ConfigPage cfg={cfg} onChange={handleConfigChange} onSave={handleSave} saved={saved} />}
        {tab === "Leads"       && <LeadsPage />}
        {tab === "Historique"  && <HistoryPage history={history} />}
      </div>
    </div>
  );
}
