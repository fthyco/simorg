"use client";

import React, { useState } from "react";
import { EVENT_TYPES, type EventType, type AppendEventRequest } from "@/types";

interface EventEditorProps {
    onSubmit: (req: AppendEventRequest) => Promise<void>;
    loading: boolean;
    roleIds: string[];
}

export default function EventEditor({
    onSubmit,
    loading,
    roleIds,
}: EventEditorProps) {
    const [eventType, setEventType] = useState<EventType>("add_role");
    const [error, setError] = useState("");

    // ── Field state ──
    const [roleId, setRoleId] = useState("");
    const [roleName, setRoleName] = useState("");
    const [rolePurpose, setRolePurpose] = useState("");
    const [responsibilities, setResponsibilities] = useState("");
    const [fromRoleId, setFromRoleId] = useState("");
    const [toRoleId, setToRoleId] = useState("");
    const [targetRoleId, setTargetRoleId] = useState("");
    const [magnitude, setMagnitude] = useState("5");
    const [depType, setDepType] = useState("operational");
    const [critical, setCritical] = useState(false);
    const [capitalDelta, setCapitalDelta] = useState("");
    const [talentDelta, setTalentDelta] = useState("");
    const [timeDelta, setTimeDelta] = useState("");
    const [politicalDelta, setPoliticalDelta] = useState("");
    const [sourceRoleId, setSourceRoleId] = useState("");

    function resetFields() {
        setRoleId("");
        setRoleName("");
        setRolePurpose("");
        setResponsibilities("");
        setFromRoleId("");
        setToRoleId("");
        setTargetRoleId("");
        setMagnitude("5");
        setCritical(false);
        setCapitalDelta("");
        setTalentDelta("");
        setTimeDelta("");
        setPoliticalDelta("");
        setSourceRoleId("");
        setError("");
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");

        let payload: Record<string, unknown> = {};

        try {
            switch (eventType) {
                case "add_role":
                    if (!roleId || !roleName) throw new Error("ID and Name are required");
                    payload = {
                        id: roleId,
                        name: roleName,
                        purpose: rolePurpose || roleName,
                        responsibilities: responsibilities
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                    };
                    if (payload.responsibilities && (payload.responsibilities as string[]).length === 0) {
                        payload.responsibilities = [`${roleId}_default`];
                    }
                    break;

                case "remove_role":
                    if (!targetRoleId) throw new Error("Role ID is required");
                    payload = { role_id: targetRoleId };
                    break;

                case "add_dependency":
                    if (!fromRoleId || !toRoleId) throw new Error("Both role IDs are required");
                    payload = {
                        from_role_id: fromRoleId,
                        to_role_id: toRoleId,
                        dep_type: depType,
                        critical,
                    };
                    break;

                case "inject_shock":
                    if (!targetRoleId) throw new Error("Target role ID is required");
                    payload = {
                        target_role_id: targetRoleId,
                        magnitude: parseInt(magnitude) || 5,
                    };
                    break;

                case "apply_constraint_change":
                    payload = {};
                    if (capitalDelta) payload.capital_delta = parseFloat(capitalDelta);
                    if (talentDelta) payload.talent_delta = parseFloat(talentDelta);
                    if (timeDelta) payload.time_delta = parseFloat(timeDelta);
                    if (politicalDelta) payload.political_cost_delta = parseFloat(politicalDelta);
                    break;

                case "differentiate_role":
                    if (!targetRoleId) throw new Error("Role ID is required");
                    payload = { role_id: targetRoleId };
                    break;

                case "compress_roles":
                    if (!sourceRoleId || !targetRoleId) throw new Error("Both role IDs are required");
                    payload = {
                        source_role_id: sourceRoleId,
                        target_role_id: targetRoleId,
                    };
                    break;
            }

            await onSubmit({
                event_type: eventType,
                payload,
                timestamp: new Date().toISOString(),
            });
            resetFields();
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
    }

    function RoleSelect({
        value,
        onChange,
        label,
    }: {
        value: string;
        onChange: (v: string) => void;
        label: string;
    }) {
        return (
            <div className="form-group">
                <label className="form-label">{label}</label>
                {roleIds.length > 0 ? (
                    <select
                        className="select-field"
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                    >
                        <option value="">Select...</option>
                        {roleIds.map((id) => (
                            <option key={id} value={id}>{id}</option>
                        ))}
                    </select>
                ) : (
                    <input
                        className="input-field"
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder="Role ID"
                    />
                )}
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-title">Event Editor</div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div className="form-group">
                    <label className="form-label">Event Type</label>
                    <select
                        className="select-field"
                        value={eventType}
                        onChange={(e) => { setEventType(e.target.value as EventType); setError(""); }}
                    >
                        {Object.entries(EVENT_TYPES).map(([key, val]) => (
                            <option key={key} value={key}>{val.label}</option>
                        ))}
                    </select>
                </div>

                {/* ── Add Role fields ── */}
                {eventType === "add_role" && (
                    <>
                        <div className="form-group">
                            <label className="form-label">Role ID</label>
                            <input className="input-field" value={roleId} onChange={(e) => setRoleId(e.target.value)} placeholder="e.g. eng_lead" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Name</label>
                            <input className="input-field" value={roleName} onChange={(e) => setRoleName(e.target.value)} placeholder="e.g. Engineering Lead" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Purpose</label>
                            <input className="input-field" value={rolePurpose} onChange={(e) => setRolePurpose(e.target.value)} placeholder="Optional" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Responsibilities (comma-separated)</label>
                            <input className="input-field" value={responsibilities} onChange={(e) => setResponsibilities(e.target.value)} placeholder="e.g. code_review, architecture" />
                        </div>
                    </>
                )}

                {/* ── Remove Role / Differentiate ── */}
                {(eventType === "remove_role" || eventType === "differentiate_role") && (
                    <RoleSelect value={targetRoleId} onChange={setTargetRoleId} label="Role" />
                )}

                {/* ── Add Dependency ── */}
                {eventType === "add_dependency" && (
                    <>
                        <RoleSelect value={fromRoleId} onChange={setFromRoleId} label="From Role" />
                        <RoleSelect value={toRoleId} onChange={setToRoleId} label="To Role" />
                        <div className="form-group">
                            <label className="form-label">Type</label>
                            <select className="select-field" value={depType} onChange={(e) => setDepType(e.target.value)}>
                                <option value="operational">Operational</option>
                                <option value="informational">Informational</option>
                                <option value="governance">Governance</option>
                            </select>
                        </div>
                        <div className="form-group" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                            <input type="checkbox" id="critical" checked={critical} onChange={(e) => setCritical(e.target.checked)} />
                            <label htmlFor="critical" className="form-label" style={{ marginBottom: 0 }}>Critical</label>
                        </div>
                    </>
                )}

                {/* ── Inject Shock ── */}
                {eventType === "inject_shock" && (
                    <>
                        <RoleSelect value={targetRoleId} onChange={setTargetRoleId} label="Target Role" />
                        <div className="form-group">
                            <label className="form-label">Magnitude (1–10)</label>
                            <input className="input-field" type="number" min="1" max="10" value={magnitude} onChange={(e) => setMagnitude(e.target.value)} />
                        </div>
                    </>
                )}

                {/* ── Constraint Change ── */}
                {eventType === "apply_constraint_change" && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        <div className="form-group">
                            <label className="form-label">Capital Δ</label>
                            <input className="input-field" type="number" step="0.5" value={capitalDelta} onChange={(e) => setCapitalDelta(e.target.value)} placeholder="0" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Talent Δ</label>
                            <input className="input-field" type="number" step="0.5" value={talentDelta} onChange={(e) => setTalentDelta(e.target.value)} placeholder="0" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Time Δ</label>
                            <input className="input-field" type="number" step="0.5" value={timeDelta} onChange={(e) => setTimeDelta(e.target.value)} placeholder="0" />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Political Δ</label>
                            <input className="input-field" type="number" step="0.5" value={politicalDelta} onChange={(e) => setPoliticalDelta(e.target.value)} placeholder="0" />
                        </div>
                    </div>
                )}

                {/* ── Compress Roles ── */}
                {eventType === "compress_roles" && (
                    <>
                        <RoleSelect value={sourceRoleId} onChange={setSourceRoleId} label="Source Role (absorbed)" />
                        <RoleSelect value={targetRoleId} onChange={setTargetRoleId} label="Target Role (absorbs)" />
                    </>
                )}

                {error && <div className="error-banner">{error}</div>}

                <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? "Applying…" : "Apply Event"}
                </button>
            </form>
        </div>
    );
}
