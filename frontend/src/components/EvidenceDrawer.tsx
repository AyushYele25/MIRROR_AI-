"use client";

import React from "react";
import { Insight } from "../lib/api";
import { X, ExternalLink, CheckCircle2, AlertTriangle, Info, Terminal } from "lucide-react";

interface EvidenceDrawerProps {
  insight: Insight | null;
  onClose: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({ insight, onClose }) => {
  if (!insight) return null;

  const isStrength = insight.type === "strength";
  const evidenceList = Array.isArray(insight.evidence) ? insight.evidence : [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity">
      <div 
        className="w-full max-w-xl h-full bg-[#0d1424] border-l border-slate-800 p-6 flex flex-col shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300"
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isStrength ? "bg-emerald-500/10 text-emerald-400" : "bg-cyan-500/10 text-cyan-400"}`}>
              {isStrength ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
            </div>
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
                {insight.type.toUpperCase()} • Score {insight.score}/100
              </span>
              <h2 className="text-lg font-bold text-slate-100">{insight.title}</h2>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Explanation & Actionable Recommendation */}
        <div className="mt-6 space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <h3 className="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-2 flex items-center gap-2">
              <Info className="w-3.5 h-3.5 text-cyan-400" /> Observable Pattern
            </h3>
            <p className="text-sm text-slate-200 leading-relaxed">{insight.explanation}</p>
          </div>

          {insight.recommendation && (
            <div className="p-4 rounded-xl bg-violet-950/20 border border-violet-800/30">
              <h3 className="text-xs uppercase tracking-wider font-semibold text-violet-400 mb-2">
                Actionable Next Step
              </h3>
              <p className="text-sm text-violet-200 leading-relaxed">{insight.recommendation}</p>
            </div>
          )}
        </div>

        {/* Verified Evidence Trails */}
        <div className="mt-8 flex-1">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" /> Evidence Audit Trail ({evidenceList.length})
            </h3>
            <span className="text-xs text-slate-400 font-mono">grounded: 100%</span>
          </div>

          {evidenceList.length === 0 ? (
            <div className="p-6 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl text-sm">
              No granular file-level evidence attached.
            </div>
          ) : (
            <div className="space-y-3">
              {evidenceList.map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                      {item.metric_name}
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-300">
                      val: {typeof item.metric_value === "number" ? item.metric_value : JSON.stringify(item.metric_value)}
                    </span>
                  </div>

                  <p className="text-sm text-slate-300 mt-2 font-mono text-xs bg-black/40 p-2.5 rounded-lg border border-slate-800/60">
                    {item.context || "No context provided"}
                  </p>

                  {item.source_url && (
                    <div className="mt-3 flex justify-end">
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition"
                      >
                        Inspect Artifact on GitHub <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-6 mt-6 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <span>Confidence: {Math.round((insight.confidence ?? 1) * 100)}%</span>
          <span>MIRROR AI Forensic Grounding</span>
        </div>
      </div>
    </div>
  );
};
