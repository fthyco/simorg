import React, { useMemo } from "react";
import {
    ReactFlow,
    Background,
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
import type { StateResponse, Department } from "@/types";

const DEPT_COLORS = [
    "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b",
    "#ef4444", "#06b6d4", "#ec4899", "#f97316",
];

const SCALE = 10000;

function getDeptColor(deptId: string, deptIds: string[]): string {
    const idx = deptIds.indexOf(deptId);
    return DEPT_COLORS[idx % DEPT_COLORS.length] || DEPT_COLORS[0];
}

interface DepartmentNodeData {
    department: Department;
    color: string;
    boundaryHeat: number;
    onZoomToRoles: () => void;
    onFocusDept: () => void;
    [key: string]: unknown;
}

function DepartmentNode({ data }: NodeProps<Node<DepartmentNodeData>>) {
    const { department, color, boundaryHeat, onZoomToRoles, onFocusDept } = data;
    const width = Math.min(200 + department.role_ids.length * 20, 350);
    const densityPct = ((department.internal_density / SCALE) * 100).toFixed(1);

    return (
        <div className="department-node"
            style={{
                width,
                borderColor: boundaryHeat > 0.5 ? "var(--accent-rose)" : color,
                boxShadow: boundaryHeat > 0.5 ? `0 0 15px rgba(239, 68, 68, 0.4)` : `0 0 15px ${color}33`,
                borderWidth: boundaryHeat > 0.5 ? 2 : 1
            }}
        >
            <Handle type="target" position={Position.Top} />
            <div className="dept-node-header">
                <h3>{department.semantic_label === "Unclassified"
                    ? department.id.replace("dept_", "Dep ").replace(/^Dep (\d+)/, (_, n) => `Dep ${parseInt(n) + 1}`)
                    : department.semantic_label}</h3>
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                    {boundaryHeat > 0.5 && (
                        <span title={`Boundary Heat: ${boundaryHeat.toFixed(2)}`} style={{ color: "var(--accent-rose)", fontSize: 13, cursor: "help" }}>🔥</span>
                    )}
                    <span className="dept-stage">{department.scale_stage}</span>
                </div>
            </div>
            <div className="dept-metrics">
                <div className="d-metric">
                    <span>roles</span>
                    <strong>{department.role_ids.length}</strong>
                </div>
                <div className="d-metric">
                    <span>density</span>
                    <strong>{densityPct}%</strong>
                </div>
            </div>
            <div className="dept-actions" style={{ gap: 6 }}>
                <button className="btn btn-sm btn-primary" onClick={onFocusDept}>Focus</button>
                <button className="btn btn-sm btn-secondary" onClick={onZoomToRoles}>All roles</button>
            </div>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

const nodeTypes = { departmentNode: DepartmentNode };

function layoutGraph(
    nodes: Node<DepartmentNodeData>[],
    edges: Edge[],
): { nodes: Node<DepartmentNodeData>[]; edges: Edge[] } {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "TB", ranksep: 100, nodesep: 80, marginx: 40, marginy: 40 });
    nodes.forEach((n) => {
        const width = Math.min(200 + n.data.department.role_ids.length * 20, 350);
        g.setNode(n.id, { width, height: 160 });
    });
    edges.forEach((e) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    return {
        nodes: nodes.map((n) => {
            const pos = g.node(n.id);
            const width = Math.min(200 + n.data.department.role_ids.length * 20, 350);
            return { ...n, position: { x: pos.x - width / 2, y: pos.y - 80 } };
        }),
        edges,
    };
}

interface DepartmentLevelProps {
    state: StateResponse | null;
    onZoomOut: () => void;
    onZoomToRoles: () => void;
    onZoomToDept: (deptId: string) => void;
}

export default function DepartmentLevel({ state, onZoomOut, onZoomToRoles, onZoomToDept }: DepartmentLevelProps) {
    const projection = state?.projection;

    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        if (!projection || projection.departments.length === 0) return { nodes: [], edges: [] };
        const deptIds = projection.departments.map((d) => d.id);

        const rawNodes: Node<DepartmentNodeData>[] = projection.departments.map((dept) => ({
            id: dept.id, type: "departmentNode",
            position: { x: 0, y: 0 }, draggable: true,
            data: {
                department: dept,
                color: getDeptColor(dept.id, deptIds),
                boundaryHeat: projection.boundary_heat[dept.id] || 0,
                onZoomToRoles,
                onFocusDept: () => onZoomToDept(dept.id),
            },
        }));

        const rawEdges: Edge[] = projection.inter_department_edges.map((edge, i) => ({
            id: `e-${edge[0]}-${edge[1]}-${i}`,
            source: edge[0], target: edge[1],
            style: { stroke: "#94a3b8", strokeWidth: 2 },
            animated: true,
        }));

        return layoutGraph(rawNodes, rawEdges);
    }, [projection, onZoomToRoles, onZoomToDept]);

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    React.useEffect(() => { setNodes(initialNodes); setEdges(initialEdges); }, [initialNodes, initialEdges, setNodes, setEdges]);

    if (!projection || projection.departments.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-text">No departments formed yet.</div>
                <button className="btn btn-secondary mt-4" onClick={onZoomOut}>Back</button>
            </div>
        );
    }

    return (
        <div style={{ width: "100%", height: "100%", position: "relative" }}>
            <div className="graph-toolbar">
                <button className="btn btn-sm btn-secondary" onClick={onZoomOut}>Overview</button>
            </div>
            <ReactFlow
                nodes={nodes} edges={edges}
                onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes} nodesDraggable={true}
                proOptions={{ hideAttribution: true }}
                fitView minZoom={0.3} maxZoom={2}
            >
                <Background color="#e5e7eb" gap={24} size={1} />
            </ReactFlow>
        </div>
    );
}
