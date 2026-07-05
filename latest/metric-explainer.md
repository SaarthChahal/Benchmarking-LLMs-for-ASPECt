# Reduced Metric Explainer

This file explains the reduced metric set used in `Latest/`.

The goal is to keep only six reported metrics, plus a seventh operational
metric that measures repair difficulty.

## Final Metric Set

### 1. `baseline_to_reverse_f1`

What it measures:

- how faithfully the reverse prompt captures the source `.prm`

Why it is kept:

- the reverse step is a major source of information loss
- F1 is enough by itself, so recall and precision were removed

Interpretation:

- high is good
- low means the reverse prompt missed source concepts or hallucinated new ones

### 2. `baseline_to_regenerated_f1`

What it measures:

- how faithfully the regenerated `.prm` preserves the source `.prm` concepts

Why it is kept:

- this is the main config-level roundtrip fidelity score

Interpretation:

- high is good
- low means the regenerated file drifted away from the original setup

### 3. `structural_retention_scs`

What it measures:

- overall structural correctness of the regenerated file relative to the source

Why it is kept:

- structure matters for ASPECT inputs
- this one score replaces several lower-level structural metrics

Interpretation:

- high is good
- low means subsection structure, parameter keys, or layout were not preserved

### 4. `physics_retention_ratio`

What it measures:

- how much physics plausibility is retained in the regenerated file compared to
  the source

Formula:

- `physics_regenerated_pps / physics_baseline_pps`

Why it is kept:

- it normalizes plausibility relative to the source rather than using raw PPS

Interpretation:

- `1.0` means equal plausibility
- below `1.0` means degraded plausibility
- above `1.0` means regenerated scored higher than source

### 5. `regenerated_category_expectation_score`

What it measures:

- whether the regenerated file still looks like the right class of problem

Examples:

- thermal convection should keep thermal-convection-like concepts
- melt transport should keep melt-related concepts
- annulus or shell cases should preserve the right geometry family

Why it is kept:

- a file can be structurally similar but semantically drift into the wrong kind
  of ASPECT model

Interpretation:

- high is good
- low means category-defining physics or geometry got lost

### 6. `parse_valid`

What it measures:

- whether the final generated file is accepted by the current validation logic

Why it is kept:

- a file that does not parse or validate is not useful, even if concept scores
  look acceptable

Interpretation:

- `true` means validation succeeded
- `false` means the file still failed the current validation loop

Important note:

- if validation uses long ASPECT runs, timeout policy matters
- for development, this should ideally mean parse-valid or setup-valid, not
  necessarily full scientific completion

### 7. `attempts_used`

What it measures:

- how many generation plus repair attempts were needed before the final file was
  produced

Why it is kept:

- it measures difficulty and repair burden
- two files with similar quality scores may differ a lot in how much repair was
  needed

Interpretation:

- lower is better
- `1` means the first generation already passed
- larger numbers mean the file needed more repair cycles

## Why Other Metrics Were Removed

The following were removed from the main output because they were redundant or
too detailed for the primary summary:

- separate recall and precision scores
- omission and hallucination lists
- lower-level structural submetrics
- raw category/source-hint supporting fields
- raw PPS delta fields

They can still be computed later if needed, but they are no longer part of the
main reduced reporting set.

## Recommended Reporting Order

When presenting results, use this order:

1. `parse_valid`
2. `attempts_used`
3. `baseline_to_regenerated_f1`
4. `structural_retention_scs`
5. `physics_retention_ratio`
6. `regenerated_category_expectation_score`
7. `baseline_to_reverse_f1`

This order emphasizes whether the file works at all before discussing fidelity.
