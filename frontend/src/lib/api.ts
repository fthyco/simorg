// API client — all requests go through here

import type { StateResponse, AppendEventRequest } from "@/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function request<T>(
    path: string,
    options?: RequestInit
): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error: ${res.status}`);
    }

    return res.json();
}

// ------------------------------------------------------------------
// Control Center (Registry) Endpoints
// ------------------------------------------------------------------

export interface ProjectMetadata {
    project_id: string;
    stage: string;
    industry: string;
    event_count: number;
    structural_debt: number;
    structural_density: number;
    state_hash: string;
    last_updated: string | null;
}

export async function listProjects(ids?: string[]): Promise<ProjectMetadata[]> {
    if (ids && ids.length === 0) return [];

    let path = "/projects";
    if (ids && ids.length > 0) {
        path += `?project_ids=${encodeURIComponent(ids.join(","))}`;
    }
    return request<ProjectMetadata[]>(path);
}

export async function deleteProject(projectId: string): Promise<{ status: string }> {
    return request<{ status: string }>(`/projects/${projectId}`, {
        method: "DELETE",
    });
}

export async function renameProject(projectId: string, newName: string): Promise<{ status: string; new_project_id: string }> {
    return request<{ status: string; new_project_id: string }>(`/projects/${projectId}/rename`, {
        method: "PATCH",
        body: JSON.stringify({ new_name: newName }),
    });
}

export async function duplicateProject(projectId: string, newProjectId: string): Promise<StateResponse> {
    return request<StateResponse>(`/projects/${projectId}/duplicate`, {
        method: "POST",
        body: JSON.stringify({ new_project_id: newProjectId }),
    });
}

// ------------------------------------------------------------------
// Session-Scoped Endpoints
// ------------------------------------------------------------------

export async function getState(projectId: string): Promise<StateResponse> {
    return request<StateResponse>(`/projects/${projectId}/state`);
}

export async function verifyDeterminism(projectId: string): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>(`/projects/${projectId}/verify-determinism`);
}

export async function appendEvent(
    projectId: string,
    req: AppendEventRequest
): Promise<StateResponse> {
    return request<StateResponse>(`/projects/${projectId}/append-event`, {
        method: "POST",
        body: JSON.stringify(req),
    });
}

export async function importEvents(
    projectId: string,
    events: Record<string, unknown>[]
): Promise<StateResponse> {
    return request<StateResponse>(`/projects/${projectId}/import`, {
        method: "POST",
        body: JSON.stringify({ events }),
    });
}

export interface GeneratorRequest {
    stage: string;
    industry: string;
    success_level: number;
    overrides?: Record<string, number | boolean>;
}

export async function generateOrg(
    projectId: string,
    req: GeneratorRequest
): Promise<StateResponse> {
    return request<StateResponse>(`/projects/${projectId}/generate-org`, {
        method: "POST",
        body: JSON.stringify(req),
    });
}
