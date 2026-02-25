# file: backend/api/index.py
"""
FastAPI Backend — Vercel Serverless Function.

Stateless: every request replays from DB.
Deployed as a single Vercel Python serverless function.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

# Add paths for kernel imports
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

from supabase_event_repository import SupabaseEventRepository, reconstruct_event

# Projection import (graceful fallback)
try:
    from org_kernel.projection import DepartmentProjectionService
    _HAS_PROJECTION = True
except ImportError:
    import traceback
    traceback.print_exc()
    _HAS_PROJECTION = False

# Import template projection fallback from main
from backend.main import _build_template_projection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
PROJECT_ID = os.environ.get("PROJECT_ID", "default")

# ---------------------------------------------------------------------------
# App — mounted at /api
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OrgKernel API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
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

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _get_repo() -> SupabaseEventRepository:
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return SupabaseEventRepository(DATABASE_URL)

def _build_event(event_type: str, payload: dict, timestamp: str) -> BaseEvent:
    cls = _EVENT_CLASS_MAP.get(event_type)
    if cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event_type: {event_type!r}. Valid: {sorted(_EVENT_CLASS_MAP)}",
        )
    return cls(timestamp=timestamp, payload=payload)

def _replay_and_project(repo: SupabaseEventRepository, department_map: dict = None) -> dict:
    events = repo.load_events(PROJECT_ID)
    event_count = len(events)

    if department_map is None:
        metadata = repo.get_project_metadata(PROJECT_ID)
        if metadata and metadata.get("department_map"):
            department_map = metadata["department_map"]

    engine = OrgEngine()
    engine.initialize_state()
    transition_results = []
    
    if events:
        for event in events:
            _, tr = engine.apply_event(event)
            transition_results.append({
                "event_type": tr.event_type,
                "success": tr.success,
                "differentiation_executed": tr.differentiation_executed,
                "suppressed_differentiation": tr.suppressed_differentiation,
                "differentiation_skipped": tr.differentiation_skipped,
                "compression_executed": tr.compression_executed,
                "deactivated": tr.deactivated,
                "reason": tr.reason,
                "primary_debt": tr.primary_debt,
                "secondary_debt": tr.secondary_debt,
                "target_density": tr.target_density,
                "shock_target": tr.shock_target,
                "magnitude": tr.magnitude,
                "cumulative_debt": engine.state.structural_debt,
            })


    state = engine.state
    state_hash = canonical_hash(state)
    diagnostics = compute_diagnostics(state)

    # Projection
    projection = None
    if event_count > 0:
        if isinstance(department_map, dict) and department_map.get("departments"):
            try:
                projection = _build_template_projection(state, department_map)
            except Exception as e:
                print(f"WARN: API Template projection failed: {e}")
                projection = None

        if projection is None and _HAS_PROJECTION:
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
                "inter_department_edges": [list(e) for e in view.inter_department_edges],
                "boundary_heat": view.boundary_heat,
                "cluster_hash": view.cluster_hash,
            }
        except Exception:
            projection = None

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

    dependencies = [
        {
            "from_role_id": dep.from_role_id,
            "to_role_id": dep.to_role_id,
            "dep_type": dep.dep_type,
            "critical": dep.critical,
        }
        for dep in state.dependencies
    ]

    return {
        "event_count": event_count,
        "state_hash": state_hash,
        "diagnostics": diagnostics,
        "projection": projection,
        "roles": roles,
        "dependencies": dependencies,
        "transition_results": transition_results,
    }

# ---------------------------------------------------------------------------
# Endpoints (all under /api/)
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "ok", "message": "OrgKernel Backend is running. Access endpoints under /api/"}

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/state")
def get_state():
    repo = _get_repo()
    return _replay_and_project(repo)

@app.get("/api/verify-determinism")
def verify_determinism():
    try:
        from org_runtime.session import SimulationSession, DeterminismError
        from org_runtime.snapshot_repository import NullSnapshotRepository
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="org_runtime not available for verification"
        )
    
    repo = _get_repo()
    engine = OrgEngine()
    snapshot_repo = NullSnapshotRepository()
    session = SimulationSession(PROJECT_ID, engine, repo, snapshot_repo)
    
    try:
        session.verify_determinism()
        return {"status": "ok", "message": "Determinism verified."}
    except DeterminismError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")

@app.post("/api/append-event")
def append_event(req: AppendEventRequest):
    repo = _get_repo()

    last_seq = repo.get_last_sequence(PROJECT_ID)
    if last_seq == 0 and req.event_type != "initialize_constants":
        init_event = InitializeConstantsEvent(timestamp=req.timestamp or "auto", payload={})
        repo.append_event(PROJECT_ID, init_event)

    event = _build_event(req.event_type, req.payload, req.timestamp)

    events = repo.load_events(PROJECT_ID)
    engine = OrgEngine()
    if events:
        engine.replay(events)
    else:
        engine.initialize_state()

    event.sequence = engine.state.event_count + 1

    try:
        engine.apply_event(event)
    except InvariantViolationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    repo.append_event(PROJECT_ID, event, event_uuid=req.event_uuid)
    return _replay_and_project(repo)

@app.post("/api/import")
def import_events(req: ImportRequest):
    repo = _get_repo()

    typed_events: List[BaseEvent] = []
    for i, evt_dict in enumerate(req.events, 1):
        try:
            event = reconstruct_event(evt_dict)
            event.sequence = i
            typed_events.append(event)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid event at index {i-1}: {exc}")

    engine = OrgEngine()
    try:
        engine.replay(typed_events)
    except (InvariantViolationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Event stream validation failed: {exc}")

    repo.replace_all_events(PROJECT_ID, typed_events)
    return _replay_and_project(repo)
