"use client";

import React, { useEffect, useState } from "react";
import { listProjects, deleteProject, duplicateProject, generateOrg, renameProject, ProjectMetadata, GeneratorRequest } from "@/lib/api";
import Link from "next/link";

export default function ControlCenter() {
    const [projects, setProjects] = useState<ProjectMetadata[]>([]);
    const [loading, setLoading] = useState(true);

    // Org Modal State
    const [showModal, setShowModal] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [stage, setStage] = useState<string>("seed");
    const [industry, setIndustry] = useState<string>("tech_saas");
    const [successLevel, setSuccessLevel] = useState<number>(50);
    const [advanced, setAdvanced] = useState(false);
    const [overrides, setOverrides] = useState({
        capital: 50000, talent: 50000, time: 50000, political_cost: 50000,
        differentiation_threshold: 3, compression_limit: 5,
    });

    // Rename State
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [renameValue, setRenameValue] = useState("");

    const getSavedProjectIds = (): string[] => {
        if (typeof window === "undefined") return [];
        try {
            const saved = localStorage.getItem("myOrgProjectIds");
            return saved ? JSON.parse(saved) : [];
        } catch {
            return [];
        }
    };

    const saveProjectId = (id: string) => {
        const saved = getSavedProjectIds();
        if (!saved.includes(id)) {
            saved.push(id);
            localStorage.setItem("myOrgProjectIds", JSON.stringify(saved));
        }
    };

    const removeProjectId = (id: string) => {
        const saved = getSavedProjectIds();
        const next = saved.filter(savedId => savedId !== id);
        localStorage.setItem("myOrgProjectIds", JSON.stringify(next));
    };

    const fetchProjects = async () => {
        setLoading(true);
        try {
            const savedIds = getSavedProjectIds();
            if (savedIds.length === 0) {
                setProjects([]);
                setLoading(false);
                return;
            }
            const data = await listProjects(savedIds);
            setProjects(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm("Delete this session?")) return;
        try {
            await deleteProject(id);
            removeProjectId(id);
            await fetchProjects();
        } catch (err) {
            console.error(err);
        }
    };

    const handleDuplicate = async (id: string, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        const newId = crypto.randomUUID();
        try {
            await duplicateProject(id, newId);
            saveProjectId(newId);
            await fetchProjects();
        } catch (err) {
            console.error(err);
        }
    };

    const startRename = (id: string, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setRenamingId(id);
        setRenameValue(id);
    };

    const confirmRename = async (e: React.FormEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!renamingId || !renameValue.trim() || renameValue === renamingId) {
            setRenamingId(null);
            return;
        }
        try {
            await renameProject(renamingId, renameValue.trim());

            // Update local storage to point to the new ID
            const savedIds = getSavedProjectIds();
            const idx = savedIds.indexOf(renamingId);
            if (idx !== -1) {
                savedIds[idx] = renameValue.trim();
                localStorage.setItem("myOrgProjectIds", JSON.stringify(savedIds));
            }

            setRenamingId(null);
            await fetchProjects();
        } catch (err) {
            console.error(err);
            alert("Failed to rename session.");
        }
    };

    const handleGenerate = async () => {
        setSubmitting(true);
        const newId = crypto.randomUUID();
        try {
            await generateOrg(newId, {
                stage, industry, success_level: successLevel,
                ...(advanced ? { overrides } : {})
            });
            saveProjectId(newId);
            window.location.href = `/session/${newId}`;
        } catch (err) {
            console.error(err);
            alert("Failed to generate organization.");
        } finally {
            setSubmitting(false);
            setShowModal(false);
        }
    };

    return (
        <div className="app-layout" style={{ background: "#ffffff", overflowY: "auto" }}>
            <header className="app-header">
                <Link href="/" style={{ textDecoration: "none" }}>
                    <div className="header-brand" style={{ cursor: "pointer" }}>⬡ OrgKernel <span style={{ color: "var(--text-muted)", marginLeft: "8px", fontSize: "11px", fontWeight: "normal" }}>Control Center</span></div>
                </Link>
                <div className="header-meta">
                    <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>+ Create New Org</button>
                </div>
            </header>

            <main style={{ padding: "40px", maxWidth: "1200px", margin: "0 auto", width: "100%" }}>
                {loading && projects.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>Loading Sessions...</div>
                ) : projects.length === 0 ? (
                    <div className="empty-state" style={{ minHeight: "60vh" }}>
                        <div className="empty-state-icon">⬡</div>
                        <div className="empty-state-text">No sessions yet. Create your first organization.</div>
                        <button className="btn btn-primary" onClick={() => setShowModal(true)} style={{ marginTop: "16px" }}>+ Create New Org</button>
                    </div>
                ) : (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
                        {projects.map(p => (
                            <Link href={`/session/${p.project_id}`} key={p.project_id} style={{ textDecoration: "none", color: "inherit", display: "block" }}>
                                <div className="card session-card" style={{ cursor: "pointer", position: "relative" }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
                                        <div style={{ flex: 1 }}>
                                            {renamingId === p.project_id ? (
                                                <form onSubmit={confirmRename} onClick={e => e.stopPropagation()} style={{ display: "flex", gap: "4px" }}>
                                                    <input
                                                        autoFocus
                                                        className="input-field"
                                                        value={renameValue}
                                                        onChange={(e) => setRenameValue(e.target.value)}
                                                        onBlur={() => setRenamingId(null)}
                                                        style={{ fontSize: "13px", padding: "4px 8px", height: "28px" }}
                                                    />
                                                </form>
                                            ) : (
                                                <div
                                                    onDoubleClick={(e) => startRename(p.project_id, e)}
                                                    title="Double-click to rename"
                                                    style={{ fontWeight: 700, fontSize: "14px", marginBottom: "4px", cursor: "text" }}
                                                >
                                                    {p.project_id}
                                                </div>
                                            )}
                                            <div style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "monospace" }}>{p.state_hash?.slice(0, 12) || "—"}</div>
                                        </div>
                                        <div style={{ textAlign: "right" }}>
                                            <div style={{ fontSize: "10px", textTransform: "uppercase", fontWeight: 600, color: "var(--text-secondary)" }}>{p.stage || "—"}</div>
                                            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{p.industry || "—"}</div>
                                        </div>
                                    </div>

                                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "16px" }}>
                                        <div>
                                            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Events</div>
                                            <div style={{ fontSize: "18px", fontWeight: 700 }}>{p.event_count}</div>
                                        </div>
                                        <div style={{ textAlign: "center" }}>
                                            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Debt</div>
                                            <div style={{ fontSize: "18px", fontWeight: 700, color: p.structural_debt > 1000 ? "var(--accent-rose)" : "inherit" }}>
                                                {p.structural_debt}
                                            </div>
                                        </div>
                                        <div style={{ textAlign: "right" }}>
                                            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Density</div>
                                            <div style={{ fontSize: "18px", fontWeight: 700 }}>{p.structural_density}</div>
                                        </div>
                                    </div>

                                    {p.structural_debt > 1000 && (
                                        <div style={{ fontSize: "10px", color: "var(--accent-rose)", marginBottom: "12px", background: "rgba(239, 68, 68, 0.06)", padding: "4px 8px", borderRadius: "4px", display: "inline-block" }}>
                                            ⚠ High Structural Debt
                                        </div>
                                    )}

                                    <div style={{ display: "flex", gap: "8px", borderTop: "1px solid var(--border-subtle)", paddingTop: "12px" }}>
                                        <button className="btn btn-secondary btn-sm" style={{ flex: 1, fontSize: "10px" }}>Open</button>
                                        <button className="btn btn-secondary btn-sm" style={{ fontSize: "10px" }} onClick={(e) => startRename(p.project_id, e)}>Rename</button>
                                        <button className="btn btn-secondary btn-sm" style={{ fontSize: "10px" }} onClick={(e) => handleDuplicate(p.project_id, e)}>Clone</button>
                                        <button className="btn btn-secondary btn-sm" style={{ fontSize: "10px", color: "var(--accent-rose)" }} onClick={(e) => handleDelete(p.project_id, e)}>Delete</button>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </main>

            {/* Generator Modal */}
            {showModal && (
                <div className="loading-overlay" style={{ alignItems: "center", justifyContent: "center" }}>
                    <div className="lobby-modal" style={{ width: "480px", maxHeight: "85vh", overflowY: "auto", position: "relative", zIndex: 100 }}>
                        <h2>Organizational Modeling Engine</h2>
                        <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
                            Configure the topological seeds and constraint profile for a new simulation session.
                        </p>

                        <div className="form-group" style={{ marginBottom: "20px" }}>
                            <label style={{ display: "block", marginBottom: "8px", fontWeight: 600, textAlign: "left" }}>Scale Stage</label>
                            <select value={stage} onChange={(e) => setStage(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid var(--border-color)", backgroundColor: "#f8fafc" }}>
                                <option value="seed">Seed (Lean, singular focus)</option>
                                <option value="growth">Growth (Emerging specialization)</option>
                                <option value="structured">Structured (Formal departments)</option>
                                <option value="mature">Mature (High density, high debt risk)</option>
                            </select>
                        </div>
                        <div className="form-group" style={{ marginBottom: "20px" }}>
                            <label style={{ display: "block", marginBottom: "8px", fontWeight: 600, textAlign: "left" }}>Industry Topology</label>
                            <select value={industry} onChange={(e) => setIndustry(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid var(--border-color)", backgroundColor: "#f8fafc" }}>
                                <option value="tech_saas">Tech SaaS (Hub & Spoke / Dense Product)</option>
                                <option value="manufacturing">Manufacturing (Linear Supply Chain)</option>
                                <option value="marketplace">Marketplace (Multi-Cluster Supply/Demand)</option>
                            </select>
                        </div>
                        <div className="form-group" style={{ marginBottom: "24px" }}>
                            <label style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontWeight: 600 }}>
                                <span>Success Level (Constraint Proxy)</span>
                                <span style={{ color: "var(--brand-primary)" }}>{successLevel}</span>
                            </label>
                            <input type="range" min="1" max="100" value={successLevel} onChange={(e) => setSuccessLevel(parseInt(e.target.value, 10))} style={{ width: "100%", accentColor: "#1f2937" }} />
                        </div>
                        <div style={{ marginBottom: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
                            <label style={{ display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 600 }}>
                                <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} style={{ marginRight: "8px" }} />
                                Advanced Constraint Overrides
                            </label>
                            {advanced && (
                                <div style={{ marginTop: "16px", padding: "16px", backgroundColor: "#f8fafc", borderRadius: "6px", fontSize: "13px" }}>
                                    {Object.entries(overrides).map(([key, val]) => (
                                        <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
                                            <label>{key}</label>
                                            <input type="number" value={val} onChange={(e) => setOverrides(prev => ({ ...prev, [key]: parseInt(e.target.value) || 0 }))} style={{ width: "80px", padding: "4px", borderRadius: "4px", border: "1px solid var(--border-subtle)", textAlign: "right" }} />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="modal-actions" style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "16px" }}>
                            <button className="btn btn-secondary" onClick={() => setShowModal(false)} disabled={submitting}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleGenerate} disabled={submitting}>
                                {submitting ? "Initializing Sequence..." : "Generate Organization"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
