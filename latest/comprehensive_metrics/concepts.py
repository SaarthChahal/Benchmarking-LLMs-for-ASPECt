from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import sys


ROOT = Path(__file__).resolve().parents[2]
ASPECT_EVAL_DIR = ROOT / "aspect_eval"
sys.path.insert(0, str(ASPECT_EVAL_DIR))

from prm_parser import flatten_params, parse_prm  # type: ignore


@dataclass(frozen=True)
class ConceptRule:
    name: str
    prompt_terms: tuple[str, ...]
    prm_terms: tuple[str, ...]
    reverse_terms: tuple[str, ...]


CONCEPT_RULES: tuple[ConceptRule, ...] = (
    ConceptRule("box_geometry", ("box", "cartesian"), ("model name = box", "cartesian", "rectangular", "hyper_cube", "type = rectangular"), ("box", "cartesian")),
    ConceptRule("spherical_shell_geometry", ("spherical shell", "shell", "annulus"), ("spherical shell", "chunk", "annulus"), ("spherical shell", "shell", "annulus")),
    ConceptRule("boussinesq", ("boussinesq",), ("boussinesq approximation",), ("boussinesq",)),
    ConceptRule("simple_material", ("simple material", "simple model", "isoviscous"), ("model name = simple", "simple model", "isoviscous", "model = isoviscous"), ("simple material", "simple model", "isoviscous")),
    ConceptRule("visco_plastic", ("visco-plastic", "viscoplastic"), ("material model.model name = visco plastic", "material model.visco plastic"), ("visco-plastic", "viscoplastic")),
    ConceptRule("fixed_temperature", ("fixed top-bottom temperatures", "fixed temperature", "top-bottom temperatures"), ("fixed temperature boundary indicators", "fixed_temperature", "type = fixed_temperature"), ("fixed temperature", "top-bottom temperatures")),
    ConceptRule("tangential_velocity", ("free-slip", "tangential velocity"), ("tangential velocity boundary indicators", "free_slip", "type = free_slip"), ("free-slip", "tangential velocity")),
    ConceptRule("prescribed_velocity", ("prescribed velocity", "side-driven", "kinematic"), ("prescribed velocity boundary indicators",), ("prescribed velocity", "side-driven", "kinematic")),
    ConceptRule("gravity", ("gravity", "buoyancy"), ("gravity model", "magnitude", "gravity:"), ("gravity", "buoyancy")),
    ConceptRule("initial_temperature", ("initial temperature", "perturbation", "sinusoidal"), ("initial temperature model", "function expression", "initial_conditions", "initial conditions", "sinusoidal"), ("initial temperature", "perturbation", "sinusoidal")),
    ConceptRule("composition", ("composition", "compositional"), ("compositional fields", "initial composition model", "composition"), ("composition", "compositional")),
    ConceptRule("particles", ("particles", "tracers"), ("particles",), ("particles", "tracers")),
    ConceptRule("melt", ("melt", "porosity", "darcy"), ("melt settings", "porosity"), ("melt", "porosity", "darcy")),
    ConceptRule("free_surface", ("free surface", "topography"), ("mesh deformation", "free surface"), ("free surface", "topography")),
    ConceptRule("adaptive_refinement", ("adaptive mesh refinement", "adaptive refinement"), ("initial adaptive refinement", "time steps between mesh refinement", "adaptive_refinement"), ("adaptive mesh refinement", "adaptive refinement")),
    ConceptRule("visualization", ("visualization", "graphical output"), ("postprocess.visualization", "list of postprocessors = visualization", "visualization:", "output_visualization"), ("visualization", "graphical output")),
    ConceptRule("velocity_statistics", ("velocity statistics",), ("velocity statistics", "output_velocity_statistics", 'statistics_type = "velocity"'), ("velocity statistics",)),
    ConceptRule("temperature_statistics", ("temperature statistics",), ("temperature statistics",), ("temperature statistics",)),
    ConceptRule("heat_flux_statistics", ("heat flux statistics", "nusselt"), ("heat flux statistics", "nusselt"), ("heat flux statistics", "nusselt")),
    ConceptRule("years_units", ("years instead of seconds", "use years"), ("use years instead of seconds",), ("years instead of seconds", "use years")),
    ConceptRule("end_time", ("end time",), ("end time", "end_time"), ("end time",)),
    ConceptRule("end_step", ("end step",), ("termination criteria.end step", "end_step"), ("end step",)),
    ConceptRule("3d", ("3d", "three-dimensional"), ("dimension = 3", 'dimension = "3"'), ("3d", "three-dimensional")),
    ConceptRule("2d", ("2d", "two-dimensional"), ("dimension = 2", 'dimension = "2"'), ("2d", "two-dimensional")),
    ConceptRule("internal_heating", ("internally heated", "internal heating"), ("internal_heat_generation", "internally heated"), ("internally heated", "internal heating")),
    ConceptRule("no_flow", ("no flow", "no-slip", "no slip"), ("no_flow", "no slip"), ("no flow", "no-slip", "no slip")),
    ConceptRule("deformation", ("deformation", "extension", "shear"), ("visco plastic", "prescribed velocity boundary indicators"), ("deformation", "extension", "shear")),
    ConceptRule("subduction", ("subduction", "slab"), ("subduction", "slab"), ("subduction", "slab")),
    ConceptRule("ridge", ("mid-ocean ridge", "ridge"), ("ridge", "mid-ocean"), ("mid-ocean ridge", "ridge")),
    ConceptRule("transform_fault", ("transform fault",), ("transform fault",), ("transform fault",)),
    ConceptRule("inner_core", ("inner core",), ("inner core",), ("inner core",)),
    ConceptRule("annulus", ("annulus",), ("annulus",), ("annulus",)),
)


def _normalise_text(text: str) -> str:
    return " ".join(text.lower().replace("\r", " ").replace("\n", " ").split())


def _read_text(source: str | Path) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8", errors="replace")
    p = Path(source)
    if "\n" not in source and p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return source


def _flatten_prm_text(prm_path_or_text: str | Path) -> str:
    raw_text = _normalise_text(_read_text(prm_path_or_text))
    try:
        tree = parse_prm(prm_path_or_text)
        flat = flatten_params(tree)
        parts = [f"{k} = {v}".lower() for k, v in flat.items()]
        return raw_text + " " + " ".join(parts)
    except Exception:
        return raw_text


def extract_prompt_concepts(prompt_text: str) -> set[str]:
    text = _normalise_text(prompt_text)
    found: set[str] = set()
    for rule in CONCEPT_RULES:
        if any(term in text for term in rule.prompt_terms):
            found.add(rule.name)
    return found


def extract_reverse_concepts(prompt_text: str) -> set[str]:
    text = _normalise_text(prompt_text)
    found: set[str] = set()
    for rule in CONCEPT_RULES:
        if any(term in text for term in rule.reverse_terms):
            found.add(rule.name)
    return found


def extract_prm_concepts(prm_path_or_text: str | Path) -> set[str]:
    text = _flatten_prm_text(prm_path_or_text)
    found: set[str] = set()
    for rule in CONCEPT_RULES:
        if any(term in text for term in rule.prm_terms):
            found.add(rule.name)
    return found


def concept_recall(reference: set[str], candidate: set[str]) -> float:
    if not reference:
        return 1.0
    return len(reference & candidate) / len(reference)


def concept_precision(reference: set[str], candidate: set[str]) -> float:
    if not candidate:
        return 1.0 if not reference else 0.0
    return len(reference & candidate) / len(candidate)


def concept_f1(reference: set[str], candidate: set[str]) -> float:
    p = concept_precision(reference, candidate)
    r = concept_recall(reference, candidate)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def omission_set(reference: set[str], candidate: set[str]) -> list[str]:
    return sorted(reference - candidate)


def hallucination_set(reference: set[str], candidate: set[str]) -> list[str]:
    return sorted(candidate - reference)


def as_sorted_list(items: Iterable[str]) -> list[str]:
    return sorted(set(items))
