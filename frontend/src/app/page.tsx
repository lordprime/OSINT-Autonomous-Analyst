"use client";

import React, { useState } from 'react';
import { Search, Map, Calendar, Share2, ShieldAlert, Cpu, Database, Settings } from 'lucide-react';
import { cn } from "@/lib/utils";

// Placeholder components
const GraphView = () => (
    <div className="w-full h-full bg-slate-900/50 rounded-lg border border-slate-800 flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 grid grid-cols-[repeat(20,minmax(0,1fr))] grid-rows-[repeat(20,minmax(0,1fr))] opacity-10">
            {Array.from({ length: 400 }).map((_, i) => (
                <div key={i} className="border-[0.5px] border-slate-700" />
            ))}
        </div>
        <div className="text-slate-400 flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-full border-2 border-blue-500/30 flex items-center justify-center animate-pulse">
                <div className="w-3 h-3 bg-blue-500 rounded-full" />
            </div>
            <p className="text-sm font-mono">Initializing WebGL Graph Engine...</p>
        </div>
    </div>
);

const ChatInterface = () => (
    <div className="flex flex-col h-full bg-slate-900/50 rounded-lg border border-slate-800">
        <div className="p-4 border-b border-slate-800">
            <h3 className="font-semibold text-sm flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-500" />
                Reasoning Engine
            </h3>
        </div>
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
            <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center mt-1">
                    <Cpu className="w-4 h-4 text-purple-500" />
                </div>
                <div className="bg-slate-800 rounded-lg rounded-tl-none p-3 max-w-[80%] text-sm">
                    <p>Ready for investigation. Connected to Neo4j Knowledge Graph.</p>
                </div>
            </div>
        </div>
        <div className="p-4 border-t border-slate-800">
            <div className="relative">
                <input
                    type="text"
                    placeholder="Ask a question or enter a command..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                    <button className="p-1 hover:bg-slate-800 rounded">
                        <Search className="w-4 h-4 text-slate-500" />
                    </button>
                </div>
            </div>
        </div>
    </div>
);

export default function Dashboard() {
    const [activeView, setActiveView] = useState<'graph' | 'map' | 'timeline'>('graph');

    return (
        <main className="flex h-screen w-full bg-slate-950 text-slate-200 overflow-hidden font-sans">
            {/* Sidebar navigation */}
            <nav className="w-16 border-r border-slate-800 flex flex-col items-center py-4 gap-4 bg-slate-950/50">
                <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center mb-4 shadow-lg shadow-blue-500/20">
                    <ShieldAlert className="w-6 h-6 text-white" />
                </div>

                <NavButton icon={Database} active />
                <NavButton icon={Map} onClick={() => setActiveView('map')} active={activeView === 'map'} />
                <NavButton icon={Calendar} onClick={() => setActiveView('timeline')} active={activeView === 'timeline'} />

                <div className="mt-auto flex flex-col gap-4">
                    <NavButton icon={Settings} />
                    <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700" />
                </div>
            </nav>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Top Header */}
                <header className="h-14 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-950/50 backdrop-blur-sm">
                    <div className="flex items-center gap-4">
                        <h1 className="font-semibold text-slate-100">Operation: SILENT ECHO</h1>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-medium border border-emerald-500/20">
                            ACTIVE
                        </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400">
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            Infrastructure Online
                        </div>
                        <button className="flex items-center gap-2 hover:text-white transition-colors">
                            <Share2 className="w-4 h-4" />
                            Export Report
                        </button>
                    </div>
                </header>

                {/* Dashboard Grid */}
                <div className="flex-1 p-4 grid grid-cols-12 gap-4 overflow-hidden">
                    {/* Main Visualization Area */}
                    <div className="col-span-12 lg:col-span-8 h-full flex flex-col gap-4">
                        <div className="flex-1 relative">
                            <GraphView />

                            {/* Overlay Controls */}
                            <div className="absolute top-4 left-4 flex gap-2">
                                <ViewToggle icon={Database} label="Graph" active={activeView === 'graph'} onClick={() => setActiveView('graph')} />
                                <ViewToggle icon={Map} label="Geospatial" active={activeView === 'map'} onClick={() => setActiveView('map')} />
                                <ViewToggle icon={Calendar} label="Timeline" active={activeView === 'timeline'} onClick={() => setActiveView('timeline')} />
                            </div>
                        </div>

                        {/* Timeline/Metrics Strip */}
                        <div className="h-32 bg-slate-900/50 rounded-lg border border-slate-800 p-4">
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Investigation Activity</h4>
                            <div className="w-full h-full flex items-center justify-center text-slate-600 text-sm">
                                Activity Histogram Placeholder
                            </div>
                        </div>
                    </div>

                    {/* Right Panel - Chat & Details */}
                    <div className="col-span-12 lg:col-span-4 h-full flex flex-col gap-4">
                        <ChatInterface />

                        <div className="h-1/3 bg-slate-900/50 rounded-lg border border-slate-800 p-4">
                            <h3 className="font-semibold text-sm mb-3 text-slate-400">Selected Entity</h3>
                            <div className="space-y-2">
                                <div className="h-20 border border-dashed border-slate-700 rounded-md flex items-center justify-center text-slate-600 text-sm">
                                    Select a node to view details
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}

const NavButton = ({ icon: Icon, active, onClick }: { icon: any, active?: boolean, onClick?: () => void }) => (
    <button
        onClick={onClick}
        className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200",
            active
                ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/50"
        )}
    >
        <Icon className="w-5 h-5" />
    </button>
);

const ViewToggle = ({ icon: Icon, label, active, onClick }: { icon: any, label: string, active?: boolean, onClick?: () => void }) => (
    <button
        onClick={onClick}
        className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium backdrop-blur-md transition-all border",
            active
                ? "bg-slate-800/90 text-white border-slate-600 shadow-lg"
                : "bg-slate-900/60 text-slate-400 border-slate-800 hover:bg-slate-800"
        )}
    >
        <Icon className="w-4 h-4" />
        {label}
    </button>
);
