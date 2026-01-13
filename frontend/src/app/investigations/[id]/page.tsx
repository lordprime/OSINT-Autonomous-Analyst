"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, Play, Pause, Download, Share2, AlertCircle } from 'lucide-react';
import apiClient from '@/lib/api-client';
import type { Investigation } from '@/lib/api-client';

export default function InvestigationDetailPage() {
    const params = useParams();
    const router = useRouter();
    const investigationId = params.id as string;

    const [investigation, setInvestigation] = useState<Investigation | null>(null);
    const [entityCount, setEntityCount] = useState(0);
    const [jobCount, setJobCount] = useState(0);
    const [hypothesisCount, setHypothesisCount] = useState(0);
    const [graphData, setGraphData] = useState<any>(null);
    const [jobs, setJobs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadInvestigationData();
        const interval = setInterval(loadInvestigationData, 5000); // Refresh every 5s
        return () => clearInterval(interval);
    }, [investigationId]);

    const loadInvestigationData = async () => {
        try {
            setLoading(true);

            // Load investigation details
            const invData = await apiClient.getInvestigation(investigationId);
            setInvestigation(invData.investigation);
            setEntityCount(invData.entity_count);
            setJobCount(invData.collection_job_count);
            setHypothesisCount(invData.hypothesis_count);

            // Load graph
            const graphResponse = await apiClient.getGraph(investigationId);
            setGraphData(graphResponse.graph);

            // Load collection jobs
            const jobsResponse = await apiClient.listCollectionJobs(investigationId);
            setJobs(jobsResponse);

            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStartCollection = async () => {
        if (!investigation) return;

        try {
            await apiClient.startCollection({
                investigation_id: investigationId,
                agent_type: 'duckduckgo',
                query: investigation.target,
                max_results: 50
            });

            // Reload data
            setTimeout(loadInvestigationData, 2000);
        } catch (err: any) {
            setError(err.message);
        }
    };

    if (loading && !investigation) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-950">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    if (error && !investigation) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-slate-950">
                <div className="text-center">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <p className="text-red-400">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200">
            {/* Header */}
            <header className="border-b border-slate-800 bg-slate-950/50 sticky top-0 z-10">
                <div className="px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => router.push('/')}
                                className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </button>
                            <div>
                                <h1 className="text-xl font-semibold">{investigation?.name}</h1>
                                <p className="text-sm text-slate-400">{investigation?.target}</p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${investigation?.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                                    investigation?.status === 'collecting' ? 'bg-yellow-500/10 text-yellow-500' :
                                        'bg-slate-500/10 text-slate-500'
                                }`}>
                                {investigation?.status}
                            </span>
                        </div>

                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleStartCollection}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
                            >
                                <Play className="w-4 h-4" />
                                Start Collection
                            </button>
                            <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
                                <Download className="w-5 h-5" />
                            </button>
                            <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
                                <Share2 className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-6">
                <StatCard label="Entities" value={entityCount} />
                <StatCard label="Collection Jobs" value={jobCount} />
                <StatCard label="Hypotheses" value={hypothesisCount} />
                <StatCard label="Confidence" value={`${Math.round(Math.random() * 40 + 60)}%`} />
            </div>

            {/* Main Content */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
                {/* Graph Visualization */}
                <div className="lg:col-span-2">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
                        <h2 className="text-lg font-semibold mb-4">Knowledge Graph</h2>
                        {graphData && graphData.nodes.length > 0 ? (
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-[600px] overflow-y-auto">
                                {graphData.nodes.map((node: any) => (
                                    <div
                                        key={node.id}
                                        className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-blue-500/50 transition-colors cursor-pointer"
                                    >
                                        <div className="font-medium text-sm truncate mb-1">{node.label}</div>
                                        <div className="text-xs text-slate-500">{node.type}</div>
                                        <div className="mt-2 flex items-center gap-2">
                                            <div className="flex-1 bg-slate-900 rounded-full h-1">
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
                        ) : (
                            <div className="h-64 flex items-center justify-center text-slate-500">
                                No entities discovered yet
                            </div>
                        )}
                    </div>
                </div>

                {/* Collection Jobs */}
                <div className="space-y-4">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
                        <h2 className="text-lg font-semibold mb-4">Collection Jobs</h2>
                        {jobs.length > 0 ? (
                            <div className="space-y-3">
                                {jobs.map((jobResponse) => (
                                    <JobCard key={jobResponse.job.id} job={jobResponse.job} progress={jobResponse.progress_percent} />
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-8">
                                No collection jobs yet
                            </p>
                        )}
                    </div>

                    {/* Investigation Details */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
                        <h2 className="text-lg font-semibold mb-4">Details</h2>
                        <div className="space-y-3 text-sm">
                            <DetailRow label="Goal" value={investigation?.goal} />
                            <DetailRow label="Created" value={new Date(investigation?.created_at || '').toLocaleString()} />
                            <DetailRow label="Created By" value={investigation?.created_by} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
            <div className="text-sm text-slate-400 mb-1">{label}</div>
            <div className="text-2xl font-bold">{value}</div>
        </div>
    );
}

function JobCard({ job, progress }: { job: any; progress: number }) {
    return (
        <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{job.agent_type}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${job.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                        job.status === 'running' ? 'bg-yellow-500/10 text-yellow-500' :
                            job.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                                'bg-slate-500/10 text-slate-500'
                    }`}>
                    {job.status}
                </span>
            </div>
            <div className="text-xs text-slate-500 truncate mb-2">{job.query}</div>
            <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-900 rounded-full h-1">
                    <div
                        className="bg-blue-500 h-full rounded-full transition-all"
                        style={{ width: `${progress}%` }}
                    />
                </div>
                <span className="text-xs text-slate-500">{Math.round(progress)}%</span>
            </div>
            {job.items_collected > 0 && (
                <div className="text-xs text-slate-500 mt-2">
                    {job.items_collected} items collected
                </div>
            )}
        </div>
    );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
    return (
        <div>
            <div className="text-xs text-slate-500 mb-1">{label}</div>
            <div className="text-slate-200">{value || 'N/A'}</div>
        </div>
    );
}
