from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


STATISTICS_CANDIDATES = [
    "statistics",
    "statistics.txt",
    "output/statistics",
    "output/statistics.txt",
]

VISUALIZATION_SUFFIXES = {".vtu", ".pvtu", ".visit", ".pvts", ".pvd"}
CHECKPOINT_PATTERNS = ("restart", "checkpoint")
DEPTH_AVERAGE_PATTERNS = ("depth_average", "depth-average")


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def find_aspect_executable(config: dict[str, Any] | None = None) -> str | None:
    config = config or {}
    explicit = str(config.get("aspect_executable", "")).strip()
    if explicit and Path(explicit).exists():
        return explicit
    env_value = os.environ.get("ASPECT_EXECUTABLE", "").strip()
    if env_value and Path(env_value).exists():
        return env_value
    repo_root = Path(__file__).resolve().parents[1]
    candidate_paths = [
        repo_root / "aspect_docker_runner.cmd",
        repo_root / "aspect_docker_runner.ps1",
        repo_root / "aspect.exe",
        repo_root / "aspect-release.exe",
        repo_root / "aspect-debug.exe",
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate)
    return None


def _build_aspect_command(aspect_executable: str, prm_path: Path) -> list[str]:
    executable_path = Path(aspect_executable)
    suffix = executable_path.suffix.lower()
    if suffix in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(executable_path), str(prm_path)]
    if suffix == ".ps1":
        return [
            "powershell.exe",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(executable_path),
            str(prm_path),
        ]
    return [str(executable_path), str(prm_path)]


def _extract_output_dir(prm_text: str) -> str:
    match = re.search(r"(?im)^\s*(?:set\s+)?output(?: directory|\.directory)?\s*=\s*(.+?)\s*$", prm_text)
    if match:
        raw = match.group(1).strip().strip('"').strip("'")
        if raw:
            return raw
    return "output"


def _extract_iteration_counts(text: str) -> dict[str, int | None]:
    patterns = {
        "nonlinear_iterations": [
            r"(?i)nonlinear iterations?\s*[:=]\s*(\d+)",
            r"(?i)number of nonlinear iterations\s*[:=]\s*(\d+)",
        ],
        "linear_iterations": [
            r"(?i)linear iterations?\s*[:=]\s*(\d+)",
            r"(?i)number of linear iterations\s*[:=]\s*(\d+)",
        ],
        "timesteps": [
            r"(?i)time steps?\s*[:=]\s*(\d+)",
            r"(?i)number of time steps?\s*[:=]\s*(\d+)",
        ],
    }
    out: dict[str, int | None] = {}
    for key, pats in patterns.items():
        value: int | None = None
        for pat in pats:
            matches = re.findall(pat, text)
            if matches:
                value = int(matches[-1])
                break
        out[key] = value
    return out


def _find_statistics_file(run_dir: Path) -> Path | None:
    for candidate in STATISTICS_CANDIDATES:
        path = run_dir / candidate
        if path.exists() and path.is_file():
            return path
    for path in run_dir.rglob("*"):
        if path.is_file() and path.name.lower().startswith("statistics"):
            return path
    return None


def _looks_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _read_statistics(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"path": None, "headers": [], "rows": [], "final_row": {}, "series": {}}

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    data_lines = [line for line in lines if not line.startswith("#")]
    if not data_lines:
        return {"path": str(path), "headers": [], "rows": [], "final_row": {}, "series": {}}

    first = data_lines[0]
    delimiter = "," if "," in first else None

    rows: list[dict[str, str]] = []
    headers: list[str] = []

    if delimiter == ",":
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader((line for line in handle if line.strip() and not line.startswith("#")))
            headers = list(reader.fieldnames or [])
            rows = [dict(row) for row in reader]
    else:
        split_lines = [re.split(r"\s+", line) for line in data_lines]
        if not split_lines:
            return {"path": str(path), "headers": [], "rows": [], "final_row": {}, "series": {}}
        maybe_header = split_lines[0]
        if any(not _looks_numeric(token) for token in maybe_header):
            headers = maybe_header
            body = split_lines[1:]
        else:
            headers = [f"col_{idx}" for idx in range(len(maybe_header))]
            body = split_lines
        for parts in body:
            if len(parts) != len(headers):
                continue
            rows.append(dict(zip(headers, parts)))

    numeric_headers = []
    for header in headers:
        sample_values = [row.get(header, "") for row in rows[:5]]
        if sample_values and all(v != "" and _looks_numeric(v) for v in sample_values):
            numeric_headers.append(header)

    series = {
        header: [float(row[header]) for row in rows if row.get(header, "") != "" and _looks_numeric(row[header])]
        for header in numeric_headers
    }
    final_row = rows[-1] if rows else {}

    return {
        "path": str(path),
        "headers": headers,
        "rows": rows,
        "final_row": final_row,
        "series": series,
    }


def _discover_outputs(run_dir: Path) -> dict[str, Any]:
    files = [path for path in run_dir.rglob("*") if path.is_file()]
    visualization_files = [str(path) for path in files if path.suffix.lower() in VISUALIZATION_SUFFIXES]
    checkpoint_files = [
        str(path) for path in files if any(token in path.name.lower() for token in CHECKPOINT_PATTERNS)
    ]
    depth_average_files = [
        str(path) for path in files if any(token in path.name.lower() for token in DEPTH_AVERAGE_PATTERNS)
    ]
    stats_file = _find_statistics_file(run_dir)
    return {
        "file_count": len(files),
        "statistics_file": str(stats_file) if stats_file else None,
        "visualization_file_count": len(visualization_files),
        "checkpoint_file_count": len(checkpoint_files),
        "depth_average_file_count": len(depth_average_files),
        "has_statistics": stats_file is not None,
        "has_visualization": bool(visualization_files),
        "has_checkpoints": bool(checkpoint_files),
        "has_depth_averages": bool(depth_average_files),
    }


def _score_output_presence(discovered: dict[str, Any]) -> float:
    checks = [
        1.0 if discovered["has_statistics"] else 0.0,
        1.0 if discovered["has_visualization"] else 0.0,
        1.0 if discovered["has_checkpoints"] else 0.0,
        1.0 if discovered["has_depth_averages"] else 0.0,
    ]
    return round(sum(checks) / len(checks), 4)


def run_aspect_case(
    aspect_executable: str,
    prm_path: Path,
    case_dir: Path,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = case_dir / "stdout.txt"
    stderr_path = case_dir / "stderr.txt"
    metadata_path = case_dir / "run_metadata.json"

    prm_text = prm_path.read_text(encoding="utf-8", errors="replace")
    output_dir_name = _extract_output_dir(prm_text)

    start = time.perf_counter()
    command = _build_aspect_command(aspect_executable, prm_path)
    try:
        completed = subprocess.run(
            command,
            cwd=str(case_dir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = None
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    end = time.perf_counter()

    stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr, encoding="utf-8", errors="replace")

    output_dir = case_dir / output_dir_name
    discovered = _discover_outputs(case_dir)
    stats = _read_statistics(_find_statistics_file(case_dir))
    iters = _extract_iteration_counts(stdout + "\n" + stderr)
    success = (return_code == 0) and not timed_out

    result = {
        "aspect_executable": aspect_executable,
        "aspect_command": command,
        "prm_file": str(prm_path),
        "case_dir": str(case_dir),
        "output_dir": str(output_dir),
        "return_code": return_code,
        "timed_out": timed_out,
        "run_success": success,
        "wall_time_seconds": round(end - start, 4),
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
        "output_presence_score": _score_output_presence(discovered),
        **iters,
        **discovered,
        "statistics": stats,
    }
    metadata_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _normalize_name(value: str) -> str:
    lowered = value.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return cleaned


CANONICAL_STAT_ALIASES: dict[str, tuple[str, ...]] = {
    "rms_velocity": ("rms_velocity", "vrms", "root_mean_square_velocity"),
    "nusselt_number": ("nusselt_number", "nu"),
    "average_temperature": ("average_temperature", "temperature_average", "t_avg"),
    "min_temperature": ("minimum_temperature", "min_temperature", "temperature_min"),
    "max_temperature": ("maximum_temperature", "max_temperature", "temperature_max"),
    "heat_flux": ("heat_flux", "heatflux"),
    "topography": ("topography", "dynamic_topography"),
    "melt_fraction": ("melt_fraction", "porosity", "melt"),
}


def _canonicalize_stats(stats: dict[str, Any]) -> dict[str, list[float]]:
    series = stats.get("series", {})
    canonical: dict[str, list[float]] = {}
    normalized_map = {_normalize_name(k): v for k, v in series.items()}
    for target, aliases in CANONICAL_STAT_ALIASES.items():
        for alias in aliases:
            if alias in normalized_map:
                canonical[target] = normalized_map[alias]
                break
    for key, value in normalized_map.items():
        if key not in canonical:
            canonical[key] = value
    return canonical


def _relative_similarity(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-12)
    return max(0.0, 1.0 - abs(a - b) / denom)


def _series_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    a_trim = a[-n:]
    b_trim = b[-n:]
    point_scores = [_relative_similarity(x, y) for x, y in zip(a_trim, b_trim)]
    return sum(point_scores) / len(point_scores)


def _field_presence_similarity(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    count_a = int(first.get("visualization_file_count", 0))
    count_b = int(second.get("visualization_file_count", 0))
    if count_a == 0 and count_b == 0:
        score = 0.0
    else:
        score = min(count_a, count_b) / max(count_a, count_b)
    return {
        "field_similarity_score": round(score, 4),
        "field_similarity_mode": "visualization_presence_proxy",
        "visualization_file_count_first": count_a,
        "visualization_file_count_second": count_b,
    }


def compare_run_results(
    category: str,
    baseline_result: dict[str, Any],
    regenerated_result: dict[str, Any],
) -> dict[str, Any]:
    baseline_success = bool(baseline_result.get("run_success"))
    regenerated_success = bool(regenerated_result.get("run_success"))
    run_success_rate = round((int(baseline_success) + int(regenerated_success)) / 2, 4)
    pair_success = 1.0 if baseline_success and regenerated_success else 0.0

    baseline_time = baseline_result.get("wall_time_seconds") or 0.0
    regenerated_time = regenerated_result.get("wall_time_seconds") or 0.0
    if baseline_time and regenerated_time:
        time_similarity = _relative_similarity(float(baseline_time), float(regenerated_time))
    else:
        time_similarity = 0.0

    ops_similarity = _relative_similarity(
        float(baseline_result.get("output_presence_score", 0.0)),
        float(regenerated_result.get("output_presence_score", 0.0)),
    )

    baseline_stats = _canonicalize_stats(baseline_result.get("statistics", {}))
    regenerated_stats = _canonicalize_stats(regenerated_result.get("statistics", {}))
    shared_stats = sorted(set(baseline_stats) & set(regenerated_stats))

    final_scores: dict[str, float] = {}
    trajectory_scores: dict[str, float] = {}
    for name in shared_stats:
        series_a = baseline_stats[name]
        series_b = regenerated_stats[name]
        if series_a and series_b:
            final_scores[name] = _relative_similarity(series_a[-1], series_b[-1])
            trajectory_scores[name] = _series_similarity(series_a, series_b)

    statistics_similarity = round(
        sum(final_scores.values()) / len(final_scores), 4
    ) if final_scores else 0.0
    trajectory_similarity = round(
        sum(trajectory_scores.values()) / len(trajectory_scores), 4
    ) if trajectory_scores else 0.0

    category_keys = {
        "Thermal Convection": ["rms_velocity", "nusselt_number", "average_temperature", "heat_flux"],
        "Free Surface And Topography": ["topography", "rms_velocity"],
        "Melt Transport": ["melt_fraction", "rms_velocity", "heat_flux"],
        "Thermo-Mechanical Deformation": ["rms_velocity"],
        "Planetary And Tectonic Geodynamics": ["rms_velocity", "topography"],
        "Composition Transport": ["average_temperature", "rms_velocity"],
        "Cookbook Inspired": ["rms_velocity", "nusselt_number"],
    }.get(category, ["rms_velocity"])

    derived = []
    for key in category_keys:
        if key in final_scores:
            derived.append(final_scores[key])
        elif key in trajectory_scores:
            derived.append(trajectory_scores[key])
    derived_similarity = round(sum(derived) / len(derived), 4) if derived else 0.0

    field_proxy = _field_presence_similarity(baseline_result, regenerated_result)

    composite = (
        0.20 * run_success_rate
        + 0.10 * pair_success
        + 0.10 * time_similarity
        + 0.10 * ops_similarity
        + 0.20 * statistics_similarity
        + 0.15 * trajectory_similarity
        + 0.10 * derived_similarity
        + 0.05 * field_proxy["field_similarity_score"]
    )

    return {
        "run_success_rate": run_success_rate,
        "pair_run_success": pair_success,
        "baseline_run_success": baseline_success,
        "regenerated_run_success": regenerated_success,
        "time_similarity": round(time_similarity, 4),
        "output_presence_similarity": round(ops_similarity, 4),
        "statistics_similarity": statistics_similarity,
        "trajectory_similarity": trajectory_similarity,
        "derived_diagnostic_similarity": derived_similarity,
        "shared_statistics": shared_stats,
        "final_statistic_scores": {k: round(v, 4) for k, v in final_scores.items()},
        "trajectory_statistic_scores": {k: round(v, 4) for k, v in trajectory_scores.items()},
        **field_proxy,
        "simulation_behavior_score": round(composite, 4),
    }


def execute_pairwise_run_metrics(
    category: str,
    aspect_executable: str,
    run_dir: Path,
    prompt_id: str,
    reverse_model: str,
    regeneration_model: str,
    baseline_file: Path,
    regenerated_file: Path,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    sim_root = run_dir / "simulation_runs"
    pair_slug = "__".join(
        [
            _safe_slug(prompt_id),
            "rev",
            _safe_slug(reverse_model),
            "regen",
            _safe_slug(regeneration_model),
        ]
    )
    pair_dir = sim_root / pair_slug
    baseline_case_dir = pair_dir / "baseline_run"
    regenerated_case_dir = pair_dir / "regenerated_run"

    baseline_result = run_aspect_case(aspect_executable, baseline_file, baseline_case_dir, timeout_seconds=timeout_seconds)
    regenerated_result = run_aspect_case(aspect_executable, regenerated_file, regenerated_case_dir, timeout_seconds=timeout_seconds)
    comparison = compare_run_results(category, baseline_result, regenerated_result)
    comparison["baseline_run"] = baseline_result
    comparison["regenerated_run"] = regenerated_result
    (pair_dir / "simulation_metrics.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return comparison
