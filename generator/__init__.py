"""
Deterministic Organization Generator.

Produces valid, replayable event streams compatible with OrgEngine v1.1.
"""

from .compiler import compile_template, GeneratorInvariantError
from .deterministic_rng import DeterministicRNG
from .exporter import export_event_stream
from .template_spec import TemplateSpec
from .verification import verify_generated_template

__all__ = [
    "compile_template",
    "GeneratorInvariantError",
    "DeterministicRNG",
    "export_event_stream",
    "TemplateSpec",
    "verify_generated_template",
]
