from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[2]
ASPECT_EVAL_DIR = ROOT / "aspect_eval"
sys.path.insert(0, str(ASPECT_EVAL_DIR))

import novel  # type: ignore
from prm_parser import flatten_params, get_sections, parse_prm  # type: ignore

from concepts import (
    as_sorted_list,
    concept_f1,
    concept_precision,
    concept_recall,
    extract_prm_concepts,
    extract_reverse_concepts,
    hallucination_set,
    omission_set,
)

CATEGORY_EXPECTATIONS: dict[str, set[str]] = {
    "Thermal Convection": {"fixed_temperature", "geometry", "material_or_rheology", "temperature_initial_or_formulation"},
    "Thermo-Mechanical Deformation": {"deformation_or_velocity", "material_or_rheology", "geometry"},
    "Composition Transport": {"composition", "geometry", "temperature_initial_or_formulation"},
    "Melt Transport": {"melt", "geometry", "material_or_rheology"},
    "Free Surface And Topography": {"free_surface", "geometry", "temperature_initial_or_formulation"},
    "Planetary And Tectonic Geodynamics": {"gravity", "geometry", "tectonic_feature"},
    "Cookbook Inspired": {"geometry", "material_or_rheology"},
    "Benchmark": {"geometry"},
    "Test Case": {"geometry"},
    "Official ASPECT": {"geometry"},
}

SOURCE_HINT_EXPECTATIONS: dict[str, set[str]] = {
    "cookbook: convection-box": {"box_geometry", "fixed_temperature", "tangential_velocity"},
    "cookbook: convection_box_3d": {"3d", "box_geometry"},
    "cookbook: composition_passive": {"composition"},
    "cookbook: composition_active": {"composition"},
    "cookbook: composition-reaction": {"composition"},
    "cookbook: free_surface": {"free_surface"},
    "cookbook: prescribed_velocity": {"prescribed_velocity"},
    "cookbook: shell_simple_2d": {"spherical_shell_geometry", "2d"},
    "cookbook: shell_simple_3d": {"spherical_shell_geometry", "3d"},
    "cookbook: continental_extension": {"deformation"},
    "cookbook: kinematically_driven_subduction_2d": {"subduction", "2d"},
}


def _satisfies_expectation(expectation: str, concepts: set[str]) -> bool:
    if expectation == "geometry":
        return bool({"box_geometry", "spherical_shell_geometry", "annulus"} & concepts)
    if expectation == "material_or_rheology":
        return bool({"simple_material", "visco_plastic"} & concepts)
    if expectation == "temperature_initial_or_formulation":
        return bool({"initial_temperature", "boussinesq", "fixed_temperature"} & concepts)
    if expectation == "deformation_or_velocity":
        return bool({"deformation", "prescribed_velocity", "tangential_velocity"} & concepts)
    if expectation == "tectonic_feature":
        return bool({"subduction", "ridge", "transform_fault", "inner_core", "deformation"} & concepts)
    return expectation in concepts


def _expectation_score(expectations: set[str], concepts: set[str]) -> tuple[float, list[str], list[str]]:
    if not expectations:
        return 1.0, [], []
    present: list[str] = []
    missing: list[str] = []
    for expectation in sorted(expectations):
        if _satisfies_expectation(expectation, concepts):
            present.append(expectation)
        else:
            missing.append(expectation)
    return len(present) / len(expectations), present, missing


def category_physics_alignment_metrics(category: str, source_hint: str, prm_concepts: set[str]) -> dict[str, Any]:
    category_expectations = CATEGORY_EXPECTATIONS.get(category, set())
    source_expectations = SOURCE_HINT_EXPECTATIONS.get(source_hint, set())
    category_score, category_present, category_missing = _expectation_score(category_expectations, prm_concepts)
    source_score, source_present, source_missing = _expectation_score(source_expectations, prm_concepts)
    return {
        "category_expectation_score": round(category_score, 4),
        "category_expectations_present": category_present,
        "category_expectations_missing": category_missing,
        "source_hint_expectation_score": round(source_score, 4),
        "source_hint_expectations_present": source_present,
        "source_hint_expectations_missing": source_missing,
    }


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _safe_physics_plausibility_score(prm: Path) -> dict[str, Any]:
    try:
        result = novel.physics_plausibility_score(prm)
    except Exception as exc:
        return {"PPS": None, "error": repr(exc)}
    if not isinstance(result, dict):
        return {"PPS": None, "error": f"Unexpected novel result type: {type(result).__name__}"}
    pps = _as_float(result.get("PPS"))
    if pps is None:
        return {**result, "PPS": None, "error": f"Unexpected PPS value: {result.get('PPS')!r}"}
    return {**result, "PPS": pps}


def _safe_parse_prm(prm: Path) -> dict[str, Any]:
    try:
        tree = parse_prm(prm)
    except Exception as exc:
        return {"tree": {}, "error": repr(exc)}
    if not isinstance(tree, dict):
        return {"tree": {}, "error": f"Unexpected parse tree type: {type(tree).__name__}"}
    return {"tree": tree, "error": None}


def _parameter_signature(tree: dict[str, Any]) -> set[str]:
    flattened = flatten_params(tree)
    return {str(key) for key in flattened.keys() if str(key).strip()}


def _section_signature(tree: dict[str, Any]) -> set[str]:
    return {str(section) for section in get_sections(tree) if str(section).strip()}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def reverse_prompt_fidelity_metrics(baseline_prm: Path, reverse_prompt_text: str) -> dict[str, Any]:
    baseline = extract_prm_concepts(baseline_prm)
    reverse = extract_reverse_concepts(reverse_prompt_text)
    return {
        "baseline_concepts": as_sorted_list(baseline),
        "reverse_prompt_concepts": as_sorted_list(reverse),
        "baseline_to_reverse_recall": round(concept_recall(baseline, reverse), 4),
        "baseline_to_reverse_precision": round(concept_precision(baseline, reverse), 4),
        "baseline_to_reverse_f1": round(concept_f1(baseline, reverse), 4),
        "reverse_omissions_vs_baseline": omission_set(baseline, reverse),
        "reverse_hallucinations_vs_baseline": hallucination_set(baseline, reverse),
    }


def regenerated_prm_metrics(baseline_prm: Path, regenerated_prm: Path) -> dict[str, Any]:
    baseline_concepts = extract_prm_concepts(baseline_prm)
    regenerated_concepts = extract_prm_concepts(regenerated_prm)

    baseline_tree_payload = _safe_parse_prm(baseline_prm)
    regenerated_tree_payload = _safe_parse_prm(regenerated_prm)
    baseline_tree = baseline_tree_payload["tree"] if isinstance(baseline_tree_payload.get("tree"), dict) else {}
    regenerated_tree = regenerated_tree_payload["tree"] if isinstance(regenerated_tree_payload.get("tree"), dict) else {}

    baseline_params = _parameter_signature(baseline_tree)
    regenerated_params = _parameter_signature(regenerated_tree)
    baseline_sections = _section_signature(baseline_tree)
    regenerated_sections = _section_signature(regenerated_tree)

    baseline_novel = _safe_physics_plausibility_score(baseline_prm)
    regenerated_novel = _safe_physics_plausibility_score(regenerated_prm)
    baseline_pps = _as_float(baseline_novel.get("PPS"))
    regenerated_pps = _as_float(regenerated_novel.get("PPS"))

    if baseline_pps is None or regenerated_pps is None:
        physics_retention = 0.0
        pps_delta = None
    else:
        denom = max(abs(baseline_pps), abs(regenerated_pps), 1e-9)
        physics_retention = 1.0 if denom == 0 else min(abs(baseline_pps), abs(regenerated_pps)) / denom
        pps_delta = round(regenerated_pps - baseline_pps, 4)

    category_metrics = category_physics_alignment_metrics("", "", regenerated_concepts)

    return {
        "regenerated_concepts": as_sorted_list(regenerated_concepts),
        "param_omission": round(len(baseline_params - regenerated_params) / max(len(baseline_params), 1), 4),
        "hallucination": round(len(regenerated_params - baseline_params) / max(len(regenerated_params), 1), 4),
        "structural_retention": round(0.5 * _jaccard(baseline_sections, regenerated_sections) + 0.5 * _jaccard(baseline_params, regenerated_params), 4),
        "physics_retention": round(physics_retention, 4),
        "pps_delta": pps_delta,
        "category_alignment_loss": round(1 - category_metrics["category_expectation_score"], 4),
        "baseline_prm_parse_error": baseline_tree_payload.get("error"),
        "regenerated_prm_parse_error": regenerated_tree_payload.get("error"),
        "physics_baseline_pps": baseline_pps,
        "physics_regenerated_pps": regenerated_pps,
        "physics_baseline_error": baseline_novel.get("error"),
        "physics_regenerated_error": regenerated_novel.get("error"),
    }


def comprehensive_row_metrics(
    category: str,
    source_hint: str,
    baseline_prm: Path,
    reverse_prompt_text: str,
    regenerated_prm: Path,
) -> dict[str, Any]:
    regen_metrics = regenerated_prm_metrics(baseline_prm, regenerated_prm)
    regenerated_category = category_physics_alignment_metrics(category, source_hint, set(regen_metrics["regenerated_concepts"]))

    return {
        "param_omission": regen_metrics["param_omission"],
        "hallucination": regen_metrics["hallucination"],
        "category_alignment_loss": round(1 - regenerated_category["category_expectation_score"], 4),
        "structural_retention": regen_metrics["structural_retention"],
        "physics_retention": regen_metrics["physics_retention"],
        "pps_delta": regen_metrics["pps_delta"],
    }
