import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { checkHealth } from '../services/api';

function Dashboard() {
  const { user, logout } = useAuth();
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    checkHealth().then(setHealthStatus).catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header Bar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/60 px-6 flex items-center justify-between backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4-4-4z" />
            </svg>
          </div>
          <span className="font-bold text-slate-100 tracking-tight">AI Chatbot Platform</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/60 border border-slate-700/50 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-300 font-medium">{user?.username}</span>
            <span className="text-slate-500">({user?.email})</span>
          </div>

          <button
            onClick={logout}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700/60 text-slate-200 text-xs font-medium transition flex items-center gap-1.5"
          >
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-xl font-bold text-white">Authentication Verified ✓</h2>
            <p className="text-sm text-slate-400">
              You are securely authenticated with JWT and bcrypt password protection.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">User ID</span>
              <span className="font-mono text-indigo-400 font-bold">{user?.id}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Username</span>
              <span className="text-slate-200 font-medium">{user?.username}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Email</span>
              <span className="text-slate-200 font-medium">{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">API Health</span>
              <span className="text-emerald-400 font-semibold">{healthStatus?.status || 'Connecting...'}</span>
            </div>
          </div>

          <div className="p-3 text-center text-xs text-indigo-400 bg-indigo-950/30 border border-indigo-800/40 rounded-xl">
            Ready for Phase 3 — Basic Gemini Chat Implementation
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
