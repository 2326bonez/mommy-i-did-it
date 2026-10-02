const API = "";

function token(): string | null {
  return localStorage.getItem("mdi_token");
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem("mdi_token", t);
  else localStorage.removeItem("mdi_token");
}

export function isLoggedIn(): boolean {
  return !!token();
}

async function req(path: string, opts: RequestInit = {}): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(API + path, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

export const api = {
  signup: (email: string, password: string, display_name: string) =>
    req("/api/auth/signup", { method: "POST", body: JSON.stringify({ email, password, display_name }) }),
  login: (email: string, password: string) =>
    req("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req("/api/auth/me"),
  projects: () => req("/api/projects"),
  createProject: (name: string, idea_text: string, description: string) =>
    req("/api/projects", { method: "POST", body: JSON.stringify({ name, idea_text, description }) }),
  project: (id: string) => req(`/api/projects/${id}`),
  deleteProject: (id: string) => req(`/api/projects/${id}`, { method: "DELETE" }),
  generateRequirements: (id: string) =>
    req(`/api/projects/${id}/generate-requirements`, { method: "POST" }),
};

export interface Requirement {
  id: string;
  req_code: string;
  title: string;
  description: string;
  acceptance_criteria: string;
  category: string;
  verification_kind: string;
  status: string;
  origin: string;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  idea_text: string;
  description: string;
  lifecycle_stage: string;
  created_at: string;
  requirements?: Requirement[];
}
