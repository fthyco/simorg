"use client";

import React from "react";
import type { Diagnostics } from "@/types";

interface DiagnosticsPanelProps {
    diagnostics: Diagnostics | null;
    eventCount: number;
}

const SCALE = 10000;

export default function DiagnosticsPanel({
    diagnostics,
    eventCount,
}: DiagnosticsPanelProps) {
    if (!diagnostics) {
        return (
            <div className="card">
                <div className="card-title">Diagnostics</div>
                <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
                    No data yet
                </div>
            </div>
        );
    }

    const densityPercent = Math.min(
        100,
        (diagnostics.structural_density / SCALE) * 100
    );

    const debtLevel =
        diagnostics.structural_debt > 10
            ? "high"
            : diagnostics.structural_debt > 5
                ? "medium"
                : "low";

    return (
        <div className="card">
            <div className="card-title">Diagnostics</div>

            {/* Metric grid */}
            <div className="metric-grid">
                <div className="metric-item">
                    <div className="metric-value">{diagnostics.role_count}</div>
                    <div className="metric-label">Total Roles</div>
                </div>
                <div className="metric-item">
                    <div className="metric-value">{diagnostics.active_role_count}</div>
                    <div className="metric-label">Active</div>
                </div>
                <div className="metric-item">
                    <div className="metric-value">{eventCount}</div>
                    <div className="metric-label">Events</div>
                </div>
                <div className="metric-item">
                    <div
                        className="metric-value"
                        style={{
                            color:
                                debtLevel === "high"
                                    ? "var(--accent-rose)"
                                    : debtLevel === "medium"
                                        ? "var(--accent-amber)"
                                        : undefined,
                            background:
                                debtLevel === "low" ? "var(--gradient-brand)" : "none",
                            WebkitBackgroundClip: debtLevel === "low" ? "text" : undefined,
                            WebkitTextFillColor:
                                debtLevel === "low" ? "transparent" : undefined,
                        }}
                    >
                        {diagnostics.structural_debt}
                    </div>
                    <div className="metric-label">Struct. Debt</div>
                </div>
            </div>

            {/* Density bar */}
            <div style={{ marginTop: 16 }}>
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 11,
                        color: "var(--text-muted)",
                        marginBottom: 4,
                    }}
                >
                    <span>Structural Density</span>
                    <span>{densityPercent.toFixed(1)}%</span>
                </div>
                <div className="density-bar-container">
                    <div
                        className="density-bar-fill"
                        style={{
                            width: `${densityPercent}%`,
                            background:
                                densityPercent > 70
                                    ? "var(--accent-rose)"
                                    : "var(--gradient-brand)",
                        }}
                    />
                </div>
            </div>

            {/* Governance edges */}
            {diagnostics.governance_edges > 0 && (
                <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-secondary)" }}>
                    Governance edges: <strong>{diagnostics.governance_edges}</strong>
                </div>
            )}

            {/* Warnings */}
            {diagnostics.warnings.length > 0 && (
                <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
                    <div className="card-title" style={{ marginBottom: 0 }}>
                        Warnings ({diagnostics.warnings.length})
                    </div>
                    {diagnostics.warnings.map((w, i) => (
                        <div key={i} className="warning-item">
                            <span className="warning-icon">⚠</span>
                            <span>{w}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
