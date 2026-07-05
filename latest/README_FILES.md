# Latest File Guide

This file explains the purpose of the files and folders inside `Latest/`.

## What `Latest/` Is

`Latest/` is a self-contained ASPECT LLM generation workspace.

It contains:

- a compact retrieval bundle for ASPECT parameter-file generation
- a standalone roundtrip pipeline in `Pipe.py`
- copied comprehensive metrics from `F1`
- a local source `.prm` dataset
- run outputs produced by the pipeline

The working goal is:

- source `.prm` -> reverse prompt -> regenerated `.prm` -> ASPECT validation -> repair loop

## Top-Level Files

### `Pipe.py`

Main standalone pipeline for `Latest/`.

Current responsibilities:

- load config and API key
- load one or more source `.prm` files
- build a retrieval context bundle from the local docs
- call the reverse model prompt
- call the generation prompt
- run generated files through ASPECT in Docker via `wsl docker run`
- feed ASPECT errors into a repair prompt
- retry until parse-valid or max attempts reached
- write logs, attempts, and summaries

### `config.json`

Default config file for the pipeline.

Current default behavior:

- runs one source file
- uses two models:
  - `deepseek/deepseek-v3.2`
  - `qwen/qwen3-32b`
- enables Docker-based ASPECT validation
- enables repair retries

### `config.one_file_annulus.json`

Explicit one-file config targeting:

- `source_prm_dataset/files/2d_annulus_visualization__2d_annulus_example.prm`

Use this when you want to focus on the annulus example only.

### `key.txt`

OpenRouter API key used by `Pipe.py`.

This is read locally by the pipeline.

### `llms.txt`

Main retrieval index for the context bundle.

It points the model to:

- syntax
- structure
- tasks
- feature docs
- validation traps
- annulus-specific notes
- example indexes

### `syntax-guide.md`

Minimal ASPECT ParameterHandler syntax guide.

Focus:

- `set ... = ...`
- `subsection ...`
- `end`
- valid versus invalid config styles

### `structure-guide.md`

High-level guide to common ASPECT `.prm` organization.

Focus:

- top-level sections
- common subsection ordering
- model-selection patterns

### `README.md`

Short bundle overview.

This is the brief human-facing intro. The current file you are reading is the
full inventory.

### `run_aspect_validation.ps1`

Helper PowerShell script for validating generated `.prm` files inside the
 ASPECT Docker image using WSL.

Useful when you want to test files manually outside `Pipe.py`.

## Top-Level Folders

### `docs/`

Focused guidance files used as retrieval context.

Files:

- `parameter-file-structure.md`
  Explains how ASPECT parameter files are organized.

- `parameter-documentation-index.md`
  Retrieval routing map for major ASPECT configuration areas.

- `feature-areas.md`
  Tags common geodynamics problem families.

- `common-validation-traps.md`
  Documents repeated failure modes seen in generated `.prm` files.

- `annulus-shell-notes.md`
  Special notes for spherical shell and annulus-style examples, especially the
  annulus validation case.

### `tasks/`

Task-specific prompt guidance.

Files:

- `generation.md`
  How to map a natural-language prompt to a valid `.prm`.

- `reverse.md`
  How to summarize a source `.prm` into a reusable reverse prompt.

- `repair.md`
  How to rewrite invalid `.prm` output into valid ASPECT syntax.

### `examples/`

Index files for example retrieval.

Files:

- `cookbooks-index.md`
- `benchmarks-index.md`
- `tests-index.md`
- `roundtrip-index.md`

These are not the real examples themselves. They are lightweight routing files
for retrieval.

### `source_prm_dataset/`

Local source dataset used as generation input.

Key contents:

- `files/`
  Smaller cookbook-focused copied `.prm` set.

- `all_files/`
  Much larger collection from cookbooks, benchmarks, and tests.

- `catalog.csv`
  Smaller catalog aligned with copied example files.

- `catalog_full.csv`
  Larger catalog across the broader source pool.

- several copied top-level `.prm` examples

This folder is the baseline source pool for reverse prompting.

### `comprehensive_metrics/`

Copied metric stack from `F1`, adapted for use inside `Latest/`.

Core files:

- `concepts.py`
  Extracts concept tags from `.prm` files and reverse prompts.

- `metrics.py`
  Computes roundtrip metrics such as reverse fidelity, regenerated retention,
  structural retention, and physics retention.

- `evaluate_run.py`
  Original evaluator for `F1`-style summary layout.

- `run_metrics.py`
  Simulation-run comparison logic.

- `run_evaluate.py`
  Simulation evaluation entry point.

- `evaluate_pipe_run.py`
  `Latest`-specific evaluator for the run layout written by `Pipe.py`.

- `README.md`
  Overview of the metric stack.

### `runs/`

Output directories produced by `Pipe.py`.

Currently includes:

- `roundtrip_demo/`
  Earlier two-file generation run.

- `roundtrip_annulus_demo/`
  One-file annulus-focused run with validation and repair loop outputs.

### `__pycache__/`

Compiled Python bytecode files.

Not important for logic.

## Run Folder Layout

Each run under `runs/<run_name>/` may contain:

- `run_manifest.json`
  Records config, selected source files, models, and context files used.

- `reverse_prompts/`
  Reverse-engineered prompts for each source/model pair.

- `regenerated_prms/`
  Final current `.prm` output for each source/model pair.

- `attempt_prms/`
  Per-attempt generated or repaired `.prm` files written before validation.

- `logs/`
  Prompt logs showing which prompt stages were run.

- `validation_logs/`
  ASPECT validation results per attempt, including stdout and stderr.

- `summary.json`
  Final run summary, including:
  - source file
  - model
  - reverse prompt file
  - regenerated file
  - validation log file
  - attempts used
  - parse validity
  - last validation return code

- `comprehensive_summary.json`
- `comprehensive_summary.csv`
- `comprehensive_aggregate.json`
  Written after metric evaluation if `evaluate_pipe_run.py` is run.

## Recommended Workflow

1. Choose a config:
   - `config.json`
   - `config.one_file_annulus.json`

2. Run the pipeline:

```powershell
& 'C:\Users\mohdw\AppData\Local\Programs\Python\Python313\python.exe' Latest\Pipe.py --config Latest\config.one_file_annulus.json
```

3. Inspect run artifacts under:

```text
Latest/runs/<run_name>/
```

4. Evaluate metrics:

```powershell
& 'C:\Users\mohdw\AppData\Local\Programs\Python\Python313\python.exe' Latest\comprehensive_metrics\evaluate_pipe_run.py --run-dir C:\Users\mohdw\OneDrive\Desktop\geo\Latest\runs\roundtrip_annulus_demo
```

## What Is New Compared To `F1`

`Latest/` differs from `F1/` in a few important ways:

- the context bundle is local and explicit
- generation is retrieval-oriented rather than only prompt-template driven
- the pipeline now includes ASPECT validation inside the generation loop
- repair is driven by actual ASPECT error messages
- one-file focused debugging is easier here than in the broader `F1` pipeline

## Important Current Limitation

Even with syntax constraints, models still invent invalid ASPECT parameter names.

That is why:

- `common-validation-traps.md` was added
- `annulus-shell-notes.md` was added
- Docker-based ASPECT validation was integrated into `Pipe.py`
- repair retries are now part of the default workflow
