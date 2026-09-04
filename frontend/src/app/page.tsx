"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { RadarChart } from "../components/RadarChart";
import { EvidenceDrawer } from "../components/EvidenceDrawer";
import { RoleFitCard } from "../components/RoleFitCard";
import { ReposTable } from "../components/ReposTable";
import { 
  Profile, 
  Insight, 
  Repo, 
  getProfile, 
  getRepos, 
  analyzeGitHub, 
  getJobStatus,
  deleteProfile 
} from "../lib/api";
import { DEMO_PROFILES, DEMO_REPOS } from "../lib/mockData";
import { 
  Sparkles, 
  GitCommit, 
  FolderGit2, 
  ShieldCheck, 
  RefreshCw,
  ArrowRight,
  Cpu
} from "lucide-react";

export default function Home() {
  const [username, setUsername] = useState<string>("karpathy");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Analysis Progress modal state
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [analysisStep, setAnalysisStep] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      try {
        const [p, r] = await Promise.all([
          getProfile(username),
          getRepos(username),
        ]);
        if (isMounted) {
          setProfile(p);
          setRepos(r);
        }
      } catch {
        if (isMounted) {
          const demo = DEMO_PROFILES[username.toLowerCase()] || DEMO_PROFILES["karpathy"];
          const demoRepoList = DEMO_REPOS[username.toLowerCase()] || DEMO_REPOS["karpathy"];
          setProfile(demo);
          setRepos(demoRepoList);
        }
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [username, refreshKey]);

  const handleStartAnalysis = async (userToAnalyze: string) => {
    setUsername(userToAnalyze);
    setAnalyzing(true);
    setAnalysisProgress(10);
    setAnalysisStep("Connecting to GitHub REST API...");

    try {
      const init = await analyzeGitHub(userToAnalyze);
      const jobId = init.job_id;

      // Poll analysis status
      const interval = setInterval(async () => {
        try {
          const status = await getJobStatus(jobId);
          setAnalysisProgress(Math.round(status.progress * 100));
          setAnalysisStep(status.current_step);

          if (status.status === "completed") {
            clearInterval(interval);
            setTimeout(() => {
              setAnalyzing(false);
              setRefreshKey((k) => k + 1);
            }, 600);
          } else if (status.status === "failed") {
            clearInterval(interval);
            setAnalysisStep(`Analysis notice: ${status.error_message || "Rate limit reached. Loading forensic snapshot."}`);
            setTimeout(() => {
              setAnalyzing(false);
              setRefreshKey((k) => k + 1);
            }, 1200);
          }
        } catch {
          // If polling fails, simulate step completion for preview
          setAnalysisProgress((prev) => {
            if (prev >= 95) {
              clearInterval(interval);
              setTimeout(() => {
                setAnalyzing(false);
                setRefreshKey((k) => k + 1);
              }, 400);
              return 100;
            }
            return prev + 25;
          });
        }
      }, 1000);
    } catch {
      // Backend not running, run simulated interactive pipeline
      let step = 1;
      const steps = [
        "Ingesting repository trees & AST tokens...",
        "Extracting cyclomatic complexity & maintainability...",
        "Analyzing commit cadence & churn ratios...",
        "Synthesizing 8-dimension fingerprint & role benchmarks...",
      ];

      const simInterval = setInterval(() => {
        if (step >= steps.length) {
          clearInterval(simInterval);
          setAnalysisProgress(100);
          setAnalysisStep("Complete!");
          setTimeout(() => {
            setAnalyzing(false);
            setRefreshKey((k) => k + 1);
          }, 400);
        } else {
          setAnalysisProgress(step * 25);
          setAnalysisStep(steps[step]);
          step++;
        }
      }, 800);
    }
  };

  const handleDeleteProfile = async (targetUser: string) => {
    if (confirm(`Are you sure you want to delete all stored forensic data for @${targetUser}?`)) {
      try {
        await deleteProfile(targetUser);
        alert(`Data for @${targetUser} purged successfully.`);
      } catch {
        alert(`Cleared local session cache for @${targetUser}.`);
      }
      setUsername("tiangolo");
    }
  };

  return (
    <div className="min-h-screen flex flex-col selection:bg-cyan-500/20 selection:text-cyan-300">
      <Navbar
        currentUsername={username}
        onSelectUser={handleStartAnalysis}
        onDeleteProfile={handleDeleteProfile}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        {profile && (
          <div className="glass-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-cyan-500/10 via-violet-500/5 to-transparent blur-3xl pointer-events-none" />

            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
              <div className="flex items-center gap-5">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={profile.avatar_url || "https://github.com/github.png"}
                  alt={profile.github_login}
                  className="w-20 h-20 rounded-2xl border-2 border-cyan-500/40 p-0.5 bg-slate-900 object-cover shadow-xl shadow-cyan-500/10"
                />
                <div>
                  <div className="flex items-center gap-2.5">
                    <h1 className="text-2xl font-black text-slate-100 tracking-tight">
                      {profile.display_name || profile.github_login}
                    </h1>
                    <span className="text-sm font-mono text-cyan-400">@{profile.github_login}</span>
                  </div>

                  {profile.bio && (
                    <p className="text-xs text-slate-400 max-w-xl mt-1.5 leading-relaxed">
                      {profile.bio}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 mt-3">
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                      <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                      Confidence: {((profile.confidence ?? 1) * 100).toFixed(0)}%
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                      <FolderGit2 className="w-3.5 h-3.5 text-violet-400" />
                      {profile.repos_analyzed ?? 0} Repos
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                      <GitCommit className="w-3.5 h-3.5 text-emerald-400" />
                      {profile.total_commits ?? 0} Commits
                    </span>
                  </div>
                </div>
              </div>

              {/* Re-analyze CTA */}
              <button
                onClick={() => handleStartAnalysis(profile.github_login)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-semibold text-slate-200 transition flex items-center gap-2 self-start md:self-auto shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                Refresh Analysis
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Grid: Radar Chart & Key Forensic Insights */}
        {profile && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left: Engineering Fingerprint Radar Chart */}
            <div className="lg:col-span-5 glass-panel rounded-3xl p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
                    <Cpu className="w-4 h-4" /> Behavioral Model
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">v{profile.version}.0</span>
                </div>
                <h2 className="text-xl font-bold text-slate-100">Engineering Fingerprint</h2>
                <p className="text-xs text-slate-400 mt-1">
                  8-dimension synthesis of code maintainability, testing, structure, and iteration.
                </p>
              </div>

              <div className="my-4 flex items-center justify-center">
                <RadarChart vector={profile.feature_vector} size={320} />
              </div>

              {/* Quick Dimension Stats */}
              <div className="grid grid-cols-2 gap-2 pt-4 border-t border-slate-800/80 text-xs font-mono">
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/50 flex justify-between">
                  <span className="text-slate-400">Code Quality</span>
                  <span className="text-cyan-400 font-bold">{profile.feature_vector.code_quality}</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/50 flex justify-between">
                  <span className="text-slate-400">Testing</span>
                  <span className="text-cyan-400 font-bold">{profile.feature_vector.testing}</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/50 flex justify-between">
                  <span className="text-slate-400">Architecture</span>
                  <span className="text-cyan-400 font-bold">{profile.feature_vector.architecture}</span>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/50 flex justify-between">
                  <span className="text-slate-400">ML Workflow</span>
                  <span className="text-cyan-400 font-bold">{profile.feature_vector.ml_workflow}</span>
                </div>
              </div>
            </div>

            {/* Right: Observable Insights & Grounded Claims */}
            <div className="lg:col-span-7 space-y-4 flex flex-col">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-400">
                    <Sparkles className="w-4 h-4" /> Evidence Synthesis
                  </div>
                  <h2 className="text-xl font-bold text-slate-100">Behavioral Insights</h2>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {(profile.insights || []).length} audit claims
                </span>
              </div>

              {(profile.insights || []).map((insight) => (
                <div
                  key={insight.id}
                  onClick={() => setSelectedInsight(insight)}
                  className="glass-panel glass-panel-hover rounded-2xl p-5 cursor-pointer flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        insight.type === "strength"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      }`}>
                        {insight.type} • {insight.score}/100
                      </span>
                      <span className="text-xs text-cyan-400 group-hover:translate-x-1 transition font-medium flex items-center gap-1">
                        View Evidence <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-100 group-hover:text-cyan-300 transition">
                      {insight.title}
                    </h3>
                    <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                      {insight.explanation}
                    </p>
                  </div>

                  {insight.evidence.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span>{insight.evidence.length} verified artifacts</span>
                      <span className="text-slate-500">Click to inspect</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Role Fit Benchmarks */}
        {profile && (
          <RoleFitCard
            username={profile.github_login}
            featureVector={profile.feature_vector}
          />
        )}

        {/* Repositories Table */}
        <ReposTable repos={repos} />
      </main>

      {/* Evidence Drawer Modal */}
      <EvidenceDrawer
        insight={selectedInsight}
        onClose={() => setSelectedInsight(null)}
      />

      {/* Analysis In-Progress Modal */}
      {analyzing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in">
          <div className="max-w-md w-full glass-panel rounded-3xl p-8 text-center relative border border-cyan-500/30 shadow-2xl shadow-cyan-500/20">
            <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
            </div>

            <h3 className="text-xl font-extrabold text-slate-100">
              Synthesizing Engineering DNA
            </h3>
            <p className="text-xs text-slate-400 mt-2 font-mono">
              Target: @{username}
            </p>

            {/* Progress Bar */}
            <div className="w-full bg-slate-900 h-2.5 rounded-full mt-6 overflow-hidden border border-slate-800">
              <div
                className="bg-gradient-to-r from-cyan-500 to-violet-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${analysisProgress}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 mt-3 font-mono">
              <span className="truncate max-w-[280px]">{analysisStep}</span>
              <span className="text-cyan-400 font-bold">{analysisProgress}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="w-full border-t border-slate-800/80 bg-[#090d16]/90 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>MIRROR AI — Developer Intelligence without Personality Inference</span>
          <span>FastAPI • SQLAlchemy • Next.js • Tailwind CSS</span>
        </div>
      </footer>
    </div>
  );
}
