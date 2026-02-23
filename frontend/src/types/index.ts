// Types mirroring the backend API response

export interface Role {
    id: string;
    name: string;
    purpose: string;
    responsibilities: string[];
    required_inputs: string[];
    produced_outputs: string[];
    active: boolean;
    scale_stage: string;
}

export interface Dependency {
    from_role_id: string;
    to_role_id: string;
    dependency_type: string;
    critical: boolean;
}

export interface Department {
    id: string;
    semantic_label: string;
    role_ids: string[];
    internal_density: number;
    external_dependencies: number;
    scale_stage: string;
}

export interface Projection {
    departments: Department[];
    role_to_department: Record<string, string>;
    inter_department_edges: [string, string][];
    boundary_heat: Record<string, number>;
    cluster_hash: string;
}

export interface Diagnostics {
    role_count: number;
    active_role_count: number;
    structural_density: number;
    structural_debt: number;
    isolated_roles: string[];
    governance_edges: number;
    warnings: string[];
}

export interface StateResponse {
    event_count: number;
    state_hash: string;
    diagnostics: Diagnostics;
    projection: Projection | null;
    roles: Record<string, Role>;
    dependencies: Dependency[];
}

export interface AppendEventRequest {
    event_type: string;
    payload: Record<string, unknown>;
    timestamp?: string;
    event_uuid?: string;
}

// Event types with their required payload fields
export const EVENT_TYPES = {
    add_role: {
        label: "Add Role",
        fields: ["id", "name", "purpose", "responsibilities"],
    },
    remove_role: {
        label: "Remove Role",
        fields: ["role_id"],
    },
    add_dependency: {
        label: "Add Dependency",
        fields: ["from_role_id", "to_role_id"],
    },
    inject_shock: {
        label: "Inject Shock",
        fields: ["target_role_id", "magnitude"],
    },
    apply_constraint_change: {
        label: "Apply Constraint Change",
        fields: ["capital_delta", "talent_delta", "time_delta", "political_cost_delta"],
    },
    differentiate_role: {
        label: "Differentiate Role",
        fields: ["role_id"],
    },
    compress_roles: {
        label: "Compress Roles",
        fields: ["source_role_id", "target_role_id"],
    },
} as const;

export type EventType = keyof typeof EVENT_TYPES;
