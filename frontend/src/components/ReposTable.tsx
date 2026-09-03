"use client";

import React, { useState } from "react";
import { Repo } from "../lib/api";
import { Star, GitFork, ExternalLink, Code, Search } from "lucide-react";

interface ReposTableProps {
  repos: Repo[];
}

export const ReposTable: React.FC<ReposTableProps> = ({ repos }) => {
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (r.primary_language && r.primary_language.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Code className="w-5 h-5 text-cyan-400" /> Analyzed Repositories ({repos.length})
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Software artifacts ingested, parsed, and checked for code health & complexity.
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter repositories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-slate-900/90 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-full sm:w-64 transition"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Repository</th>
              <th className="py-3 px-4">Language</th>
              <th className="py-3 px-4">Stars</th>
              <th className="py-3 px-4">Forks</th>
              <th className="py-3 px-4">Size</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No repositories found matching &quot;{searchTerm}&quot;.
                </td>
              </tr>
            ) : (
              filtered.map((repo) => (
                <tr key={repo.id} className="hover:bg-slate-800/30 transition">
                  <td className="py-3.5 px-4 font-medium text-slate-100">
                    <div className="flex flex-col">
                      <span className="font-semibold text-cyan-300">{repo.name}</span>
                      {repo.description && (
                        <span className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                          {repo.description}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    {repo.primary_language ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700/60">
                        {repo.primary_language}
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <span className="inline-flex items-center gap-1">
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                      {repo.stars.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <span className="inline-flex items-center gap-1 text-slate-400">
                      <GitFork className="w-3 h-3" />
                      {repo.forks_count.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-400">
                    {repo.size_kb > 1024 ? `${(repo.size_kb / 1024).toFixed(1)} MB` : `${repo.size_kb} KB`}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <a
                      href={repo.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    >
                      GitHub <ExternalLink className="w-3 h-3" />
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
