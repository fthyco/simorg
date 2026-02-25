"use client";

import React, { useMemo } from "react";
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    Handle,
    Position,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import type { Role, Dependency, Projection } from "@/types";

const DEPT_COLORS = [
    "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b",
    "#ef4444", "#06b6d4", "#ec4899", "#f97316",
];

const SCALE = 10000;

function getDeptColor(deptId: string, deptIds: string[]): string {
    const idx = deptIds.indexOf(deptId);
    return DEPT_COLORS[idx % DEPT_COLORS.length] || DEPT_COLORS[0];
}

// ── Role Node ─────────────────────────────────────────────────

interface RoleNodeData {
    role: Role;
    deptColor: string;
    [key: string]: unknown;
}

function RoleNode({ data }: NodeProps<Node<RoleNodeData>>) {
    const { role, deptColor } = data;
    return (
        <div className="role-node" style={{ position: "relative" }}>
            <div className="dept-stripe" style={{ backgroundColor: deptColor }} />
            <Handle type="target" position={Position.Top} />
            <div className="role-node-header">
                <span className="role-node-name">{role.name}</span>
                <span className={`status-badge ${role.active ? "status-active" : "status-inactive"}`}>
                    {role.active ? "active" : "inactive"}
                </span>
            </div>
            <div className="role-node-id">{role.id}</div>
            <div className="role-node-responsibilities">
                {role.responsibilities.slice(0, 3).map((r) => (
                    <span key={r} className="resp-tag">{r}</span>
                ))}
                {role.responsibilities.length > 3 && (
                    <span className="resp-tag">+{role.responsibilities.length - 3}</span>
                )}
            </div>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

// ── Department Group Header ───────────────────────────────────

interface DeptGroupData {
    label: string;
    color: string;
    roleCount: number;
    density: number;
    [key: string]: unknown;
}

function DeptGroupNode({ data }: NodeProps<Node<DeptGroupData>>) {
    const densityPct = ((data.density / SCALE) * 100).toFixed(1);
    return (
        <div className="dept-group-node" style={{ borderColor: data.color }}>
            <div className="dept-group-stripe" style={{ backgroundColor: data.color }} />
            <div className="dept-group-label">{data.label}</div>
            <div className="dept-group-meta">
                {data.roleCount} roles / {densityPct}% density
            </div>
        </div>
    );
}

const nodeTypes = { roleNode: RoleNode, deptGroup: DeptGroupNode };

// ── Layout ────────────────────────────────────────────────────

function layoutGraph(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "TB", ranksep: 80, nodesep: 50, marginx: 40, marginy: 40 });
    nodes.forEach((n) => g.setNode(n.id, { width: n.type === "deptGroup" ? 280 : 200, height: n.type === "deptGroup" ? 50 : 90 }));
    edges.forEach((e) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    return {
        nodes: nodes.map((n) => {
            const pos = g.node(n.id);
            return pos ? { ...n, position: { x: pos.x - 100, y: pos.y - 45 } } : n;
        }),
        edges,
    };
}

// ── Clustered layout ──────────────────────────────────────────

function layoutClustered(
    roles: Record<string, Role>,
    dependencies: Dependency[],
    projection: Projection,
    filters: any
): { nodes: Node[]; edges: Edge[] } {
    const deptIds = projection.departments.map((d) => d.id);
    const allNodes: Node[] = [];
    const allEdges: Edge[] = [];
    let xOffset = 0;
    const DEPT_GAP = 80;
    const ROLE_GAP_Y = 130;
    const ROLE_WIDTH = 220;
    const HEADER_HEIGHT = 60;

    for (const dept of projection.departments) {
        const color = getDeptColor(dept.id, deptIds);
        const deptRoles = dept.role_ids.map((rid) => roles[rid]).filter(Boolean);
        if (deptRoles.length === 0) continue;
        const colWidth = Math.max(ROLE_WIDTH + 40, 280);
        const colCenter = xOffset + colWidth / 2;

        allNodes.push({
            id: `group-${dept.id}`, type: "deptGroup",
            position: { x: colCenter - 140, y: 0 },
            draggable: false, selectable: false,
            data: { label: dept.semantic_label, color, roleCount: deptRoles.length, density: dept.internal_density },
        });

        deptRoles.forEach((role, i) => {
            allNodes.push({
                id: role.id, type: "roleNode",
                position: { x: colCenter - ROLE_WIDTH / 2, y: HEADER_HEIGHT + i * ROLE_GAP_Y },
                draggable: true, data: { role, deptColor: color },
            });
        });
        xOffset += colWidth + DEPT_GAP;
    }

    const validRoleIds = new Set(Object.keys(roles));
    dependencies.forEach((dep, i) => {
        if (!validRoleIds.has(dep.from_role_id) || !validRoleIds.has(dep.to_role_id)) return;

        // Filter logic
        if (filters.criticalOnly && !dep.critical) return;
        const dt = dep.dependency_type || "operational";
        if (!filters.operational && dt === "operational") return;
        if (!filters.informational && dt === "informational") return;
        if (!filters.governance && dt === "governance") return;

        const fromDept = projection.role_to_department?.[dep.from_role_id];
        const toDept = projection.role_to_department?.[dep.to_role_id];
        const crossDept = fromDept !== toDept;
        const isInfo = dt === "informational";
        const isGov = dt === "governance";

        allEdges.push({
            id: `e-${dep.from_role_id}-${dep.to_role_id}-${i}`,
            source: dep.from_role_id, target: dep.to_role_id,
            animated: dep.critical,
            style: {
                stroke: dep.critical ? "#ef4444" : isGov ? "#8b5cf6" : isInfo ? "#3b82f6" : crossDept ? "#f59e0b" : "#475569",
                strokeWidth: dep.critical ? 3 : isGov ? 2.5 : crossDept ? 2 : 1.5,
                strokeDasharray: dep.critical ? "6 3" : isGov ? "8 4" : isInfo ? "2 4" : crossDept ? "4 2" : undefined,
            },
            label: dt !== "operational" ? dt : undefined,
            labelStyle: { fontSize: 10, fill: "#94a3b8" },
        });
    });

    return { nodes: allNodes, edges: allEdges };
}

// ── Focused layout ────────────────────────────────────────────

function layoutFocused(
    deptId: string, roles: Record<string, Role>,
    dependencies: Dependency[], projection: Projection, filters: any
): { nodes: Node[]; edges: Edge[] } {
    const dept = projection.departments.find((d) => d.id === deptId);
    if (!dept) return { nodes: [], edges: [] };
    const deptIds = projection.departments.map((d) => d.id);
    const color = getDeptColor(dept.id, deptIds);
    const deptRoleSet = new Set(dept.role_ids);

    const rawNodes: Node[] = dept.role_ids.map((rid) => roles[rid]).filter(Boolean).map((role) => ({
        id: role.id, type: "roleNode" as const,
        position: { x: 0, y: 0 }, draggable: true,
        data: { role, deptColor: color },
    }));

    const rawEdges: Edge[] = [];
    dependencies.forEach((dep, i) => {
        if (!deptRoleSet.has(dep.from_role_id) || !deptRoleSet.has(dep.to_role_id)) return;

        // Filter logic
        if (filters.criticalOnly && !dep.critical) return;
        const dt = dep.dependency_type || "operational";
        if (!filters.operational && dt === "operational") return;
        if (!filters.informational && dt === "informational") return;
        if (!filters.governance && dt === "governance") return;

        const isInfo = dt === "informational";
        const isGov = dt === "governance";

        rawEdges.push({
            id: `e-${dep.from_role_id}-${dep.to_role_id}-${i}`,
            source: dep.from_role_id, target: dep.to_role_id,
            animated: dep.critical,
            style: {
                stroke: dep.critical ? "#ef4444" : isGov ? "#8b5cf6" : isInfo ? "#3b82f6" : "#475569",
                strokeWidth: dep.critical ? 3 : isGov ? 2.5 : 1.5,
                strokeDasharray: dep.critical ? "6 3" : isGov ? "8 4" : isInfo ? "2 4" : undefined,
            },
            label: dt !== "operational" ? dt : undefined,
            labelStyle: { fontSize: 10, fill: "#94a3b8" },
        });
    });

    return layoutGraph(rawNodes, rawEdges);
}

// ── Main ──────────────────────────────────────────────────────

interface GraphViewProps {
    roles: Record<string, Role>;
    dependencies: Dependency[];
    projection: Projection | null;
    focusDeptId?: string | null;
    onClearFocus?: () => void;
    onBackToDepts?: () => void;
}

export default function GraphView({
    roles, dependencies, projection, focusDeptId, onClearFocus, onBackToDepts,
}: GraphViewProps) {
    const deptIds = useMemo(() => projection?.departments.map((d) => d.id) ?? [], [projection]);

    const [filters, setFilters] = React.useState({
        operational: true,
        informational: true,
        governance: true,
        criticalOnly: false,
    });

    const focusDept = useMemo(() => {
        if (!focusDeptId || !projection) return null;
        return projection.departments.find((d) => d.id === focusDeptId) ?? null;
    }, [focusDeptId, projection]);

    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        if (Object.keys(roles).length === 0) return { nodes: [], edges: [] };
        if (focusDeptId && projection) return layoutFocused(focusDeptId, roles, dependencies, projection, filters);
        if (projection && projection.departments.length > 0) return layoutClustered(roles, dependencies, projection, filters);

        // Fallback
        const rawNodes: Node[] = Object.values(roles).map((role) => ({
            id: role.id, type: "roleNode" as const,
            position: { x: 0, y: 0 }, draggable: true,
            data: { role, deptColor: "#475569" },
        }));
        const rawEdges: Edge[] = dependencies.map((dep, i) => ({
            id: `e-${dep.from_role_id}-${dep.to_role_id}-${i}`,
            source: dep.from_role_id, target: dep.to_role_id,
            animated: dep.critical,
            style: { stroke: dep.critical ? "#ef4444" : "#475569", strokeWidth: 1.5 },
        }));
        return layoutGraph(rawNodes, rawEdges);
    }, [roles, dependencies, projection, deptIds, focusDeptId, filters]);

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    React.useEffect(() => { setNodes(initialNodes); setEdges(initialEdges); }, [initialNodes, initialEdges, setNodes, setEdges]);

    if (Object.keys(roles).length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-text">No roles. Use the event editor to begin.</div>
            </div>
        );
    }

    return (
        <div style={{ width: "100%", height: "100%", position: "relative" }}>
            {/* Toolbar */}
            <div className="graph-toolbar">
                {onBackToDepts && (
                    <button className="btn btn-sm btn-secondary" onClick={onBackToDepts}>
                        Departments
                    </button>
                )}
                {focusDept && onClearFocus && (
                    <>
                        <span className="toolbar-divider" />
                        <span className="toolbar-label">
                            {focusDept.semantic_label}
                            <span className="toolbar-meta">
                                {focusDept.role_ids.length} roles / {((focusDept.internal_density / SCALE) * 100).toFixed(1)}%
                            </span>
                        </span>
                        <button className="btn btn-sm btn-secondary" onClick={onClearFocus}>
                            Show all
                        </button>
                    </>
                )}
                {!focusDeptId && projection && projection.departments.length > 0 && (
                    <>
                        <span className="toolbar-divider" />
                        <span className="toolbar-label">
                            {projection.departments.length} departments
                        </span>
                    </>
                )}
                <span className="toolbar-divider" />
                <div style={{ display: "flex", gap: "8px", alignItems: "center", fontSize: "11px", color: "var(--text-secondary)" }}>
                    <label style={{ cursor: "pointer", display: "flex", gap: "4px" }}>
                        <input type="checkbox" checked={filters.operational} onChange={e => setFilters(f => ({ ...f, operational: e.target.checked }))} /> Ops
                    </label>
                    <label style={{ cursor: "pointer", display: "flex", gap: "4px" }}>
                        <input type="checkbox" checked={filters.informational} onChange={e => setFilters(f => ({ ...f, informational: e.target.checked }))} /> Info
                    </label>
                    <label style={{ cursor: "pointer", display: "flex", gap: "4px" }}>
                        <input type="checkbox" checked={filters.governance} onChange={e => setFilters(f => ({ ...f, governance: e.target.checked }))} /> Gov
                    </label>
                    <span className="toolbar-divider" />
                    <label style={{ cursor: "pointer", display: "flex", gap: "4px", color: filters.criticalOnly ? "var(--accent-rose)" : "inherit" }}>
                        <input type="checkbox" checked={filters.criticalOnly} onChange={e => setFilters(f => ({ ...f, criticalOnly: e.target.checked }))} /> Critical Only
                    </label>
                </div>
            </div>

            <ReactFlow
                nodes={nodes} edges={edges}
                onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes} nodesDraggable={true}
                fitView proOptions={{ hideAttribution: true }}
                minZoom={0.2} maxZoom={2}
            >
                <Background gap={24} size={1} color="rgba(148, 163, 184, 0.06)" />
                <Controls />
                <MiniMap nodeStrokeWidth={2} pannable zoomable
                    nodeColor={(n) => {
                        if (n.type === "deptGroup") return (n.data as DeptGroupData)?.color || "#475569";
                        return (n.data as RoleNodeData)?.deptColor || "#475569";
                    }}
                />
            </ReactFlow>
        </div>
    );
}
