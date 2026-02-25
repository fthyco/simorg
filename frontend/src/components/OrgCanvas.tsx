"use client";

import React, { useState, useCallback, useEffect } from "react";
import type { StateResponse, AppendEventRequest } from "@/types";
import { getState, appendEvent } from "@/lib/api";
import WorldMapLevel from "./levels/WorldMapLevel";
import DepartmentLevel from "./levels/DepartmentLevel";
import GraphView from "./GraphView";
import EventEditor from "./EventEditor";
import DiagnosticsPanel from "./DiagnosticsPanel";
import EventOutcomePanel from "./EventOutcomePanel";
import Link from "next/link";
import { verifyDeterminism } from "@/lib/api";
import type { TransitionResult } from "@/types";

export default function OrgCanvas({ projectId }: { projectId: string }) {
    const [zoomLevel, setZoomLevel] = useState<number>(1);
    const [state, setState] = useState<StateResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [focusDeptId, setFocusDeptId] = useState<string | null>(null);
    const [lastResult, setLastResult] = useState<TransitionResult | null>(null);
    const [determinismStatus, setDeterminismStatus] = useState<string | null>(null);

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
        setDeterminismStatus(null);
        try {
            const data = await appendEvent(projectId, req);
            setState(data);
            if (data.transition_results && data.transition_results.length > 0) {
                setLastResult(data.transition_results[data.transition_results.length - 1]);
            }
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
                            <div className="meta-item" style={{ borderLeft: "1px solid var(--border-subtle)", paddingLeft: 12, marginLeft: 12 }}>
                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={async () => {
                                        setLoading(true);
                                        try {
                                            const res = await verifyDeterminism(projectId);
                                            setDeterminismStatus(res.message);
                                        } catch (e: any) {
                                            setDeterminismStatus(`Failed: ${e.message}`);
                                        } finally {
                                            setLoading(false);
                                        }
                                    }}
                                >
                                    Verify Determinism
                                </button>
                            </div>
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
                {determinismStatus && (
                    <div className="error-banner-container" style={{ top: error ? 100 : 64 }}>
                        <div className={determinismStatus.startsWith("Failed") ? "error-banner" : "error-banner"} style={{ background: determinismStatus.startsWith("Failed") ? undefined : "var(--brand-primary)" }}>
                            {determinismStatus}
                        </div>
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
                        }}>
                            <EventEditor
                                onSubmit={handleEvent}
                                loading={loading || !!determinismStatus?.startsWith("Failed")}
                                roleIds={roleIds}
                            />
                            {lastResult && <EventOutcomePanel result={lastResult} />}
                        </div>
                    </div>
                )}

                <div className="diagnostics-floating">
                    <DiagnosticsPanel
                        diagnostics={state?.diagnostics ?? null}
                        eventCount={state?.event_count ?? 0}
                        transitionResults={state?.transition_results}
                    />
                </div>
            </main>
        </div>
    );
}
