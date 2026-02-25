"use client";

import React from "react";
import type { TransitionResult } from "@/types";

interface EventOutcomePanelProps {
    result: TransitionResult | null;
}

export default function EventOutcomePanel({ result }: EventOutcomePanelProps) {
    if (!result) return null;

    return (
        <div className="card" style={{ marginTop: 16 }}>
            <div className="card-title">Event Outcome</div>
            <div style={{ fontSize: 13, marginBottom: 8, color: "var(--text-secondary)" }}>
                <strong>{result.event_type}</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* Structural Debt Causality */}
                {(result.primary_debt > 0 || result.secondary_debt > 0) && (
                    <div style={{ padding: 8, background: "rgba(239, 68, 68, 0.05)", borderLeft: "2px solid var(--accent-rose)", borderRadius: 4 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-rose)", marginBottom: 4, textTransform: "uppercase" }}>Debt Accrued</div>
                        <div style={{ fontSize: 12 }}>
                            <code>primary: +{result.primary_debt}</code>
                            {result.secondary_debt > 0 && <code>, secondary: +{result.secondary_debt}</code>}
                        </div>
                        {result.event_type === "inject_shock" && (
                            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>
                                Formula: <code>magnitude × (base_multiplier + density_scaled)</code>
                            </div>
                        )}
                        {result.suppressed_differentiation && (
                            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>
                                Cause: Suppressed differentiation — Capacity limitation.
                            </div>
                        )}
                    </div>
                )}

                {/* Density Effect */}
                {result.target_density > 0 && result.event_type === "inject_shock" && (
                    <div style={{ fontSize: 12, display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-muted)" }}>Target Density:</span>
                        <span style={{ fontWeight: 600 }}>{result.target_density}</span>
                    </div>
                )}

                {/* Operations Executed */}
                {result.differentiation_executed && (
                    <div style={{ fontSize: 12, color: "var(--brand-primary)", fontWeight: 500 }}>
                        ✓ Differentiation Executed
                    </div>
                )}
                {result.compression_executed && (
                    <div style={{ fontSize: 12, color: "var(--brand-primary)", fontWeight: 500 }}>
                        ✓ Compression Executed
                    </div>
                )}
                {result.differentiation_skipped && (
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        — Differentiation Skipped (Threshold not met)
                    </div>
                )}
                {result.deactivated && (
                    <div style={{ fontSize: 12, color: "var(--accent-rose)", fontWeight: 600 }}>
                        ⚠ Role Deactivated
                    </div>
                )}

                {/* Reason Tracking */}
                {result.reason && (
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic", marginTop: 4 }}>
                        {result.reason}
                    </div>
                )}
            </div>
        </div>
    );
}
