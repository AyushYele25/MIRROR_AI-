const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AnalyzeResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  current_step: string;
  repos_found: number;
  repos_analyzed: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface FeatureVector {
  code_quality: number;
  testing: number;
  architecture: number;
  documentation: number;
  iteration: number;
  debugging: number;
  tooling: number;
  ml_workflow: number;
  project_complexity: number;
}

export interface Evidence {
  id: string;
  metric_name: string;
  metric_value: number;
  source_url: string;
  context: string;
}

export interface Insight {
  id: string;
  type: string;
  title: string;
  severity: string;
  score: number;
  confidence: number;
  explanation: string;
  recommendation: string;
  evidence: Evidence[];
}

export interface GapDetail {
  skill: string;
  current_score: number;
  target_score: number;
  gap: number;
}

export interface Profile {
  profile_id: string;
  user_id: string;
  github_login: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  version: number;
  feature_vector: FeatureVector;
  confidence: number;
  repos_analyzed: number;
  total_commits: number;
  total_files: number;
  created_at: string;
  insights: Insight[];
}

export interface RoleFitResult {
  profile_id: string;
  github_login: string;
  target_role: string;
  overall_fit_score: number;
  gaps: GapDetail[];
}

export interface Repo {
  id: string;
  name: string;
  full_name: string;
  url: string;
  description: string | null;
  primary_language: string | null;
  stars: number;
  forks_count: number;
  size_kb: number;
  topics: string[] | null;
  last_analyzed_at: string | null;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error ${res.status}`);
  }
  return res.json();
}

export async function analyzeGitHub(username: string): Promise<AnalyzeResponse> {
  return fetchAPI("/api/analyze/github", {
    method: "POST",
    body: JSON.stringify({ github_username: username }),
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return fetchAPI(`/api/analysis/${jobId}`);
}

export async function getProfile(username: string): Promise<Profile> {
  return fetchAPI(`/api/profile/${username}`);
}

export async function getRoleFit(
  username: string,
  role: string
): Promise<RoleFitResult> {
  return fetchAPI("/api/role-fit", {
    method: "POST",
    body: JSON.stringify({ github_username: username, target_role: role }),
  });
}

export async function getRepos(username: string): Promise<Repo[]> {
  return fetchAPI(`/api/repos/${username}`);
}

export async function deleteProfile(username: string): Promise<void> {
  await fetchAPI(`/api/profile/${username}`, { method: "DELETE" });
}

export const AVAILABLE_ROLES = [
  "ML Engineer",
  "Data Scientist",
  "Software Engineer",
  "Data Engineer",
  "AI Engineer",
];
