"use client";

import React, { useState, useCallback, useEffect } from "react";
import type { StateResponse, AppendEventRequest } from "@/types";
import { getState, appendEvent } from "@/lib/api";
import WorldMapLevel from "./levels/WorldMapLevel";
import DepartmentLevel from "./levels/DepartmentLevel";
import GraphView from "./GraphView";
import EventEditor from "./EventEditor";
import DiagnosticsPanel from "./DiagnosticsPanel";
import Link from "next/link";

export default function OrgCanvas({ projectId }: { projectId: string }) {
    const [zoomLevel, setZoomLevel] = useState<number>(1);
    const [state, setState] = useState<StateResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [focusDeptId, setFocusDeptId] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const data = await getState(projectId);
            setState(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { refresh(); }, [refresh]);

    const handleEvent = async (req: AppendEventRequest) => {
        setLoading(true);
        setError("");
        try {
            const data = await appendEvent(projectId, req);
            setState(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const goToRolesOverview = useCallback(() => { setFocusDeptId(null); setZoomLevel(3); }, []);
    const goToRolesFocused = useCallback((deptId: string) => { setFocusDeptId(deptId); setZoomLevel(3); }, []);
    const clearFocus = useCallback(() => { setFocusDeptId(null); }, []);

    const scaleStage = state?.roles && Object.keys(state.roles).length > 0
        ? Object.values(state.roles)[0]?.scale_stage ?? ""
        : "";

    const roleIds = state ? Object.keys(state.roles) : [];

    const viewLabel = zoomLevel === 3
        ? focusDeptId
            ? state?.projection?.departments.find(d => d.id === focusDeptId)?.semantic_label || "Focused"
            : "All Roles"
        : zoomLevel === 2 ? "Departments" : "Overview";

    return (
        <div className="app-layout">
            <header className="app-header">
                <Link href="/" style={{ textDecoration: "none" }}>
                    <div className="header-brand" style={{ cursor: "pointer" }}>OrgKernel</div>
                </Link>
                <div className="header-meta">
                    <div className="meta-item">
                        <span className="meta-label">project</span>
                        <span className="meta-value">{projectId}</span>
                    </div>
                    <div className="meta-item">
                        <span className="meta-label">view</span>
                        <span className="meta-value">{viewLabel}</span>
                    </div>
                    {state && (
                        <>
                            <div className="meta-item">
                                <span className="meta-label">seq</span>
                                <span className="meta-value">{state.event_count}</span>
                            </div>
                            <div className="meta-item">
                                <span className="meta-label">hash</span>
                                <span className="hash-badge">{state.state_hash.slice(0, 10)}</span>
                            </div>
                            {scaleStage && (
                                <div className="meta-item">
                                    <span className="meta-label">stage</span>
                                    <span className="meta-value">{scaleStage}</span>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </header>

            <main className="main-canvas">
                {loading && (
                    <div className="loading-overlay"><div className="spinner" /></div>
                )}
                {error && (
                    <div className="error-banner-container">
                        <div className="error-banner">{error}</div>
                    </div>
                )}

                {zoomLevel === 1 && (
                    <WorldMapLevel state={state} onZoomIn={() => setZoomLevel(2)} />
                )}

                {zoomLevel === 2 && (
                    <DepartmentLevel
                        state={state}
                        onZoomOut={() => setZoomLevel(1)}
                        onZoomToRoles={goToRolesOverview}
                        onZoomToDept={goToRolesFocused}
                    />
                )}

                {zoomLevel === 3 && (
                    <div style={{ width: "100%", height: "100%", position: "relative" }}>
                        <GraphView
                            roles={state?.roles ?? {}}
                            dependencies={state?.dependencies ?? []}
                            projection={state?.projection ?? null}
                            focusDeptId={focusDeptId}
                            onClearFocus={clearFocus}
                            onBackToDepts={() => setZoomLevel(2)}
                        />

                        <div style={{
                            position: "absolute", bottom: 24, left: 24, zIndex: 10,
                            width: 320, maxHeight: "calc(100vh - 120px)", overflowY: "auto",
                            boxShadow: "var(--shadow-card)", borderRadius: "var(--radius-lg)"
                        }}>
                            <EventEditor onSubmit={handleEvent} loading={loading} roleIds={roleIds} />
                        </div>
                    </div>
                )}

                <div className="diagnostics-floating">
                    <DiagnosticsPanel diagnostics={state?.diagnostics ?? null} eventCount={state?.event_count ?? 0} />
                </div>
            </main>
        </div>
    );
}
