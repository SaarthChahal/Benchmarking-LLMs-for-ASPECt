from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from metrics import comprehensive_row_metrics


ROOT = Path(__file__).resolve().parents[2]
CATALOG_CANDIDATES = [
    ROOT / "Latest" / "source_prm_dataset" / "catalog.csv",
    ROOT / "Latest" / "source_prm_dataset" / "catalog_full.csv",
    ROOT / "F1" / "source_prm_dataset" / "catalog.csv",
    ROOT / "F1" / "source_prm_dataset" / "catalog_full.csv",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_summary(summary_json: Path) -> list[dict[str, Any]]:
    rows = json.loads(read_text(summary_json))
    if not isinstance(rows, list):
        raise ValueError(f"Expected list payload in {summary_json}")
    return [row for row in rows if isinstance(row, dict)]


def load_catalog_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k).lstrip("\ufeff"): str(v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


def source_variants(path: Path) -> set[str]:
    variants = {path.name.lower(), path.stem.lower(), str(path).lower()}
    try:
        variants.add(str(path.resolve()).lower())
    except OSError:
        pass
    return {value for value in variants if value}


def build_source_index() -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for catalog_path in CATALOG_CANDIDATES:
        for row in load_catalog_rows(catalog_path):
            for key in ("file_path", "original_source"):
                value = row.get(key, "")
                if not value:
                    continue
                for variant in source_variants(Path(value)):
                    index.setdefault(variant, row)
    return index


def find_metadata(source_path: Path, source_index: dict[str, dict[str, str]]) -> dict[str, str]:
    for variant in source_variants(source_path):
        if variant in source_index:
            return source_index[variant]
    return {}


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"rows": 0}

    numeric_keys = [
        "parse_valid",
        "attempts_used",
        "param_omission",
        "hallucination",
        "category_alignment_loss",
        "structural_retention",
        "physics_retention",
        "pps_delta",
    ]
    aggregates: dict[str, Any] = {"rows": len(rows)}
    for key in numeric_keys:
        values = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
        if values:
            aggregates[f"avg_{key}"] = round(sum(values) / len(values), 4)
    return aggregates


def evaluate_run(run_dir: Path) -> list[dict[str, Any]]:
    summary_rows = load_summary(run_dir / "summary.json")
    source_index = build_source_index()
    output_rows: list[dict[str, Any]] = []
    total = len(summary_rows)

    for index, row in enumerate(summary_rows, start=1):
        source_file = Path(str(row["source_file"]))
        reverse_prompt_file = Path(str(row["reverse_prompt_file"]))
        regenerated_file = Path(str(row["regenerated_prm_file"]))
        model = str(row.get("model", ""))
        metadata = find_metadata(source_file, source_index)

        metrics = comprehensive_row_metrics(
            category=metadata.get("category", ""),
            source_hint=metadata.get("source_hint", ""),
            baseline_prm=source_file,
            reverse_prompt_text=read_text(reverse_prompt_file),
            regenerated_prm=regenerated_file,
        )

        output_rows.append(
            {
                "prompt_id": metadata.get("prompt_id", source_file.stem),
                "category": metadata.get("category", ""),
                "source_hint": metadata.get("source_hint", ""),
                "model": model,
                "baseline_file": str(source_file),
                "regenerated_file": str(regenerated_file),
                "parse_valid": bool(row.get("parse_valid", False)),
                "attempts_used": int(row.get("attempts_used", 0) or 0),
                **metrics,
            }
        )

        if index == 1 or index % 10 == 0 or index == total:
            print(
                f"Comprehensive metrics progress: {index}/{total} "
                f"({source_file.name}, model={model})",
                flush=True,
            )

    return output_rows


def write_outputs(run_dir: Path, rows: list[dict[str, Any]]) -> None:
    json_path = run_dir / "comprehensive_summary.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    csv_path = run_dir / "comprehensive_summary.csv"
    if rows:
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
    else:
        csv_path.write_text("", encoding="utf-8")

    aggregate_path = run_dir / "comprehensive_aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate_rows(rows), indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a Latest/Pipe.py run with comprehensive metrics.")
    parser.add_argument("--run-dir", required=True, help="Path to a Latest run directory.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    rows = evaluate_run(run_dir)
    write_outputs(run_dir, rows)
    print(f"Wrote comprehensive metrics to {run_dir}")


if __name__ == "__main__":
    main()
