# New Reduced Metrics

This document defines the reduced metric set for the `Latest/` roundtrip run.
It replaces the older wider summary with seven metrics that are easier to read
and harder to misinterpret.

The guiding principle is simple:

- use error rates for missing or invented content
- use retention scores for structure and physics similarity
- keep one signed delta for physics movement
- keep attempts as the operational difficulty signal

## Notation

Let:

- `B` = baseline `.prm`
- `R` = regenerated `.prm`
- `U(X)` = parameter signature set for file `X`
- `S(X)` = section signature set for file `X`
- `C(X)` = extracted concept set for file `X`
- `E_c` = expected concept set for category `c`
- `P(X)` = PPS score for file `X`

The implementation uses parsed ASPECT structure when available:

- `U(X)` is built from flattened parameter keys
- `S(X)` is built from subsection paths
- `C(X)` comes from the existing concept extractor
- `P(X)` comes from the existing physics plausibility scorer

## 1. `attempts_used`

What it measures:

- how many generation plus repair cycles were needed before the final file was
  accepted

Formula:

```text
attempts_used = 1 + number_of_repairs
```

Trend meaning:

- lower is better
- `1` means the first generation already passed
- rising values mean the model needed more repair help

Why it matters:

- this is the operational cost of the roundtrip
- a file that takes four repair steps is more expensive than one that passes on
  the first try, even if the final files look similar

## 2. `param_omission`

What it measures:

- how many baseline parameters disappeared from the regenerated file

Definition:

```text
O = U(B) \ U(R)
```

Normalized score:

```text
param_omission = |U(B) \ U(R)| / max(|U(B)|, 1)
```

Equivalent form:

```text
param_omission = 1 - |U(B) ∩ U(R)| / max(|U(B)|, 1)
```

Trend meaning:

- lower is better
- `0` means nothing important from the baseline was dropped
- `1` means all baseline parameter signatures were lost

Why it matters:

- this is the cleanest “what got lost?” signal
- it catches missing section keys, missing parameter lines, and dropped child
  subsection content

What `U(X)` contains:

- flattened parameter keys from the parsed `.prm`
- for example, `Geometry model.Box.X extent`
- values are not part of this score; only presence of the parameter key is
  counted

## 3. `hallucination`

What it measures:

- how many new parameters the regenerated file invented that were not present
  in the baseline

Definition:

```text
H = U(R) \ U(B)
```

Normalized score:

```text
hallucination = |U(R) \ U(B)| / max(|U(R)|, 1)
```

Equivalent form:

```text
hallucination = 1 - |U(B) ∩ U(R)| / max(|U(R)|, 1)
```

Trend meaning:

- lower is better
- `0` means the regenerated file introduced no extra parameter signatures
- higher values mean the model invented more content

Why it matters:

- omission alone does not tell you whether the model also added wrong content
- hallucination is the mirror image of omission
- a strong roundtrip should keep both near zero

## 4. `category_alignment_loss`

What it measures:

- how much the regenerated file drifted away from the expected category

Definition:

```text
category_alignment_score = |E_c ∩ C(R)| / max(|E_c|, 1)
category_alignment_loss = 1 - category_alignment_score
```

Trend meaning:

- lower is better
- `0` means all expected category-defining concepts are present
- higher values mean the regenerated file stopped looking like the intended
  class of model

Why it matters:

- a file can be syntactically valid and still drift into the wrong physics family
- this metric keeps geometry and physics intent tied to the source category

## 5. `structural_retention`

What it measures:

- how much of the source file’s ASPECT structure survived the roundtrip

Definition:

```text
J(X, Y) = |X ∩ Y| / |X ∪ Y|

structural_retention =
  0.5 * J(S(B), S(R)) +
  0.5 * J(U(B), U(R))
```

Trend meaning:

- higher is better
- `1` means the regenerated file preserved both the section skeleton and the
  parameter layout
- `0` means the structure diverged completely

Why it matters:

- ASPECT inputs are not just bags of keywords
- subsection nesting and parameter placement are part of the model meaning

Why this form:

- the Jaccard form is simple and bounded
- it avoids hidden weighting inside a black-box structural score
- it gives a stable summary of both section shape and parameter layout

## 6. `physics_retention`

What it measures:

- how close the regenerated file’s physics plausibility is to the baseline

Definition:

```text
P_b = P(B)
P_r = P(R)

physics_retention = min(P_b, P_r) / max(P_b, P_r)
```

If both scores are zero:

```text
physics_retention = 1
```

Trend meaning:

- higher is better
- `1` means the regenerated file matches the baseline PPS exactly
- values closer to `0` mean a large physics plausibility mismatch

Why this is better than the old ratio:

- the old `P_r / P_b` ratio is directional and can be misleading
- the new form is symmetric
- the new form is bounded in `[0, 1]`
- the new form measures closeness, not direction

Important interpretation:

- this is a similarity score, not a signed improvement score
- if you want direction, use `pps_delta`

## 7. `pps_delta`

What it measures:

- the signed change in physics plausibility from baseline to regenerated

Definition:

```text
pps_delta = P(R) - P(B)
```

Trend meaning:

- `0` is ideal for fidelity
- positive values mean the regenerated file scored higher than baseline
- negative values mean the regenerated file scored lower than baseline

Why it matters:

- `physics_retention` tells you how close the two scores are
- `pps_delta` tells you whether the change went up or down
- keeping both avoids collapsing two different questions into one number

How to read it:

- if `physics_retention` is high and `pps_delta` is near zero, the physics
  signal is stable
- if `physics_retention` is high but `pps_delta` is strongly positive or
  negative, the file may have moved together with the source but still shifted
  meaningfully
- if `physics_retention` is low and `pps_delta` is large in magnitude, the
  regenerated file diverged sharply

## Recommended Trend Summary

For a good run:

- `attempts_used` should trend downward
- `param_omission` should trend downward
- `hallucination` should trend downward
- `category_alignment_loss` should trend downward
- `structural_retention` should trend upward
- `physics_retention` should trend upward
- `pps_delta` should trend toward `0`

## Scoring Priorities

If the metrics disagree, use this order of trust:

1. `attempts_used`
2. `param_omission`
3. `hallucination`
4. `category_alignment_loss`
5. `structural_retention`
6. `physics_retention`
7. `pps_delta`

Reason:

- omission and hallucination are the most direct evidence of content drift
- category alignment checks whether the file still belongs to the intended
  physics family
- structure and physics retention are broader similarity checks
- `pps_delta` is informative, but it should be interpreted with the other
  metrics rather than alone

