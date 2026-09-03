"use client";

import React, { useState, useEffect } from "react";
import { RoleFitResult, AVAILABLE_ROLES, getRoleFit, FeatureVector } from "../lib/api";
import { getMockRoleFit } from "../lib/mockData";
import { Target, Compass, ArrowUpRight } from "lucide-react";

interface RoleFitCardProps {
  username: string;
  featureVector: FeatureVector;
}

export const RoleFitCard: React.FC<RoleFitCardProps> = ({ username, featureVector }) => {
  const [selectedRole, setSelectedRole] = useState<string>("Software Engineer");
  const [roleFit, setRoleFit] = useState<RoleFitResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    async function fetchFit() {
      try {
        const res = await getRoleFit(username, selectedRole);
        if (isMounted) setRoleFit(res);
      } catch {
        if (isMounted) {
          const fallback = getMockRoleFit(selectedRole, featureVector);
          setRoleFit(fallback);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchFit();

    return () => {
      isMounted = false;
    };
  }, [selectedRole, username, featureVector]);

  return (
    <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
            <Target className="w-4 h-4" /> Strategic Career Alignment
          </div>
          <h2 className="text-xl font-bold text-slate-100">Role Fit & Gap Analysis</h2>
        </div>

        {/* Role Selector Tabs */}
        <div className="flex items-center gap-1.5 p-1.5 bg-slate-900/90 rounded-xl border border-slate-800 overflow-x-auto max-w-full">
          {AVAILABLE_ROLES.map((role) => (
            <button
              key={role}
              onClick={() => setSelectedRole(role)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                selectedRole === role
                  ? "bg-cyan-500 text-slate-950 font-bold shadow-lg shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              {role}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center text-slate-500 flex flex-col items-center justify-center gap-2">
          <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Calculating role fit benchmarks...</span>
        </div>
      ) : roleFit ? (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Overall Fit Score badge */}
          <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800 text-center relative">
            <div className="w-28 h-28 rounded-full border-4 border-cyan-500/30 flex items-center justify-center relative mb-3">
              <div className="text-3xl font-black text-cyan-400 font-mono tracking-tight">
                {roleFit.overall_fit_score}%
              </div>
              <div className="absolute inset-0 rounded-full border-4 border-cyan-400 border-t-transparent animate-pulse opacity-60" />
            </div>

            <div className="text-sm font-bold text-slate-200">
              {roleFit.overall_fit_score >= 75
                ? "Excellent Match"
                : roleFit.overall_fit_score >= 50
                ? "Strong Potential"
                : "Developing Fit"}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Relative to verifiable baseline requirements for {selectedRole}
            </p>
          </div>

          {/* Skill Gap Bars */}
          <div className="lg:col-span-2 space-y-3 flex flex-col justify-center">
            <div className="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-1 flex items-center justify-between">
              <span>Competency Breakdown</span>
              <span>Observed vs Target</span>
            </div>

            {roleFit.gaps.map((gap, i) => {
              const current = Math.round(gap.current_score);
              const target = Math.round(gap.target_score);
              const hasGap = gap.gap > 5;

              return (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="capitalize text-slate-300 font-medium">
                      {gap.skill.replace("_", " ")}
                    </span>
                    <span className="text-slate-400">
                      <span className={hasGap ? "text-amber-400 font-bold" : "text-emerald-400 font-bold"}>
                        {current}
                      </span>
                      <span className="text-slate-600"> / </span>
                      <span className="text-slate-400">{target}</span>
                    </span>
                  </div>

                  {/* Dual Bar */}
                  <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden flex relative border border-slate-800">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        hasGap ? "bg-gradient-to-r from-amber-500 to-amber-400" : "bg-gradient-to-r from-cyan-500 to-emerald-400"
                      }`}
                      style={{ width: `${Math.min(100, current)}%` }}
                    />
                    {/* Target Marker */}
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-slate-200 z-10 opacity-70"
                      style={{ left: `${Math.min(100, target)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Recommended Next Challenge */}
      <div className="mt-6 pt-6 border-t border-slate-800/80">
        <div className="p-4 rounded-xl bg-gradient-to-r from-violet-950/30 via-slate-900/60 to-cyan-950/30 border border-violet-800/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400 shrink-0">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold tracking-wider uppercase text-violet-400">
                Recommended Portfolio Project
              </span>
              <h3 className="text-sm font-bold text-slate-100 mt-0.5">
                Targeted Sprint for {selectedRole}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Build an automated test harness with GitHub Actions CI to bridge testing and tooling competencies.
              </p>
            </div>
          </div>
          <button className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 whitespace-nowrap transition flex items-center gap-1.5 self-start sm:self-center border border-slate-700">
            View Challenge Blueprint <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
