"use client";

import React, { useState } from "react";
import type { GeneratorRequest } from "@/lib/api";

interface LobbyLevelProps {
    onGenerateSubmit: (req: GeneratorRequest) => Promise<void>;
}

export default function LobbyLevel({ onGenerateSubmit }: LobbyLevelProps) {
    const [showModal, setShowModal] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Form State
    const [stage, setStage] = useState<string>("seed");
    const [industry, setIndustry] = useState<string>("tech_saas");
    const [successLevel, setSuccessLevel] = useState<number>(50); // 1-100

    // Advanced State
    const [advanced, setAdvanced] = useState(false);
    const [overrides, setOverrides] = useState({
        capital: 50000,
        talent: 50000,
        time: 50000,
        political_cost: 50000,
        differentiation_threshold: 3,
        compression_limit: 5,
    });

    const handleOverrideChange = (field: string, value: string) => {
        setOverrides(prev => ({ ...prev, [field]: parseInt(value, 10) || 0 }));
    };

    const handleInitialize = async () => {
        setSubmitting(true);
        try {
            await onGenerateSubmit({
                stage,
                industry,
                success_level: successLevel,
                ...(advanced ? { overrides } : {})
            });
        } finally {
            setSubmitting(false);
            setShowModal(false);
        }
    };

    return (
        <div className="lobby-container">
            {!showModal ? (
                <div className="lobby-actions">
                    <button
                        className="btn btn-primary lobby-btn"
                        onClick={() => setShowModal(true)}
                    >
                        New Organization
                    </button>
                    <button className="btn btn-secondary lobby-btn" disabled>
                        Load Organization
                    </button>
                    <div className="lobby-note">
                        (Organizations load automatically on boot from Supabase if they exist)
                    </div>
                </div>
            ) : (
                <div className="lobby-modal" style={{ width: "480px", maxHeight: "85vh", overflowY: "auto" }}>
                    <h2>Organizational Modeling Engine</h2>
                    <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
                        Configure the topological seeds and constraint profile for the deterministic simulation.
                    </p>

                    {/* Section 1: Stage */}
                    <div className="form-group" style={{ marginBottom: "20px" }}>
                        <label style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>Scale Stage</label>
                        <select
                            value={stage}
                            onChange={(e) => setStage(e.target.value)}
                            style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid var(--border-color)", backgroundColor: "#f8fafc" }}
                        >
                            <option value="seed">Seed (Lean, singular focus)</option>
                            <option value="growth">Growth (Emerging specialization)</option>
                            <option value="structured">Structured (Formal departments)</option>
                            <option value="mature">Mature (High density, high debt risk)</option>
                        </select>
                    </div>

                    {/* Section 2: Industry */}
                    <div className="form-group" style={{ marginBottom: "20px" }}>
                        <label style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>Industry Topology</label>
                        <select
                            value={industry}
                            onChange={(e) => setIndustry(e.target.value)}
                            style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid var(--border-color)", backgroundColor: "#f8fafc" }}
                        >
                            <option value="tech_saas">Tech SaaS (Hub & Spoke / Dense Product)</option>
                            <option value="manufacturing">Manufacturing (Linear Supply Chain)</option>
                            <option value="marketplace">Marketplace (Multi-Cluster Supply/Demand)</option>
                        </select>
                    </div>

                    {/* Section 3: Success Level */}
                    <div className="form-group" style={{ marginBottom: "24px" }}>
                        <label style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontWeight: 600 }}>
                            <span>Success Level (Constraint Proxy)</span>
                            <span style={{ color: "var(--brand-primary)" }}>{successLevel}</span>
                        </label>
                        <input
                            type="range"
                            min="1"
                            max="100"
                            value={successLevel}
                            onChange={(e) => setSuccessLevel(parseInt(e.target.value, 10))}
                            style={{ width: "100%", accentColor: "var(--brand-primary)" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                            <span>Weak</span>
                            <span>Stable</span>
                            <span>Dominant</span>
                        </div>
                    </div>

                    {/* Section 4: Advanced Toggle */}
                    <div style={{ marginBottom: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-color)" }}>
                        <label style={{ display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 600 }}>
                            <input
                                type="checkbox"
                                checked={advanced}
                                onChange={(e) => setAdvanced(e.target.checked)}
                                style={{ marginRight: "8px" }}
                            />
                            Advanced Constraint Overrides
                        </label>

                        {advanced && (
                            <div style={{ marginTop: "16px", padding: "16px", backgroundColor: "#f8fafc", borderRadius: "6px", fontSize: "13px" }}>
                                {Object.entries(overrides).map(([key, val]) => (
                                    <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
                                        <label>{key}</label>
                                        <input
                                            type="number"
                                            value={val}
                                            onChange={(e) => handleOverrideChange(key, e.target.value)}
                                            style={{ width: "80px", padding: "4px", borderRadius: "4px", border: "1px solid var(--border-color)", textAlign: "right" }}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="modal-actions" style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "16px" }}>
                        <button
                            className="btn btn-secondary"
                            onClick={() => setShowModal(false)}
                            disabled={submitting}
                        >
                            Cancel
                        </button>
                        <button
                            className="btn btn-primary"
                            onClick={handleInitialize}
                            disabled={submitting}
                        >
                            {submitting ? "Initializing Sequence..." : "Generate Organization"}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
