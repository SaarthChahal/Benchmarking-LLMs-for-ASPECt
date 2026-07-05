# SRC001 Worked Example

This is the full worked scoring example for:

- `prompt_id`: `SRC001`
- `category`: `Thermal Convection`
- `source_hint`: `cookbook: 2d_annulus_visualization`
- `model`: `anthropic/claude-3-haiku`

Baseline file:

- `source_prm_dataset/files/2d_annulus_visualization__2d_annulus_example.prm`

Regenerated file:

- `runs/roundtrip_97prms_7models/regenerated_prms/2d_annulus_visualization__2d_annulus_example__anthropic__claude-3-haiku.prm`

## Reported Row Values

- `parse_valid = False`
- `attempts_used = 4`
- `param_omission = 0.1714`
- `hallucination = 0.0`
- `category_alignment_loss = 0.0`
- `structural_retention = 0.9143`
- `physics_retention = 1.0`
- `pps_delta = 0.0`

## 1. Attempts Used

This value comes from the run summary, not from PRM structure.

```text
attempts_used = 4
```

Meaning:

- the file needed 4 generation/repair cycles before the run stopped on that pair

## 2. Parameter Omission

From the parsed files:

- baseline parameter keys: `35`
- regenerated parameter keys: `29`
- intersection: `29`

So the number of omitted baseline parameters is:

```text
|U(B) \ U(R)| = 35 - 29 = 6
```

Normalized omission:

```text
param_omission = 6 / 35
               = 0.1714285714
               \u2248 0.1714
```

Interpretation:

- about `17.14%` of the baseline parameter signatures were missing

## 3. Hallucination

From the same parsed files:

- regenerated parameter keys: `29`
- baseline parameter keys: `35`
- intersection: `29`

So the number of invented parameter signatures is:

```text
|U(R) \ U(B)| = 29 - 29 = 0
```

Normalized hallucination:

```text
hallucination = 0 / 29
              = 0.0
```

Interpretation:

- the regenerated file did not invent extra parameter signatures

## 4. Category Alignment Loss

For the category `Thermal Convection`, the expected concept set is:

```text
E_c = {
  fixed_temperature,
  geometry,
  material_or_rheology,
  temperature_initial_or_formulation
}
```

That is `4` expected concepts.

The regenerated file contains concepts that satisfy all 4 expectations:

- `fixed_temperature`
- `spherical_shell_geometry`, which satisfies `geometry`
- `simple_material`, which satisfies `material_or_rheology`
- `initial_temperature`, which satisfies `temperature_initial_or_formulation`

So:

```text
|E_c \u2229 C(R)| = 4
|E_c| = 4
```

Category alignment score:

```text
category_alignment_score = 4 / 4 = 1.0
```

Category alignment loss:

```text
category_alignment_loss = 1 - 1.0 = 0.0
```

Interpretation:

- the file still looks like the right category of model

## 5. Structural Retention

The implementation uses:

```text
structural_retention
  = 0.5 * J(S(B), S(R)) + 0.5 * J(U(B), U(R))
```

where:

```text
J(X, Y) = |X \u2229 Y| / |X \u222a Y|
```

### Section Jaccard

From the parsed files:

- baseline sections: `16`
- regenerated sections: `16`
- section intersection: `16`

So:

```text
J(S(B), S(R)) = 16 / 16 = 1.0
```

### Parameter Jaccard

From the parsed files:

- baseline parameters: `35`
- regenerated parameters: `29`
- intersection: `29`

So union size:

```text
|U(B) \u222a U(R)| = 35 + 29 - 29 = 35
```

Thus:

```text
J(U(B), U(R)) = 29 / 35 = 0.8285714286
```

### Final Structural Retention

```text
structural_retention
  = 0.5 * 1.0 + 0.5 * 0.8285714286
  = 0.5 + 0.4142857143
  = 0.9142857143
  \u2248 0.9143
```

Interpretation:

- the section structure was preserved perfectly
- some parameter signatures were dropped

## 6. Physics Retention

The baseline PPS and regenerated PPS are both:

```text
P(B) = 0.6945
P(R) = 0.6945
```

The reworked physics retention is:

```text
physics_retention = min(P(B), P(R)) / max(P(B), P(R))
```

So:

```text
physics_retention = 0.6945 / 0.6945 = 1.0
```

Interpretation:

- the PPS value did not change

## 7. PPS Delta

This is the signed change in PPS:

```text
pps_delta = P(R) - P(B)
```

So:

```text
pps_delta = 0.6945 - 0.6945
          = 0.0
```

Interpretation:

- there was no net change in physics plausibility

## 8. PPS Full Breakdown

The PPS formula is:

```text
PPS =  0.15 * PPRS +  0.20 * RNCS +  0.10 * TTC  +  0.10 * STRC +  0.15 * BCSC +  0.15 * MCS  +  0.05 * CCS  +  0.10 * PRC
```

For this baseline file, the breakdown is:

- `PPRS = 1.0`
- `RNCS = 0.5`
- `TTC = 0.0`
- `STRC = 0.5`
- `BCSC = 1.0`
- `MCS = 1.0`
- `CCS = 0.8901`
- `PRC = 0.5`

Now substitute:

```text
PPS =  0.15*1.0 +  0.20*0.5 +  0.10*0.0 +  0.10*0.5 +  0.15*1.0 +  0.15*1.0 +  0.05*0.8901 +  0.10*0.5
```

Compute each term:

```text
0.15 * 1.0    = 0.1500
0.20 * 0.5    = 0.1000
0.10 * 0.0    = 0.0000
0.10 * 0.5    = 0.0500
0.15 * 1.0    = 0.1500
0.15 * 1.0    = 0.1500
0.05 * 0.8901 = 0.044505
0.10 * 0.5    = 0.0500
```

Sum:

```text
PPS = 0.1500 + 0.1000 + 0.0000 + 0.0500 + 0.1500 + 0.1500 + 0.044505 + 0.0500
    = 0.694505
```

Rounded:

```text
PPS = 0.6945
```

## 9. What The PPS Subscores Mean

### `PPRS = 1.0`

All 7 checked physical parameters were inside valid ranges.

Checked parameters:

- density
- viscosity
- thermal conductivity
- thermal expansion coefficient
- reference specific heat
- gravity magnitude
- initial global refinement

So:

```text
passed = 7
checked = 7
PPRS = 7 / 7 = 1.0
```

### `RNCS = 0.5`

The scorer could not infer Rayleigh number from the file in the way it expects.

Fallback:

```text
RNCS = 0.5
```

### `TTC = 0.0`

End time was missing or zero, so the thermal-timescale check failed.

Fallback:

```text
TTC = 0.0
```

### `STRC = 0.5`

The tolerance-resolution check could not be fully evaluated.

Fallback:

```text
STRC = 0.5
```

### `BCSC = 1.0`

Boundary conditions were internally consistent.

Fallback:

```text
BCSC = 1.0
```

### `MCS = 1.0`

All required sections for the declared model were present.

Fallback:

```text
MCS = 1.0
```

### `CCS = 0.8901`

This is weighted completeness over expected top-level sections.

Present:

- Geometry model
- Material model
- Gravity model
- Boundary temperature model
- Boundary velocity model
- Initial temperature model
- Mesh refinement
- Postprocess
- Formulation
- Dimension

Absent:

- Solver parameters
- End time

Weights:

- Geometry model: `1.0`
- Material model: `1.0`
- Gravity model: `1.0`
- Boundary temperature model: `0.9`
- Boundary velocity model: `0.9`
- Initial temperature model: `0.8`
- Mesh refinement: `0.8`
- Postprocess: `0.7`
- Formulation: `0.6`
- Solver parameters: `0.5`
- End time: `0.5`
- Dimension: `0.4`

Achieved weight:

```text
1.0 + 1.0 + 1.0 + 0.9 + 0.9 + 0.8 + 0.8 + 0.7 + 0.6 + 0.4 = 8.1
```

Total weight:

```text
1.0 + 1.0 + 1.0 + 0.9 + 0.9 + 0.8 + 0.8 + 0.7 + 0.6 + 0.5 + 0.5 + 0.4 = 9.1
```

So:

```text
CCS = 8.1 / 9.1 = 0.890109...
\u2248 0.8901
```

### `PRC = 0.5`

Rayleigh number could not be classified, so the regime consistency scorer used its fallback score.

```text
PRC = 0.5
```

## Final Summary

For `SRC001`, the full math gives:

```text
attempts_used = 4
param_omission = 6/35 = 0.1714
hallucination = 0/29 = 0.0
category_alignment_loss = 1 - 4/4 = 0.0
structural_retention = 0.5*(16/16) + 0.5*(29/35) = 0.9143
physics_retention = 0.6945/0.6945 = 1.0
pps_delta = 0.6945 - 0.6945 = 0.0
PPS = 0.15*1.0 + 0.20*0.5 + 0.10*0.0 + 0.10*0.5 + 0.15*1.0 + 0.15*1.0 + 0.05*0.8901 + 0.10*0.5
    = 0.6945
```

Interpretation:

- structure was mostly preserved
- category stayed correct
- physics plausibility stayed unchanged
- but 6 baseline parameter signatures were missing

