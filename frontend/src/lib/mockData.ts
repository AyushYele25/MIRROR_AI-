import { Profile, RoleFitResult, Repo, JobStatus } from "./api";

export const DEMO_PROFILES: Record<string, Profile> = {
  "karpathy": {
    profile_id: "demo-karpathy-001",
    user_id: "usr-001",
    github_login: "karpathy",
    display_name: "Andrej Karpathy",
    avatar_url: "https://avatars.githubusercontent.com/u/281147?v=4",
    bio: "I like to train deep neural nets on large datasets.",
    version: 3,
    confidence: 0.94,
    repos_analyzed: 14,
    total_commits: 842,
    total_files: 320,
    created_at: new Date().toISOString(),
    feature_vector: {
      code_quality: 88,
      testing: 72,
      architecture: 85,
      documentation: 94,
      iteration: 78,
      debugging: 81,
      tooling: 86,
      ml_workflow: 98,
      project_complexity: 92,
    },
    insights: [
      {
        id: "ins-1",
        type: "strength",
        title: "World-Class ML Pipeline & Pedagogical Architecture",
        severity: "info",
        score: 98,
        confidence: 0.96,
        explanation: "Observational evidence demonstrates exceptional clarity in deep neural net implementations. Single-file architectures with zero extraneous dependencies maximize reproducibility.",
        recommendation: "Maintain the micro-framework pattern for emerging foundation model experiments.",
        evidence: [
          {
            id: "ev-1",
            metric_name: "ml_workflow_score",
            metric_value: 0.98,
            source_url: "https://github.com/karpathy/nanoGPT",
            context: "nanoGPT: Complete GPT training loop in ~300 lines of readable PyTorch code.",
          },
          {
            id: "ev-2",
            metric_name: "readme_density",
            metric_value: 48.5,
            source_url: "https://github.com/karpathy/micrograd",
            context: "micrograd: 80-line autograd engine with comprehensive educational README.",
          },
        ],
      },
      {
        id: "ins-2",
        type: "strength",
        title: "High Code Maintainability & Low Cognitive Load",
        severity: "info",
        score: 91,
        confidence: 0.92,
        explanation: "Functions average 14 lines with cyclomatic complexity strictly constrained below 4.0 across core algorithms.",
        recommendation: "Incorporate automated property-based test suites for numeric gradients.",
        evidence: [
          {
            id: "ev-3",
            metric_name: "avg_cyclomatic_complexity",
            metric_value: 2.1,
            source_url: "https://github.com/karpathy/nanoGPT/blob/master/model.py",
            context: "model.py: Clean CausalSelfAttention with attention mask decomposition.",
          },
        ],
      },
      {
        id: "ins-3",
        type: "observation",
        title: "Experimental Cadence Follows Burst Releases",
        severity: "info",
        score: 78,
        confidence: 0.88,
        explanation: "Commit activity shows intense weekend and evening sprints with focused multi-file architectural overhauls rather than fragmented daily micro-commits.",
        recommendation: "Standardize changelog tagging between major model architectural revisions.",
        evidence: [
          {
            id: "ev-4",
            metric_name: "avg_change_size",
            metric_value: 142,
            source_url: "https://github.com/karpathy/llm.c",
            context: "llm.c: High velocity commit bursts delivering pure C CUDA kernels.",
          },
        ],
      },
    ],
  },
  "tiangolo": {
    profile_id: "demo-tiangolo-002",
    user_id: "usr-002",
    github_login: "tiangolo",
    display_name: "Sebastián Ramírez",
    avatar_url: "https://avatars.githubusercontent.com/u/1326112?v=4",
    bio: "Creator of FastAPI, Typer, SQLModel, AsmPHP.",
    version: 4,
    confidence: 0.98,
    repos_analyzed: 28,
    total_commits: 3420,
    total_files: 1420,
    created_at: new Date().toISOString(),
    feature_vector: {
      code_quality: 95,
      testing: 96,
      architecture: 94,
      documentation: 99,
      iteration: 89,
      debugging: 90,
      tooling: 94,
      ml_workflow: 65,
      project_complexity: 96,
    },
    insights: [
      {
        id: "ins-10",
        type: "strength",
        title: "Exemplary Automated Testing & 100% CI Coverage",
        severity: "info",
        score: 99,
        confidence: 0.99,
        explanation: "Test file ratio exceeds 38% with dedicated GitHub Actions matrices testing across Python 3.8-3.13, PyPy, and multi-OS runners.",
        recommendation: "Benchmark suite could benefit from continuous regression tracking dashboards.",
        evidence: [
          {
            id: "ev-10",
            metric_name: "test_file_ratio",
            metric_value: 0.38,
            source_url: "https://github.com/fastapi/fastapi",
            context: "tests/ directory contains over 1,200 modular test scenarios for dependency injection.",
          },
          {
            id: "ev-11",
            metric_name: "ci_present",
            metric_value: 1.0,
            source_url: "https://github.com/fastapi/fastapi/.github/workflows/test.yml",
            context: "GitHub Actions workflow running matrix tests with strict coverage requirements.",
          },
        ],
      },
    ],
  },
};

export const DEMO_REPOS: Record<string, Repo[]> = {
  "karpathy": [
    {
      id: "repo-1",
      name: "nanoGPT",
      full_name: "karpathy/nanoGPT",
      url: "https://github.com/karpathy/nanoGPT",
      description: "The simplest, fastest repository for training/finetuning medium-sized GPTs.",
      primary_language: "Python",
      stars: 36200,
      forks_count: 5400,
      size_kb: 1420,
      topics: ["deep-learning", "pytorch", "transformers", "gpt"],
      last_analyzed_at: new Date().toISOString(),
    },
    {
      id: "repo-2",
      name: "micrograd",
      full_name: "karpathy/micrograd",
      url: "https://github.com/karpathy/micrograd",
      description: "A tiny scalar-valued autograd engine and a neural net library on top of it.",
      primary_language: "Python",
      stars: 12800,
      forks_count: 1900,
      size_kb: 450,
      topics: ["autograd", "educational", "neural-network"],
      last_analyzed_at: new Date().toISOString(),
    },
    {
      id: "repo-3",
      name: "llm.c",
      full_name: "karpathy/llm.c",
      url: "https://github.com/karpathy/llm.c",
      description: "LLM training in simple, raw C/CUDA without PyTorch.",
      primary_language: "C",
      stars: 25400,
      forks_count: 2800,
      size_kb: 3200,
      topics: ["cuda", "c", "llm", "performance"],
      last_analyzed_at: new Date().toISOString(),
    },
  ],
};

export function getMockRoleFit(role: string, vector: Profile["feature_vector"]): RoleFitResult {
  const roleTargets: Record<string, Record<string, number>> = {
    "ML Engineer": { ml_workflow: 80, code_quality: 70, testing: 65, tooling: 75, architecture: 60, documentation: 55 },
    "Data Scientist": { ml_workflow: 85, documentation: 65, code_quality: 55, testing: 45, iteration: 60, tooling: 50 },
    "Software Engineer": { code_quality: 80, testing: 75, architecture: 75, tooling: 70, debugging: 60, documentation: 55 },
    "Data Engineer": { architecture: 80, tooling: 80, code_quality: 70, testing: 65, debugging: 55, documentation: 50 },
    "AI Engineer": { ml_workflow: 75, architecture: 75, tooling: 75, code_quality: 70, testing: 60, documentation: 55 },
  };

  const targets = roleTargets[role] || roleTargets["Software Engineer"];
  let totalFit = 0;
  let count = 0;
  const gaps = [];

  for (const [skill, target] of Object.entries(targets)) {
    const current = (vector as any)[skill] || 50;
    const gap = Math.max(0, target - current);
    const fitRatio = Math.min(current / target, 1.0);
    totalFit += fitRatio;
    count++;
    gaps.push({
      skill,
      current_score: current,
      target_score: target,
      gap,
    });
  }

  gaps.sort((a, b) => b.gap - a.gap);
  const overall = Math.round((totalFit / count) * 100);

  return {
    profile_id: "demo-fit",
    github_login: "developer",
    target_role: role,
    overall_fit_score: overall,
    gaps,
  };
}
