import React, { useMemo } from "react";
import { ReactFlow, Background, Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { StateResponse } from "@/types";

interface WorldMapLevelProps {
    state: StateResponse | null;
    onZoomIn: () => void;
}

const SCALE = 10000;

function WorldNode({ data }: { data: any }) {
    return (
        <div className="world-node">
            <div className="world-node-content">
                <h3>{data.label}</h3>
                <div className="world-metrics">
                    <div className="w-metric">
                        <span>roles</span>
                        <strong>{data.roleCount}</strong>
                    </div>
                    <div className="w-metric">
                        <span>active</span>
                        <strong>{data.activeCount}</strong>
                    </div>
                    <div className="w-metric">
                        <span>debt</span>
                        <strong style={{ color: data.debt > 5 ? '#ef4444' : data.debt > 0 ? '#f59e0b' : 'inherit' }}>{data.debt}</strong>
                    </div>
                    <div className="w-metric">
                        <span>density</span>
                        <strong>{data.densityPct}%</strong>
                    </div>
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px', letterSpacing: '0.02em' }}>
                    {data.eventCount} events / {data.deptCount} departments
                </div>
            </div>
            <div className="world-actions">
                <button className="btn btn-sm btn-primary" onClick={data.onZoomIn}>
                    Departments
                </button>
            </div>
        </div>
    );
}

const nodeTypes = { worldNode: WorldNode };

export default function WorldMapLevel({ state, onZoomIn }: WorldMapLevelProps) {
    const roleCount = state ? Object.keys(state.roles).length : 0;
    const activeCount = state?.diagnostics?.active_role_count ?? 0;
    const debt = state?.diagnostics?.structural_debt ?? 0;
    const density = state?.diagnostics?.structural_density ?? 0;
    const densityPct = ((density / SCALE) * 100).toFixed(1);
    const eventCount = state?.event_count ?? 0;
    const deptCount = state?.projection?.departments?.length ?? 0;

    const initialNodes: Node[] = [
        {
            id: "org-root",
            type: "worldNode",
            position: { x: window.innerWidth / 2 - 150, y: window.innerHeight / 2 - 100 },
            data: { label: "Organization", roleCount, activeCount, debt, densityPct, eventCount, deptCount, onZoomIn },
        },
    ];

    const nodes = useMemo(() => initialNodes, [roleCount, activeCount, debt, densityPct, eventCount, deptCount, onZoomIn]);
    const edges: Edge[] = [];

    return (
        <div style={{ width: "100%", height: "100%" }}>
            <ReactFlow
                nodes={nodes} edges={edges} nodeTypes={nodeTypes}
                proOptions={{ hideAttribution: true }}
                fitView minZoom={0.5} maxZoom={2}
            >
                <Background color="#ccc" gap={16} />
            </ReactFlow>
        </div>
    );
}
