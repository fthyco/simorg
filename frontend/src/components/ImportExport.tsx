"use client";

import React, { useRef } from "react";
import type { StateResponse } from "@/types";

interface ImportExportProps {
    state: StateResponse | null;
    onImport: (events: Record<string, unknown>[]) => Promise<void>;
    loading: boolean;
}

export default function ImportExport({
    state,
    onImport,
    loading,
}: ImportExportProps) {
    const fileRef = useRef<HTMLInputElement>(null);
    const [error, setError] = React.useState("");

    function handleExport() {
        if (!state) return;
        const blob = new Blob(
            [JSON.stringify(state, null, 2)],
            { type: "application/json" }
        );
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `org-state-${state.event_count}-events.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
        setError("");
        const file = e.target.files?.[0];
        if (!file) return;

        try {
            const text = await file.text();
            const data = JSON.parse(text);

            // Accept either { events: [...] } or raw array
            let events: Record<string, unknown>[];
            if (Array.isArray(data)) {
                events = data;
            } else if (data.events && Array.isArray(data.events)) {
                events = data.events;
            } else {
                throw new Error("Expected { events: [...] } or an array of events");
            }

            await onImport(events);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }

        // Reset file input
        if (fileRef.current) fileRef.current.value = "";
    }

    return (
        <div className="card">
            <div className="card-title">Import / Export</div>

            <div className="io-buttons">
                <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleExport}
                    disabled={!state || state.event_count === 0}
                >
                    ⬇ Export JSON
                </button>

                <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => fileRef.current?.click()}
                    disabled={loading}
                >
                    ⬆ Import JSON
                </button>
            </div>

            <input
                ref={fileRef}
                type="file"
                accept=".json"
                className="file-input-hidden"
                onChange={handleImport}
            />

            {error && (
                <div className="error-banner" style={{ marginTop: 8 }}>
                    {error}
                </div>
            )}

            {state && state.event_count > 0 && (
                <div style={{ marginTop: 10, fontSize: 11, color: "var(--text-muted)" }}>
                    {state.event_count} events · hash: {state.state_hash.slice(0, 12)}…
                </div>
            )}
        </div>
    );
}
