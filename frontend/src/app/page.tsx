"use client";

import React, { useState, useEffect } from 'react';
import { Search, Database, AlertCircle, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api-client';
import type { Investigation, GraphData } from '@/lib/api-client';

export default function Dashboard() {
    const [investigations, setInvestigations] = useState<Investigation[]>([]);
    const [currentInvestigation, setCurrentInvestigation] = useState<Investigation | null>(null);
    const [graphData, setGraphData] = useState<GraphData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // New investigation form
    const [newTarget, setNewTarget] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    // Load investigations on mount
    useEffect(() => {
        loadInvestigations();
    }, []);

    // Load graph when investigation changes
    useEffect(() => {
        if (currentInvestigation) {
            loadGraph(currentInvestigation.id);
        }
    }, [currentInvestigation]);

    const loadInvestigations = async () => {
        try {
            setLoading(true);
            const data = await apiClient.listInvestigations();
            setInvestigations(data.investigations);
            if (data.investigations.length > 0) {
                setCurrentInvestigation(data.investigations[0]);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load investigations');
        } finally {
            setLoading(false);
        }
    };

    const loadGraph = async (investigationId: string) => {
        try {
            const data = await apiClient.getGraph(investigationId);
            setGraphData(data.graph);
        } catch (err: any) {
            console.error('Failed to load graph:', err);
        }
    };

    const handleCreateInvestigation = async () => {
        if (!newTarget.trim()) return;

        setIsCreating(true);
        setError(null);

        try {
            const result = await apiClient.createInvestigation({
                name: `Investigation: ${newTarget}`,
                target: newTarget,
                goal: `Investigate ${newTarget} using OSINT sources`
            });

            setInvestigations([result.investigation, ...investigations]);
            setCurrentInvestigation(result.investigation);
            setNewTarget('');

            // Start collection automatically
            await handleStartCollection(result.investigation.id, newTarget);
        } catch (err: any) {
            setError(err.message || 'Failed to create investigation');
        } finally {
            setIsCreating(false);
        }
    };

    const handleStartCollection = async (investigationId: string, query: string) => {
        try {
            await apiClient.startCollection({
                investigation_id: investigationId,
                agent_type: 'duckduckgo',
                query: query,
                max_results: 20
            });

            // Reload graph after a delay
            setTimeout(() => loadGraph(investigationId), 5000);
        } catch (err: any) {
            console.error('Failed to start collection:', err);
        }
    };

    return (
        <main className="flex h-screen w-full bg-slate-950 text-slate-200 overflow-hidden">
            {/* Sidebar */}
            <aside className="w-80 border-r border-slate-800 flex flex-col bg-slate-950/50">
                <div className="p-4 border-b border-slate-800">
                    <h1 className="text-lg font-semibold flex items-center gap-2">
                        <Database className="w-5 h-5 text-blue-500" />
                        OSINT Autonomous Analyst
                    </h1>
                </div>

                {/* New Investigation Form */}
                <div className="p-4 border-b border-slate-800">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        New Investigation
                    </label>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            placeholder="Enter target (e.g., example.com)"
                            value={newTarget}
                            onChange={(e) => setNewTarget(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleCreateInvestigation()}
                            className="flex-1 bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                            disabled={isCreating}
                        />
                        <button
                            onClick={handleCreateInvestigation}
                            disabled={isCreating || !newTarget.trim()}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-500 rounded-md text-sm font-medium transition-colors"
                        >
                            {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
                        </button>
                    </div>
                </div>

                {/* Investigations List */}
                <div className="flex-1 overflow-y-auto p-4">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Investigations ({investigations.length})
                    </label>
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
                        </div>
                    ) : investigations.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-8">
                            No investigations yet.<br />Create one above to start.
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {investigations.map((inv) => (
                                <button
                                    key={inv.id}
                                    onClick={() => setCurrentInvestigation(inv)}
                                    className={`w-full text-left p-3 rounded-lg border transition-colors ${currentInvestigation?.id === inv.id
                                            ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                                            : 'bg-slate-900/50 border-slate-800 hover:bg-slate-800'
                                        }`}
                                >
                                    <div className="font-medium text-sm truncate">{inv.name}</div>
                                    <div className="text-xs text-slate-500 mt-1">{inv.target}</div>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className={`px-2 py-0.5 rounded text-xs ${inv.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                                                inv.status === 'collecting' ? 'bg-yellow-500/10 text-yellow-500' :
                                                    'bg-slate-500/10 text-slate-500'
                                            }`}>
                                            {inv.status}
                                        </span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <header className="h-14 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-950/50">
                    <div className="flex items-center gap-4">
                        <h2 className="font-semibold">
                            {currentInvestigation ? currentInvestigation.name : 'No Investigation Selected'}
                        </h2>
                        {currentInvestigation && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-xs border border-emerald-500/20">
                                {currentInvestigation.status.toUpperCase()}
                            </span>
                        )}
                    </div>
                </header>

                {/* Graph Area */}
                <div className="flex-1 p-6 overflow-hidden">
                    {error && (
                        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
                            <div>
                                <div className="font-medium text-red-400">Error</div>
                                <div className="text-sm text-red-300">{error}</div>
                            </div>
                        </div>
                    )}

                    {!currentInvestigation ? (
                        <div className="h-full flex items-center justify-center text-slate-500">
                            <div className="text-center">
                                <Database className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                <p>Create an investigation to begin</p>
                            </div>
                        </div>
                    ) : !graphData ? (
                        <div className="h-full flex items-center justify-center">
                            <div className="text-center">
                                <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-slate-500" />
                                <p className="text-slate-500">Loading graph...</p>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full bg-slate-900/50 rounded-lg border border-slate-800 p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-sm">Knowledge Graph</h3>
                                <div className="text-xs text-slate-500">
                                    {graphData.nodes.length} nodes • {graphData.edges.length} edges
                                </div>
                            </div>

                            {graphData.nodes.length === 0 ? (
                                <div className="h-full flex items-center justify-center text-slate-500">
                                    <div className="text-center">
                                        <p>No entities discovered yet.</p>
                                        <p className="text-sm mt-2">Data collection is in progress...</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[calc(100%-3rem)] overflow-y-auto">
                                    {graphData.nodes.map((node) => (
                                        <div
                                            key={node.id}
                                            className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-blue-500/50 transition-colors"
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="font-medium text-sm truncate flex-1">{node.label}</div >
                                                <span className="text-xs text-slate-500 ml-2">{node.type}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 bg-slate-900 rounded-full h-1.5">
                                                    <div
                                                        className="bg-blue-500 h-full rounded-full"
                                                        style={{ width: `${node.confidence * 100}%` }}
                                                    />
                                                </div>
                                                <span className="text-xs text-slate-500">{Math.round(node.confidence * 100)}%</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </main>
    );
}
