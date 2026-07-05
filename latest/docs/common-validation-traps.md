# Common Validation Traps

These are common reasons ASPECT-generated `.prm` files fail even when the file
looks syntactically plausible.

## Do Not Invent Alternative Parameter Schemas

- Do not replace one valid ASPECT parameter family with a made-up equivalent.
- Prefer exact names from official examples and documentation.

## Boundary Velocity Model Traps

- `Tangential velocity boundary indicators` is not the same as
  `Prescribed velocity boundary indicators`.
- Do not use `Prescribed velocity boundary indicators` unless the selected
  boundary velocity model actually expects a mapped prescribed-velocity pattern.
- In many official examples, boundary indicators are named `top` and `bottom`,
  even for spherical shell geometries. Do not rename them to `inner` and
  `outer` unless the source file already does so.

## Boundary Temperature Model Traps

- Keep `Fixed temperature boundary indicators` when that is what the source file
  uses.
- Do not rewrite it into an unrelated `Model name = fixed values` schema unless
  official ASPECT documentation for the target version supports that exact form.

## Material Model Traps

- When `Model name = simple`, the child subsection is `Simple model`.
- Do not shorten subsection names to `Simple`.

## Gravity Model Traps

- Preserve valid model names such as `radial constant`.
- Do not collapse them into guessed names like `radial`.

## Output And Visualization Traps

- Prefer official `Postprocess` blocks with `Visualization` subsection.
- Do not invent a top-level `Output` subsection unless the source example and
  docs for the target version clearly use it.
