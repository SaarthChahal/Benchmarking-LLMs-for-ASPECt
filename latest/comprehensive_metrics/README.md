# Comprehensive Metrics

This folder contains the refactored metric stack for the source-PRM roundtrip study.

The comparison target is now:

- source `.prm` -> reverse prompt -> regenerated `.prm`

not the older prompt-first workflow.

## Why This Exists

`aspect_eval/novel.py` is useful, but it only scores the plausibility of a single `.prm`.

For this study we also need to know:

- how faithfully the reverse prompt captures the source `.prm`
- how much information is lost from source `.prm` to regenerated `.prm`
- whether category-defining physics survives the roundtrip
- whether the regenerated model behaves similarly when actually run in ASPECT

## Main Files

- `concepts.py`
  Extracts concept tags from `.prm` files and reverse prompts.

- `metrics.py`
  Computes config-level and category-aware roundtrip metrics.

- `evaluate_run.py`
  Batch evaluator for `summary.csv` that writes `comprehensive_summary.csv/json`.

- `run_metrics.py`
  Executes ASPECT on baseline and regenerated `.prm` files and compares run behavior.

- `run_evaluate.py`
  Batch evaluator for simulation metrics that writes `simulation_summary.csv/json`.

## Reduced Config-Level Metrics

The `Latest/` copy is intentionally reduced. The main output is now centered on
the smallest useful set of headline metrics, while some lists are kept only as
diagnostics.

### Reverse Prompt Fidelity

- `baseline_to_reverse_f1`
- `reverse_omissions_vs_baseline`
- `reverse_hallucinations_vs_baseline`

### Baseline To Regenerated Retention

- `baseline_to_regenerated_f1`
- `regenerated_omissions_vs_baseline`
- `regenerated_hallucinations_vs_baseline`

### Structural Retention

- `structural_retention_scs`
- `structural_error`

### Physics Retention

- `physics_retention_ratio`
- `physics_baseline_pps`
- `physics_regenerated_pps`
- `physics_regenerated_error`

### Category And Source-Hint Alignment

- `regenerated_category_expectation_score`
- `source_hint_expectation_score`
- regenerated expectation-missing lists
- `category_alignment_loss`

### Composite Config Score

- `comprehensive_roundtrip_score`

## Simulation Metric Families

The simulation metric files are still present. They have not yet been reduced in
this pass.

### Run Success

- `baseline_run_success`
- `regenerated_run_success`
- `run_success_rate`
- `pair_run_success`

### Execution Similarity

- `time_similarity`
- parsed iteration counts when available

### Output Similarity

- `output_presence_similarity`
- `statistics_similarity`
- `trajectory_similarity`
- `derived_diagnostic_similarity`
- `field_similarity_score`

### Composite Simulation Score

- `simulation_behavior_score`

## Typical Usage

The pipeline calls these automatically, but the evaluators can also be run directly after a completed run folder exists.

Config-level evaluation:

```powershell
& C:\Users\mohdw\AppData\Local\Programs\Python\Python313\python.exe F1\comprehensive_metrics\evaluate_run.py --run-dir C:\Users\mohdw\OneDrive\Desktop\geo\F1\runs\source_prm_sanity_2x2
```

Simulation evaluation:

```powershell
& C:\Users\mohdw\AppData\Local\Programs\Python\Python313\python.exe F1\comprehensive_metrics\run_evaluate.py --run-dir C:\Users\mohdw\OneDrive\Desktop\geo\F1\runs\source_prm_sanity_2x2 --aspect-executable C:\Users\mohdw\OneDrive\Desktop\geo\F1\aspect_docker_runner.cmd
```
