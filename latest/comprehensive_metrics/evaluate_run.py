from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from metrics import comprehensive_row_metrics
from run_metrics import find_aspect_executable


def load_summary(summary_csv: Path) -> list[dict[str, str]]:
    with summary_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = [normalize_summary_row(row) for row in csv.DictReader(handle)]
    rows = enrich_summary_rows(rows)
    return fill_missing_rows_from_artifacts(summary_csv.parent, rows)


def normalize_summary_row(row: dict[str, str]) -> dict[str, str]:
    extras = row.get(None)
    if not extras:
        return dict(row)
    if len(extras) == 8 and row.get("baseline_file") == "catalog":
        return {
            "prompt_id": row.get("prompt_id", ""),
            "category": row.get("reverse_model", ""),
            "source_hint": row.get("regeneration_model", ""),
            "source_type": row.get("baseline_file", ""),
            "relative_path": row.get("reverse_prompt_file", ""),
            "original_source": row.get("regenerated_file", ""),
            "reverse_model": extras[0],
            "regeneration_model": extras[1],
            "baseline_file": extras[2],
            "reverse_prompt_file": extras[3],
            "regenerated_file": extras[4],
            "baseline_pps": extras[5],
            "regenerated_pps": extras[6],
            "pps_delta": extras[7],
        }
    normalized = dict(row)
    normalized.pop(None, None)
    return normalized


def safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def _catalog_index() -> dict[str, dict[str, str]]:
    catalog_path = Path(__file__).resolve().parents[1] / "source_prm_dataset" / "catalog.csv"
    if not catalog_path.exists():
        return {}
    with catalog_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["prompt_id"]: row for row in rows if row.get("prompt_id")}


def enrich_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    catalog = _catalog_index()
    enriched: list[dict[str, str]] = []
    for row in rows:
        prompt_id = row.get("prompt_id", "")
        catalog_row = catalog.get(prompt_id, {})
        merged = dict(row)
        merged.setdefault("category", catalog_row.get("category", ""))
        merged.setdefault("source_hint", catalog_row.get("source_hint", ""))
        merged.setdefault("source_type", catalog_row.get("source_type", "catalog"))
        merged.setdefault("relative_path", catalog_row.get("relative_path", ""))
        merged.setdefault("original_source", catalog_row.get("original_source", catalog_row.get("file_path", "")))
        enriched.append(merged)
    return enriched


def _model_slug_index(run_dir: Path) -> dict[str, str]:
    manifest_path = run_dir / "run_manifest.json"
    slug_to_model: dict[str, str] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for model in manifest.get("regeneration_models", []):
            if isinstance(model, str):
                slug_to_model[safe_slug(model)] = model
    reverse_dir = run_dir / "reverse_prompts"
    if reverse_dir.exists():
        for path in reverse_dir.glob("*.txt"):
            match = re.match(r"^SRC\d+__(.+)\.txt$", path.name)
            if match:
                slug = match.group(1)
                slug_to_model.setdefault(slug, slug)
    return slug_to_model


def fill_missing_rows_from_artifacts(run_dir: Path, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    catalog = _catalog_index()
    slug_to_model = _model_slug_index(run_dir)
    existing_stems = {
        Path(regenerated_file).stem
        for row in rows
        for regenerated_file in [row.get("regenerated_file", "")]
        if regenerated_file
    }
    metrics_dir = run_dir / "metrics"
    filled_rows = list(rows)
    for regenerated_path in sorted((run_dir / "regenerated_prms").glob("*.prm")):
        stem = regenerated_path.stem
        if stem in existing_stems:
            continue
        match = re.match(r"^(SRC\d+)__rev_(.+)__regen_(.+)$", stem)
        if not match:
            continue
        prompt_id, reverse_slug, regen_slug = match.groups()
        catalog_row = catalog.get(prompt_id, {})
        metric_path = metrics_dir / f"{stem}.json"
        baseline_pps = ""
        regenerated_pps = ""
        pps_delta = ""
        if metric_path.exists():
            metric_payload = json.loads(metric_path.read_text(encoding="utf-8"))
            baseline_pps = metric_payload.get("baseline_pps", "")
            regenerated_pps = metric_payload.get("regenerated_pps", "")
            pps_delta = metric_payload.get("pps_delta", "")
        filled_rows.append(
            {
                "prompt_id": prompt_id,
                "category": catalog_row.get("category", ""),
                "source_hint": catalog_row.get("source_hint", ""),
                "source_type": catalog_row.get("source_type", "catalog"),
                "relative_path": catalog_row.get("relative_path", ""),
                "original_source": catalog_row.get("original_source", catalog_row.get("file_path", "")),
                "reverse_model": slug_to_model.get(reverse_slug, reverse_slug),
                "regeneration_model": slug_to_model.get(regen_slug, regen_slug),
                "baseline_file": str(run_dir / "baseline_inputs" / f"{prompt_id}.prm"),
                "reverse_prompt_file": str(run_dir / "reverse_prompts" / f"{prompt_id}__{reverse_slug}.txt"),
                "regenerated_file": str(regenerated_path),
                "baseline_pps": baseline_pps,
                "regenerated_pps": regenerated_pps,
                "pps_delta": pps_delta,
            }
        )
    return filled_rows


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def evaluate_run(run_dir: Path) -> list[dict[str, Any]]:
    summary_rows = load_summary(run_dir / "summary.csv")
    output_rows: list[dict[str, Any]] = []
    total = len(summary_rows)
    for index, row in enumerate(summary_rows, start=1):
        reverse_prompt_text = read_text(Path(row["reverse_prompt_file"]))
        baseline_prm = Path(row["baseline_file"])
        regenerated_prm = Path(row["regenerated_file"])
        metrics = comprehensive_row_metrics(
            category=row.get("category", ""),
            source_hint=row.get("source_hint", ""),
            baseline_prm=baseline_prm,
            reverse_prompt_text=reverse_prompt_text,
            regenerated_prm=regenerated_prm,
        )
        output_rows.append({**row, **metrics})
        if index == 1 or index % 25 == 0 or index == total:
            print(
                f"Comprehensive metrics progress: {index}/{total} "
                f"({row.get('prompt_id', '')}, rev={row.get('reverse_model', '')}, regen={row.get('regeneration_model', '')})",
                flush=True,
            )
    return output_rows


def attach_simulation_metrics(run_dir: Path, rows: list[dict[str, Any]], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = config or {}
    aspect_executable = find_aspect_executable(config)
    if not aspect_executable:
        return rows
    from run_evaluate import evaluate_simulation_run

    sim_rows = evaluate_simulation_run(run_dir, config)
    sim_index = {(row["prompt_id"], row["reverse_model"], row["regeneration_model"]): row for row in sim_rows}
    return [{**row, **sim_index.get((row["prompt_id"], row["reverse_model"], row["regeneration_model"]), {})} for row in rows]


def write_outputs(run_dir: Path, rows: list[dict[str, Any]]) -> None:
    json_path = run_dir / "comprehensive_summary.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    csv_path = run_dir / "comprehensive_summary.csv"
    if not rows:
        csv_path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an F1 run with comprehensive source-prm metrics.")
    parser.add_argument("--run-dir", required=True, help="Path to a pipeline run directory.")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    rows = evaluate_run(run_dir)
    write_outputs(run_dir, rows)
    print(f"Wrote comprehensive metrics to {run_dir}")


if __name__ == "__main__":
    main()
