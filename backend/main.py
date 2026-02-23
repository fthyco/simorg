# file: backend/main.py
"""
FastAPI Backend — Organizational Kernel API v1.

Stateless: every request replays from DB.
No in-memory state between requests.

Endpoints:
  POST /append-event   — save + replay + return projection
  GET  /state          — replay + return projection
  POST /import         — replace events + replay + return projection
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path for kernel imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.engine import OrgEngine
from org_kernel.events import (
    AddDependencyEvent,
    AddRoleEvent,
    ApplyConstraintChangeEvent,
    BaseEvent,
    CompressRolesEvent,
    DifferentiateRoleEvent,
    InitializeConstantsEvent,
    InjectShockEvent,
    RemoveRoleEvent,
)
from org_kernel.hashing import canonical_hash
from org_kernel.diagnostics import compute_diagnostics
from org_kernel.invariants import InvariantViolationError

from backend.supabase_event_repository import SupabaseEventRepository, reconstruct_event

from generator.compiler import compile_template, compile_from_template
from generator.template_spec import TemplateSpec
from generator.industry_templates import get_template

# ---------------------------------------------------------------------------
# Projection import (graceful fallback if not all deps available)
# ---------------------------------------------------------------------------
try:
    from org_kernel.projection import DepartmentProjectionService
    _HAS_PROJECTION = True
except ImportError:
    _HAS_PROJECTION = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OrgKernel API",
    version="1.0.0",
    description="Deterministic Organizational Kernel — Event-Sourced API",
)
print("=== LOADED MAIN.PY ===")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "https://orgkernel.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

_EVENT_CLASS_MAP = {
    "initialize_constants": InitializeConstantsEvent,
    "add_role": AddRoleEvent,
    "remove_role": RemoveRoleEvent,
    "differentiate_role": DifferentiateRoleEvent,
    "compress_roles": CompressRolesEvent,
    "apply_constraint_change": ApplyConstraintChangeEvent,
    "inject_shock": InjectShockEvent,
    "add_dependency": AddDependencyEvent,
}

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AppendEventRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any] = {}
    timestamp: str = ""
    event_uuid: str = ""


class ImportRequest(BaseModel):
    events: List[Dict[str, Any]]

class GeneratorRequest(BaseModel):
    stage: str
    industry: str
    success_level: int
    overrides: Optional[Dict[str, Any]] = None

class DuplicateRequest(BaseModel):
    new_project_id: str


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _get_repo() -> SupabaseEventRepository:
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL not configured",
        )
    return SupabaseEventRepository(DATABASE_URL)


def _build_event(event_type: str, payload: dict, timestamp: str) -> BaseEvent:
    """Build a typed event from request data. Server assigns sequence."""
    cls = _EVENT_CLASS_MAP.get(event_type)
    if cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event_type: {event_type!r}. "
                   f"Valid types: {sorted(_EVENT_CLASS_MAP)}",
        )
    return cls(timestamp=timestamp, payload=payload)


def _replay_and_project(repo: SupabaseEventRepository, project_id: str, stage: str = "", industry: str = "", department_map: dict = None) -> dict:
    """
    Full replay + projection.
    This is the core stateless operation — called by every endpoint.

    If department_map is provided (from template generation), it builds
    the projection from that map instead of using graph-based clustering.
    """
    events = repo.load_events(project_id)
    event_count = len(events)

    # Fetch department map from metadata if not explicitly provided
    if department_map is None:
        metadata = repo.get_project_metadata(project_id)
        if metadata and metadata.get("department_map"):
            department_map = metadata["department_map"]

    # Replay
    engine = OrgEngine()
    if events:
        engine.replay(events)
    else:
        engine.initialize_state()

    state = engine.state
    state_dict = state.to_dict()
    state_hash = canonical_hash(state)

    # Diagnostics
    diagnostics = compute_diagnostics(state)

    # Projection
    projection = None
    if event_count > 0:
        if department_map and department_map.get("departments"):
            # ── Template-driven projection: use exact department structure ──
            try:
                projection = _build_template_projection(state, department_map)
            except Exception as e:
                print(f"WARN: Template projection failed, falling back to clustering: {e}")
                projection = None

        if projection is None and _HAS_PROJECTION:
            # ── Fallback: graph-based clustering ──
            try:
                svc = DepartmentProjectionService()
                view = svc.build(state)
                projection = {
                    "departments": [
                        {
                            "id": d.id,
                            "semantic_label": d.semantic_label,
                            "role_ids": d.role_ids,
                            "internal_density": d.internal_density,
                            "external_dependencies": d.external_dependencies,
                            "scale_stage": d.scale_stage,
                        }
                        for d in view.departments
                    ],
                    "role_to_department": view.role_to_department,
                    "inter_department_edges": [
                        list(e) for e in view.inter_department_edges
                    ],
                    "boundary_heat": view.boundary_heat,
                    "cluster_hash": view.cluster_hash,
                }
            except Exception:
                projection = None

    # Build roles dict for frontend
    roles = {}
    for role in state.roles.values():
        roles[role.id] = {
            "id": role.id,
            "name": role.name,
            "purpose": role.purpose,
            "responsibilities": list(role.responsibilities),
            "required_inputs": list(role.required_inputs),
            "produced_outputs": list(role.produced_outputs),
            "active": role.active,
            "scale_stage": role.scale_stage,
        }
    # Build dependencies list
    dependencies = [
        {
            "from_role_id": dep.from_role_id,
            "to_role_id": dep.to_role_id,
            "dependency_type": dep.dependency_type,
            "critical": dep.critical,
        }
        for dep in state.dependencies
    ]

    try:
        if event_count > 0:
            debt = diagnostics.get("structural_debt", 0)
            density = diagnostics.get("structural_density", 0)
            repo.upsert_project_metadata(
                project_id,
                stage=stage,
                industry=industry,
                event_count=event_count,
                structural_debt=debt,
                structural_density=density,
                state_hash=state_hash,
                department_map=department_map
            )
    except Exception as e:
        print(f"WARN: Failed to upsert metadata: {e}")

    return {
        "event_count": event_count,
        "state_hash": state_hash,
        "diagnostics": diagnostics,
        "projection": projection,
        "roles": roles,
        "dependencies": dependencies,
    }


def _build_template_projection(state, department_map: dict) -> dict:
    """
    Build projection directly from template department mapping.
    This ensures departments match the template's intended structure exactly.
    """
    from org_kernel.domain_types import SCALE, checked_mul

    departments = []
    role_to_department = {}
    active_roles = {rid for rid, r in state.roles.items() if r.active}

    # Build directed edge set for density calculation
    edge_set = {
        (dep.from_role_id, dep.to_role_id)
        for dep in state.dependencies
        if dep.from_role_id in active_roles and dep.to_role_id in active_roles
    }

    mapped_role_ids = set()

    for idx, dept_info in enumerate(department_map["departments"]):
        dept_id = f"dept_{idx}"
        dept_name = dept_info["name"]
        dept_role_ids = [rid for rid in dept_info["role_ids"] if rid in active_roles]

        if not dept_role_ids:
            continue

        mapped_role_ids.update(dept_role_ids)

        # Calculate internal density for this department
        n = len(dept_role_ids)
        members = set(dept_role_ids)
        if n < 2:
            internal_density = 0
        else:
            internal_edges = sum(1 for (a, b) in edge_set if a in members and b in members)
            max_possible = n * (n - 1)
            internal_density = checked_mul(internal_edges, SCALE) // max_possible if max_possible > 0 else 0

        # Count external dependencies
        external_deps = sum(
            1 for (a, b) in edge_set
            if (a in members) != (b in members)
        )

        # Get scale stage from first role
        first_role = state.roles.get(dept_role_ids[0])
        scale_stage = first_role.scale_stage if first_role else "seed"

        departments.append({
            "id": dept_id,
            "semantic_label": dept_name,
            "role_ids": dept_role_ids,
            "internal_density": internal_density,
            "external_dependencies": external_deps,
            "scale_stage": scale_stage,
        })

        for rid in dept_role_ids:
            role_to_department[rid] = dept_id

    # Handle any active roles that weren't in the template map (e.g., added manually later)
    unassigned_role_ids = [rid for rid in active_roles if rid not in mapped_role_ids]
    if unassigned_role_ids:
        # Calculate internal density for unassigned department
        n = len(unassigned_role_ids)
        members = set(unassigned_role_ids)
        if n < 2:
            internal_density = 0
        else:
            internal_edges = sum(1 for (a, b) in edge_set if a in members and b in members)
            max_possible = n * (n - 1)
            internal_density = checked_mul(internal_edges, SCALE) // max_possible if max_possible > 0 else 0
            
        external_deps = sum(
            1 for (a, b) in edge_set
            if (a in members) != (b in members)
        )
        
        dept_id = f"dept_{len(departments)}"
        departments.append({
            "id": dept_id,
            "semantic_label": "Unassigned",
            "role_ids": unassigned_role_ids,
            "internal_density": internal_density,
            "external_dependencies": external_deps,
            "scale_stage": "seed"
        })
        for rid in unassigned_role_ids:
            role_to_department[rid] = dept_id

    # Compute inter-department edges
    inter_dept_edges = set()
    for (a, b) in edge_set:
        dept_a = role_to_department.get(a)
        dept_b = role_to_department.get(b)
        if dept_a and dept_b and dept_a != dept_b:
            pair = tuple(sorted([dept_a, dept_b]))
            inter_dept_edges.add(pair)

    # Compute boundary heat
    boundary_heat = {}
    for dept in departments:
        dept_id = dept["id"]
        members = set(dept["role_ids"])
        crossing = sum(
            1 for (a, b) in edge_set
            if (a in members) != (b in members)
        )
        boundary_heat[dept_id] = crossing

    return {
        "departments": departments,
        "role_to_department": role_to_department,
        "inter_department_edges": [list(e) for e in sorted(inter_dept_edges)],
        "boundary_heat": boundary_heat,
        "cluster_hash": "",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

from fastapi import Query

@app.get("/projects")
def list_projects(project_ids: str = Query(None, description="Comma-separated list of project IDs to filter by")):
    """Returns metadata for projects, optionally filtered by a comma-separated list of IDs."""
    repo = _get_repo()
    if project_ids:
        # Split by comma and strip whitespace
        id_list = [pid.strip() for pid in project_ids.split(",") if pid.strip()]
        return repo.list_projects(project_ids=id_list)
    return repo.list_projects()

@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    """Deletes a project."""
    repo = _get_repo()
    repo.delete_project(project_id)
    return {"status": "deleted"}

class RenameRequest(BaseModel):
    new_name: str

@app.patch("/projects/{project_id}/rename")
def rename_project(project_id: str, req: RenameRequest):
    """Renames a project by changing its project_id."""
    repo = _get_repo()
    repo.rename_project(project_id, req.new_name)
    return {"status": "renamed", "new_project_id": req.new_name}

@app.post("/projects/{project_id}/duplicate")
def duplicate_project(project_id: str, req: DuplicateRequest):
    """Duplicates a project's event stream into a new project and replays it."""
    repo = _get_repo()
    events = repo.load_events(project_id)
    if not events:
        raise HTTPException(status_code=404, detail="Source project not found or empty")
    
    existing = repo.load_events(req.new_project_id)
    if existing:
        raise HTTPException(status_code=400, detail="Target project already exists")
        
    repo.replace_all_events(req.new_project_id, events)
    return _replay_and_project(repo, req.new_project_id)


@app.get("/projects/{project_id}/state")
def get_state(project_id: str):
    """
    Load all events → replay → return projection + diagnostics.
    """
    repo = _get_repo()
    return _replay_and_project(repo, project_id)


@app.post("/projects/{project_id}/append-event")
def append_event(project_id: str, req: AppendEventRequest):
    """
    Save event → replay all → return projection + diagnostics.

    Server assigns sequence. Client sends only event_type + payload.
    InitializeConstants is auto-inserted if this is the first event.
    """
    repo = _get_repo()

    # Auto-insert InitializeConstants if this is the first event
    last_seq = repo.get_last_sequence(project_id)
    if last_seq == 0 and req.event_type != "initialize_constants":
        init_event = InitializeConstantsEvent(
            timestamp=req.timestamp or "auto",
            payload={},
        )
        repo.append_event(project_id, init_event)

    # Build and validate event
    event = _build_event(req.event_type, req.payload, req.timestamp)

    # Apply-before-persist: replay + apply in memory first
    events = repo.load_events(project_id)
    engine = OrgEngine()
    if events:
        engine.replay(events)
    else:
        engine.initialize_state()

    # Assign next sequence
    event.sequence = len(engine.state.event_history) + 1

    try:
        engine.apply_event(event)
    except InvariantViolationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Persist only after successful apply
    repo.append_event(project_id, event, event_uuid=req.event_uuid)

    return _replay_and_project(repo, project_id)


@app.post("/projects/{project_id}/import")
def import_events(project_id: str, req: ImportRequest):
    """
    Replace entire event stream → replay → return projection.
    """
    repo = _get_repo()

    # Reconstruct typed events
    typed_events: List[BaseEvent] = []
    for i, evt_dict in enumerate(req.events, 1):
        try:
            event = reconstruct_event(evt_dict)
            event.sequence = i
            typed_events.append(event)
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event at index {i-1}: {exc}",
            )

    # Validate by replaying in memory
    engine = OrgEngine()
    try:
        engine.replay(typed_events)
    except (InvariantViolationError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Event stream validation failed: {exc}",
        )

    # Persist only after successful replay
    repo.replace_all_events(project_id, typed_events)

    return _replay_and_project(repo, project_id)


@app.post("/projects/{project_id}/generate-org")
def generate_org(project_id: str, req: GeneratorRequest):
    """
    Generate deterministic organization structure from parameters.
    Replaces current event stream completely.

    The generator now models realistic organizational imperfections:
    - Density is kept deliberately low (real orgs are loosely coupled)
    - Fragility (hub-and-spoke bottlenecks) emerges naturally
    - Shocks test organizational resilience
    - Differentiation pressure creates role complexity
    - Seeds vary with timestamp so each generation is unique
    """
    import time

    repo = _get_repo()

    # Success level is a 1–100 "health proxy":
    #   Low  (1-33):  stressed org — low capacity, high fragility, shocks
    #   Mid  (34-66): typical org — moderate everything
    #   High (67-100): well-resourced — more roles, higher density, less fragility
    success = max(1, min(100, req.success_level))
    ratio = success / 100.0  # 0.01 .. 1.0

    # ── Role counts (stage-driven, success adds headcount) ──
    if req.stage == "seed":
        role_count = int(3 + ratio * 4)        # 3–7
        domain_count = max(1, role_count // 3)  # 1–2
    elif req.stage == "growth":
        role_count = int(8 + ratio * 7)         # 8–15
        domain_count = max(2, role_count // 4)   # 2–4
    elif req.stage == "structured":
        role_count = int(15 + ratio * 10)        # 15–25
        domain_count = max(3, role_count // 5)   # 3–5
    elif req.stage == "mature":
        role_count = int(25 + ratio * 15)        # 25–40
        domain_count = max(4, role_count // 6)   # 4–7
    else:
        role_count = int(5 + ratio * 5)
        domain_count = 2

    # ── Density targets: realistic orgs are NOT fully connected ──
    # Real engineering teams have ~20-40% internal connectivity.
    # Cross-team connectivity is even sparser: ~5-15%.
    if req.industry == "tech_saas":
        # Hub-and-spoke: moderate internal, moderate cross-team
        intra_density = int(2000 + ratio * 1500)   # 20–35%
        inter_density = int(500 + ratio * 1000)     # 5–15%
    elif req.industry == "manufacturing":
        # Linear/rigid: higher internal (assembly lines), very low cross
        intra_density = int(3000 + ratio * 1500)   # 30–45%
        inter_density = int(300 + ratio * 400)      # 3–7%
    elif req.industry == "marketplace":
        # Multi-cluster: moderate internal, moderate cross (supply↔demand)
        intra_density = int(2500 + ratio * 1000)   # 25–35%
        inter_density = int(800 + ratio * 1200)     # 8–20%
        if domain_count < 2:
            domain_count = 2
    else:
        intra_density = int(2500 + ratio * 1500)
        inter_density = int(500 + ratio * 1000)

    # ── Capacity profile ──
    if ratio < 0.33:
        capacity_profile = "low"
    elif ratio > 0.66:
        capacity_profile = "high"
    else:
        capacity_profile = "balanced"

    # ── Fragility: stressed orgs develop bottleneck hubs ──
    # Low success → high fragility (hub-and-spoke concentration of risk)
    fragility_mode = ratio < 0.5 or req.industry == "manufacturing"

    # ── Shock: stressed orgs experience disruption ──
    # Low success → higher shock magnitude
    if ratio < 0.3:
        shock_magnitude = 3
    elif ratio < 0.6:
        shock_magnitude = 1
    else:
        shock_magnitude = 0

    # ── Differentiation pressure: mature orgs get role bloat ──
    if req.stage in ("structured", "mature"):
        diff_pressure = max(0, int(3 - ratio * 2))  # 1–3 for low success, 0 for high
    else:
        diff_pressure = 1 if ratio < 0.4 else 0

    # ── Fetch the domain-realistic template ──
    industry_template = get_template(req.industry, req.stage)

    # Apply raw overrides if Advanced Mode is used
    overrides = req.overrides or {}

    # role_count and domain_count come from the template itself now
    template_role_count = sum(len(d.roles) for d in industry_template.departments)
    template_domain_count = len(industry_template.departments)

    spec = TemplateSpec(
        role_count=int(overrides.get("role_count", template_role_count)),
        domain_count=int(overrides.get("domain_count", template_domain_count)),
        intra_density_target=int(overrides.get("intra_density_target", intra_density)),
        inter_density_target=int(overrides.get("inter_density_target", inter_density)),
        capacity_profile=overrides.get("capacity_profile", capacity_profile),
        fragility_mode=bool(overrides.get("fragility_mode", fragility_mode)),
        drift_mode=bool(overrides.get("drift_mode", False)),
        shock_magnitude=int(overrides.get("shock_magnitude", shock_magnitude)),
        differentiation_pressure=int(overrides.get("differentiation_pressure", diff_pressure)),
    )

    # ── Seed: use timestamp so each generation is unique ──
    seed = int(time.time() * 1000) % (2**31)

    try:
        events, department_map = compile_from_template(industry_template, spec, seed=seed)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"ERROR generate_org: stage={req.stage} industry={req.industry} "
              f"success={req.success_level} seed={seed} → {exc}")
        raise HTTPException(status_code=400, detail=f"Generation failed: {str(exc)}")

    # Replace stream and trigger full replay logic
    repo.replace_all_events(project_id, events)
    return _replay_and_project(repo, project_id, stage=req.stage, industry=req.industry, department_map=department_map)


import pg8000.native

@app.get("/test-db")
def test_db():
    url = DATABASE_URL.split("://", 1)[1]
    at_idx = url.rfind("@")
    credentials = url[:at_idx]
    host_part = url[at_idx + 1:]
    colon_idx = credentials.find(":")
    user = credentials[:colon_idx]
    password = credentials[colon_idx + 1:]
    host_port, database = host_part.split("/", 1)
    host, port_str = host_port.rsplit(":", 1)
    conn = pg8000.native.Connection(
        user=user,
        password=password,
        host=host,
        port=int(port_str),
        database=database or "postgres",
        ssl_context=True,
    )
    rows = conn.run("select count(*) from events;")
    count = rows[0][0]
    conn.close()
    return {"events_count": count}

@app.get("/debug-env")
def debug_env():
    """Temporary debug endpoint — tries DB connection and reports details."""
    import traceback
    db = DATABASE_URL
    if not db:
        return {"error": "DATABASE_URL is empty"}

    # Parse URL the same way _get_conn does
    url = db.split("://", 1)[1]
    at_idx = url.rfind("@")
    credentials = url[:at_idx]
    host_part = url[at_idx + 1:]
    colon_idx = credentials.find(":")
    user = credentials[:colon_idx]
    password = credentials[colon_idx + 1:]
    host_port, database = host_part.split("/", 1)
    host, port_str = host_port.rsplit(":", 1)

    result = {
        "parsed_user": user,
        "parsed_password_length": len(password),
        "parsed_password_first3": password[:3] + "***",
        "parsed_host": host,
        "parsed_port": port_str,
        "parsed_database": database,
        "url_length": len(db),
    }

    try:
        conn = pg8000.native.Connection(
            user=user,
            password=password,
            host=host,
            port=int(port_str),
            database=database or "postgres",
            ssl_context=True,
        )
        rows = conn.run("SELECT 1")
        conn.close()
        result["connection"] = "SUCCESS"
        result["select_1"] = str(rows)
    except Exception as e:
        result["connection"] = "FAILED"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}



