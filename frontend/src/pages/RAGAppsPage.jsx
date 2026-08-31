import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../context/AuthContext';
import {
  getRAGAppsApi,
  createRAGAppApi,
  deleteRAGAppApi,
  listRAGDocsApi,
  uploadRAGDocApi,
  deleteRAGDocApi,
  reindexRAGAppApi,
  chatRAGAppApi
} from '../services/api';

function RAGAppsPage() {
  const { user } = useAuth();
  const [ragApps, setRagApps] = useState([]);
  const [activeAppId, setActiveAppId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [newAppName, setNewAppName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState('');

  // RAG Chat State
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);

  useEffect(() => {
    loadRAGApps();
  }, []);

  useEffect(() => {
    if (activeAppId) {
      loadDocuments(activeAppId);
      setMessages([]);
      setIndexMessage('');
    }
  }, [activeAppId]);

  const loadRAGApps = async () => {
    try {
      const apps = await getRAGAppsApi();
      setRagApps(apps);
      if (apps.length > 0 && !activeAppId) {
        setActiveAppId(apps[0].id);
      }
    } catch (err) {
      console.error('Failed to load RAG Apps:', err);
    }
  };

  const loadDocuments = async (appId) => {
    try {
      const docs = await listRAGDocsApi(appId);
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleCreateApp = async (e) => {
    e.preventDefault();
    if (!newAppName.trim()) return;
    setIsCreating(true);
    try {
      const created = await createRAGAppApi(newAppName.trim());
      setRagApps((prev) => [created, ...prev]);
      setActiveAppId(created.id);
      setNewAppName('');
    } catch (err) {
      console.error('Failed to create RAG app:', err);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteApp = async (appId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this RAG Application and all its documents and index?')) return;
    try {
      await deleteRAGAppApi(appId);
      setRagApps((prev) => prev.filter((a) => a.id !== appId));
      if (activeAppId === appId) {
        const remaining = ragApps.filter((a) => a.id !== appId);
        setActiveAppId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete RAG app:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !activeAppId) return;

    setIsUploading(true);
    try {
      await uploadRAGDocApi(activeAppId, file);
      loadDocuments(activeAppId);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await deleteRAGDocApi(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleReindex = async () => {
    if (!activeAppId) return;
    setIsReindexing(true);
    setIndexMessage('');
    try {
      const res = await reindexRAGAppApi(activeAppId);
      setIndexMessage(res.message || 'FAISS Vector Index updated successfully!');
    } catch (err) {
      setIndexMessage(err.response?.data?.detail || 'Failed to build index.');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleSendQuestion = async (e) => {
    e.preventDefault();
    if (!inputQuestion.trim() || !activeAppId || isAsking) return;

    const questionText = inputQuestion.trim();
    setInputQuestion('');
    setIsAsking(true);

    const userMsg = { role: 'user', content: questionText };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await chatRAGAppApi(activeAppId, questionText);
      const aiMsg = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: Failed to query document context.' }
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  const activeApp = ragApps.find((a) => a.id === activeAppId);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-72 bg-slate-900 border-r border-slate-800/80 flex flex-col justify-between shrink-0">
        <div className="p-4 space-y-4 flex-1 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between">
            <Link
              to="/"
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
            >
              ← Back to Chat
            </Link>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
              Knowledge Base
            </span>
          </div>

          {/* New App Form */}
          <form onSubmit={handleCreateApp} className="space-y-2">
            <input
              type="text"
              required
              placeholder="Collection Name (e.g. Policies, Notes)"
              value={newAppName}
              onChange={(e) => setNewAppName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="submit"
              disabled={isCreating}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl text-xs shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
            >
              + Create Collection
            </button>
          </form>

          {/* Collections List */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
            <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Document Collections
            </h3>
            {ragApps.length === 0 ? (
              <p className="px-3 text-xs text-slate-500 italic">No collections created yet.</p>
            ) : (
              ragApps.map((app) => (
                <div
                  key={app.id}
                  onClick={() => setActiveAppId(app.id)}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium cursor-pointer transition ${
                    activeAppId === app.id
                      ? 'bg-slate-800 text-indigo-400 border border-slate-700/60'
                      : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <svg className="w-4 h-4 text-indigo-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 01-2-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    <span className="truncate">{app.name}</span>
                  </div>

                  <button
                    onClick={(e) => handleDeleteApp(app.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-400 transition"
                    title="Delete Collection"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
        {activeApp ? (
          <>
            {/* App Top Bar */}
            <header className="h-16 border-b border-slate-800/80 px-6 flex items-center justify-between bg-slate-950/80 backdrop-blur">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  {activeApp.name}
                  <span className="text-xs text-slate-500 font-normal">
                    (ID: #{activeApp.id})
                  </span>
                </h2>
                <p className="text-xs text-slate-400">Document Intelligence &amp; Search</p>
              </div>

              <button
                onClick={handleReindex}
                disabled={isReindexing || documents.length === 0}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium rounded-xl text-xs shadow-lg shadow-indigo-600/20 transition flex items-center gap-2"
              >
                {isReindexing ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing Documents...
                  </>
                ) : (
                  '⚡ Process Documents'
                )}
              </button>
            </header>

            {indexMessage && (
              <div className="mx-6 mt-4 p-3 rounded-xl bg-indigo-950/50 border border-indigo-800/50 text-indigo-300 text-xs flex justify-between items-center">
                <span>{indexMessage}</span>
                <button onClick={() => setIndexMessage('')} className="text-slate-400 hover:text-white">✕</button>
              </div>
            )}

            {/* Split Screen: Documents Manager & Document Chat */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden p-6 gap-6">
              {/* Document Manager Panel (4 columns) */}
              <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col space-y-4 overflow-hidden">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white">Uploaded Documents</h3>
                  <span className="text-xs text-slate-400">{documents.length} files</span>
                </div>

                {/* Upload Button */}
                <label className="w-full py-3 border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-xl bg-slate-950/50 flex flex-col items-center justify-center cursor-pointer transition">
                  <svg className="w-6 h-6 text-slate-400 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 0115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <span className="text-xs text-slate-300 font-medium">
                    {isUploading ? 'Uploading file...' : 'Upload Document'}
                  </span>
                  <span className="text-[10px] text-slate-500">PDF, TXT, DOCX, CSV (Max 10MB)</span>
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx,.csv"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                    className="hidden"
                  />
                </label>

                {/* Documents List */}
                <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar">
                  {documents.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-6 italic">No documents uploaded yet.</p>
                  ) : (
                    documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                      >
                        <div className="overflow-hidden pr-2">
                          <p className="font-semibold text-slate-200 truncate">{doc.filename}</p>
                          <p className="text-[10px] text-slate-500 uppercase">
                            {doc.file_type} • {(doc.file_size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                        <button
                          onClick={() => handleDeleteDoc(doc.id)}
                          className="p-1 text-slate-500 hover:text-rose-400 rounded transition"
                          title="Delete document"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Document Chat Panel (8 columns) */}
              <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col overflow-hidden">
                <div className="p-4 border-b border-slate-800 bg-slate-950/40">
                  <h3 className="text-sm font-bold text-white">Document Q&amp;A Chat</h3>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto space-y-2 text-slate-500">
                      <svg className="w-10 h-10 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      <p className="text-xs">Ask any question about your uploaded documents.</p>
                      <p className="text-[10px] text-slate-600">Ensure you process documents after adding new files!</p>
                    </div>
                  ) : (
                    messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-3 max-w-2xl ${
                          msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                        }`}
                      >
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 font-bold text-[10px] ${
                            msg.role === 'user'
                              ? 'bg-indigo-600 text-white'
                              : 'bg-emerald-600/30 text-emerald-400 border border-emerald-500/40'
                          }`}
                        >
                          {msg.role === 'user' ? 'U' : 'AI'}
                        </div>

                        <div
                          className={`p-3.5 rounded-2xl text-xs leading-relaxed ${
                            msg.role === 'user'
                              ? 'bg-indigo-600 text-white rounded-tr-none'
                              : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none prose prose-invert max-w-none'
                          }`}
                        >
                          <ReactMarkdown>{msg.content}</ReactMarkdown>

                          {msg.sources && msg.sources.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-slate-800 text-[10px] text-emerald-400 flex items-center gap-1">
                              <span className="font-semibold">Sources:</span>
                              <span>{msg.sources.join(', ')}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}

                  {isAsking && (
                    <div className="flex gap-3 max-w-2xl mr-auto">
                      <div className="w-7 h-7 rounded-full bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 flex items-center justify-center font-bold text-[10px] shrink-0">
                        AI
                      </div>
                      <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
                        Analyzing documents &amp; generating answer...
                      </div>
                    </div>
                  )}
                </div>

                {/* Input */}
                <div className="p-4 border-t border-slate-800 bg-slate-950">
                  <form onSubmit={handleSendQuestion} className="flex gap-3">
                    <input
                      type="text"
                      value={inputQuestion}
                      onChange={(e) => setInputQuestion(e.target.value)}
                      placeholder="Ask a question about these documents..."
                      className="flex-1 px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-white text-xs placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button
                      type="submit"
                      disabled={!inputQuestion.trim() || isAsking}
                      className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium rounded-xl text-xs transition"
                    >
                      Ask Question
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 text-slate-500">
            <svg className="w-12 h-12 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 01-2-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <h3 className="text-base font-bold text-white">No Collection Selected</h3>
            <p className="text-xs text-slate-400 max-w-sm">
              Create a new document collection in the left sidebar to start uploading files and asking questions.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default RAGAppsPage;
