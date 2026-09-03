"use client";

import React, { useState } from "react";
import { Sparkles, Search, Trash2 } from "lucide-react";

interface NavbarProps {
  currentUsername: string;
  onSelectUser: (username: string) => void;
  onDeleteProfile?: (username: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentUsername, onSelectUser, onDeleteProfile }) => {
  const [inputVal, setInputVal] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputVal.trim()) {
      onSelectUser(inputVal.trim());
      setInputVal("");
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#090d16]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectUser("karpathy")}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              MIRROR AI
            </span>
            <span className="hidden sm:inline-block ml-2 text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/50">
              v0.1.0 • Developer Intelligence
            </span>
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex-1 max-w-md mx-4 hidden md:block">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Analyze GitHub profile (e.g. torvalds, karpathy)..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              className="w-full pl-9 pr-24 py-1.5 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
            />
            <button
              type="submit"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 px-2.5 py-1 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-[11px] rounded-lg transition"
            >
              Analyze
            </button>
          </div>
        </form>

        {/* Action Controls & Demos */}
        <div className="flex items-center gap-2">
          {/* Quick Demos */}
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 mr-2">
            <span>Demos:</span>
            {["karpathy", "tiangolo"].map((demo) => (
              <button
                key={demo}
                onClick={() => onSelectUser(demo)}
                className={`px-2 py-1 rounded-md text-[11px] font-mono transition ${
                  currentUsername.toLowerCase() === demo
                    ? "bg-slate-800 text-cyan-400 border border-cyan-800/50"
                    : "hover:bg-slate-800/60 text-slate-300"
                }`}
              >
                @{demo}
              </button>
            ))}
          </div>

          {/* Privacy Delete button */}
          {onDeleteProfile && (
            <button
              onClick={() => onDeleteProfile(currentUsername)}
              title="Purge and delete profile data"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition border border-transparent hover:border-rose-900/40"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
};
