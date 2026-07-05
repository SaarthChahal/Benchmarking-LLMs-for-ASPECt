# ASPECT LLM Context Bundle

This folder contains a compact retrieval-oriented context bundle for ASPECT
parameter-file generation, reverse engineering, and repair.

Purpose:

- give an LLM a stable index of the important ASPECT concepts
- point retrieval toward syntax, structure, and examples first
- support a roundtrip pipeline:
  source `.prm` -> reverse prompt -> regenerated `.prm` -> repair

Main entry points:

- `llms.txt`
- `syntax-guide.md`
- `structure-guide.md`
- `tasks/generation.md`
- `tasks/reverse.md`
- `tasks/repair.md`
- `Pipe.py`
- `comprehensive_metrics/evaluate_pipe_run.py`
- `docs/common-validation-traps.md`
- `docs/annulus-shell-notes.md`

Primary upstream sources:

- ASPECT user documentation:
  `https://aspect-documentation.readthedocs.io/en/stable/user/index.html`
- ASPECT source repository:
  `https://github.com/geodynamics/aspect`

Recommended next step after creating these files:

1. replace version placeholders with the exact ASPECT version you will target
2. expand the example indexes from your `F1/source_prm_dataset/files/`
3. build retrieval over this folder plus real source `.prm` examples
4. run comprehensive metrics on a `Pipe.py` output directory
