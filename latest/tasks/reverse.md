# Reverse Engineer PRM

Goal:

- turn a source ASPECT `.prm` file into a concise but complete natural-language
  prompt that another model could use to regenerate the same setup

The reverse prompt should cover:

- geometry and dimension
- formulation or major physics
- material model
- boundary conditions
- initial conditions
- compositional fields or special fields
- mesh refinement
- gravity and heating
- postprocessing and output behavior
- notable solver or termination choices when important

Reverse-engineering style:

- concise, but not vague
- preserve unusual parameters and special physics
- prioritize model-defining choices over generic defaults
- use natural language, not `.prm` syntax

What to preserve carefully:

- geometry type and extents
- free surface, melt, particles, reactions, phase transitions
- custom boundary-condition styles
- exact material-model family
- whether the case is 2D or 3D
- shell, chunk, annulus, or spherical domain distinctions

What to avoid:

- line-by-line restatement of the whole file
- unsupported guesses about omitted defaults
- outputting raw `.prm` syntax instead of a regeneration prompt
