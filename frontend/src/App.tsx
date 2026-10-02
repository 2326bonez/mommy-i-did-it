import { useEffect, useState } from "react";
import { api, isLoggedIn, setToken, type Project, type Requirement } from "./api";

type Route = { name: "login" } | { name: "signup" } | { name: "dashboard" } | { name: "project"; id: string };

const STAGES = ["idea", "plan", "build", "test", "evidence", "verify", "protect", "release", "publish", "own"];

function useRoute(): [Route, (r: Route) => void] {
  const parse = (): Route => {
    const h = window.location.hash;
    if (h.startsWith("#/project/")) return { name: "project", id: h.slice(11) };
    if (h === "#/signup") return { name: "signup" };
    if (h === "#/login") return { name: "login" };
    return { name: "dashboard" };
  };
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const fn = () => setRoute(parse());
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);
  return [route, (r: Route) => {
    setRoute(r);
    window.location.hash =
      r.name === "project" ? `#/project/${r.id}` : r.name === "dashboard" ? "#/" : `#/${r.name}`;
  }];
}

function Topbar({ user, onLogout }: { user: any; onLogout: () => void }) {
  return (
    <div className="topbar">
      <div className="brand" onClick={() => (window.location.hash = "#/")}>
        💀 Mommy I Did It<small>BUILD IT • TUNE IT • FINISH IT</small>
      </div>
      <div className="who">
        {user && (
          <>
            <span>{user.display_name}</span>
            <button className="btn small" onClick={onLogout}>Log out</button>
          </>
        )}
      </div>
    </div>
  );
}

function AuthPage({ mode, go }: { mode: "login" | "signup"; go: (r: Route) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const data = mode === "login"
        ? await api.login(email, password)
        : await api.signup(email, password, name);
      setToken(data.token);
      go({ name: "dashboard" });
    } catch (e: any) {
      setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <div className="auth-wrap">
        <h1>{mode === "login" ? "Welcome back" : "Start building"}</h1>
        <p className="sub">💀 Mommy I Did It — Build It • Tune It • Finish It 🔥</p>
        {err && <div className="err">{err}</div>}
        <form onSubmit={submit}>
          {mode === "signup" && (
            <div className="field">
              <label>Display name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Bonez" />
            </div>
          )}
          <div className="field">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={mode === "signup" ? "8+ characters" : "••••••••"} required />
          </div>
          <button className="btn primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? <><span className="spin" />Working…</> : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
        <p style={{ marginTop: 16, color: "#999", fontSize: ".9rem" }}>
          {mode === "login" ? (
            <>No account? <a href="#/signup">Sign up</a></>
          ) : (
            <>Have an account? <a href="#/login">Log in</a></>
          )}
        </p>
      </div>
    </div>
  );
}

function Dashboard({ go }: { go: (r: Route) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [err, setErr] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try { setProjects((await api.projects()).projects); }
    catch (e: any) { setErr(e.message); }
  };
  useEffect(() => { load(); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const { project } = await api.createProject(name, idea, "");
      setName(""); setIdea(""); setShowNew(false);
      go({ name: "project", id: project.id });
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="page">
      <div className="hero">
        <h1>💀 What are we building?</h1>
        <p>Describe your app idea. AI turns it into a real plan.</p>
      </div>
      <div className="row" style={{ marginBottom: 20 }}>
        <div className="spacer" />
        <button className="btn primary" onClick={() => setShowNew(!showNew)}>
          {showNew ? "Cancel" : "+ New project"}
        </button>
      </div>
      {err && <div className="err">{err}</div>}
      {showNew && (
        <div className="card">
          <form onSubmit={create}>
            <div className="field">
              <label>Project name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Awesome App" required />
            </div>
            <div className="field">
              <label>Your idea — describe it in plain language</label>
              <textarea value={idea} onChange={(e) => setIdea(e.target.value)} placeholder="An app that…" required />
            </div>
            <button className="btn primary" disabled={busy || idea.trim().length < 20}>
              {busy ? <><span className="spin" />Creating…</> : "Create project"}
            </button>
            {idea.trim().length > 0 && idea.trim().length < 20 && (
              <p style={{ color: "#999", fontSize: ".8rem", marginTop: 8 }}>Give a little more detail (20+ characters).</p>
            )}
          </form>
        </div>
      )}
      {projects.length === 0 && !showNew ? (
        <div className="empty">
          <div className="big">🛠️</div>
          <p>No projects yet. Hit <b>+ New project</b> and let's build something.</p>
        </div>
      ) : (
        projects.map((p) => (
          <div key={p.id} className="card clickable" onClick={() => go({ name: "project", id: p.id })}>
            <div className="row">
              <h3>{p.name}</h3>
              <div className="spacer" />
              <span className={`stage ${p.lifecycle_stage}`}>{p.lifecycle_stage}</span>
            </div>
            <p style={{ marginTop: 8 }}>{p.idea_text.slice(0, 160)}{p.idea_text.length > 160 ? "…" : ""}</p>
          </div>
        ))
      )}
    </div>
  );
}

function RequirementCard({ r }: { r: Requirement }) {
  return (
    <div className="card req">
      <div className="req-head">
        <span className="req-code">{r.req_code}</span>
        <h4>{r.title}</h4>
      </div>
      <p>{r.description}</p>
      <dl>
        <dt>Acceptance criteria</dt>
        <dd>{r.acceptance_criteria}</dd>
      </dl>
      <div className="meta">
        <span className="tag">{r.category}</span>
        <span className={`tag ${r.verification_kind}`}>verify: {r.verification_kind}</span>
        <span className="tag">{r.status}</span>
      </div>
    </div>
  );
}

function ProjectDetail({ id, go }: { id: string; go: (r: Route) => void }) {
  const [project, setProject] = useState<Project | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const load = async () => {
    try { setProject((await api.project(id)).project); }
    catch (e: any) { setErr(e.message); }
  };
  useEffect(() => { load(); }, [id]);

  const generate = async () => {
    setBusy(true); setErr(""); setNotice("");
    try {
      const { requirements } = await api.generateRequirements(id);
      setNotice(`Generated ${requirements.length} requirements with AI.`);
      await load();
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!confirm("Delete this project?")) return;
    await api.deleteProject(id);
    go({ name: "dashboard" });
  };

  if (err && !project) return <div className="page"><div className="err">{err}</div></div>;
  if (!project) return <div className="page"><p><span className="spin" />Loading…</p></div>;

  const reqs = project.requirements || [];
  const stageIdx = STAGES.indexOf(project.lifecycle_stage);

  return (
    <div className="page">
      <button className="btn small" onClick={() => go({ name: "dashboard" })}>← Projects</button>
      <div style={{ margin: "18px 0" }}>
        <div className="row">
          <h1 style={{ fontSize: "1.9rem" }}>{project.name}</h1>
          <div className="spacer" />
          <span className={`stage ${project.lifecycle_stage}`}>{project.lifecycle_stage}</span>
        </div>
        <div className="lifecycle">
          {STAGES.map((s, i) => (
            <span key={s} className={i < stageIdx ? "done" : i === stageIdx ? "now" : ""}>{s}</span>
          ))}
        </div>
        <div className="card">
          <p><b style={{ color: "#f5f5f5" }}>The idea:</b> {project.idea_text}</p>
        </div>
      </div>

      {err && <div className="err">{err}</div>}
      {notice && <div className="ok">{notice}</div>}

      <div className="row" style={{ marginBottom: 18 }}>
        <h2>Requirements {reqs.length > 0 && <span style={{ color: "#999", fontSize: "1rem" }}>({reqs.length})</span>}</h2>
        <div className="spacer" />
        <button className="btn primary" onClick={generate} disabled={busy}>
          {busy ? <><span className="spin" />AI is planning…</> : "✨ Generate requirements with AI"}
        </button>
        <button className="btn danger small" onClick={remove}>Delete</button>
      </div>

      {reqs.length === 0 ? (
        <div className="empty">
          <div className="big">📋</div>
          <p>No requirements yet. Hit <b>Generate requirements with AI</b> and watch the plan come together.</p>
          <p style={{ marginTop: 8, fontSize: ".82rem" }}>Phase 0 note: AI planning is real. Builds, tests & verification land in Phase 1–2.</p>
        </div>
      ) : (
        reqs.map((r) => <RequirementCard key={r.id} r={r} />)
      )}
    </div>
  );
}

export default function App() {
  const [route, go] = useRoute();
  const [user, setUser] = useState<any>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) { setChecked(true); return; }
    api.me()
      .then((d) => setUser(d.user))
      .catch(() => setToken(null))
      .finally(() => setChecked(true));
  }, []);

  const logout = () => {
    setToken(null); setUser(null);
    window.location.hash = "#/login";
  };

  // Refresh user after login/signup navigates to dashboard
  useEffect(() => {
    if (route.name === "dashboard" && isLoggedIn() && !user) {
      api.me().then((d) => setUser(d.user)).catch(() => setToken(null));
    }
  }, [route]);

  if (!checked) return <div className="page"><p><span className="spin" />Loading…</p></div>;

  if (!isLoggedIn()) {
    return (
      <>
        {route.name === "signup"
          ? <AuthPage mode="signup" go={go} />
          : <AuthPage mode="login" go={go} />}
      </>
    );
  }

  return (
    <>
      <Topbar user={user} onLogout={logout} />
      {route.name === "project"
        ? <ProjectDetail id={route.id} go={go} />
        : <Dashboard go={go} />}
    </>
  );
}
