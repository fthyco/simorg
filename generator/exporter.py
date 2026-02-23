"""
JSON Event Stream Exporter.

Exports a generated event stream + metadata to a JSON file.
Never exports OrgState.
"""

from __future__ import annotations

import json
from typing import List

from org_kernel.events import BaseEvent

from .template_spec import TemplateSpec


def export_event_stream(
    events: List[BaseEvent],
    path: str,
    spec: TemplateSpec,
    seed: int,
) -> None:
    """
    Write event stream + metadata to a JSON file.

    Output format:
    {
        "metadata": {"seed": int, "template": {...}},
        "events": [event.to_dict(), ...]
    }
    """
    doc = {
        "metadata": {
            "seed": seed,
            "template": spec.to_dict(),
        },
        "events": [e.to_dict() for e in events],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=True, indent=2)
