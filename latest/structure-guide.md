# ASPECT Structure Guide

ASPECT `.prm` files do not have a single mandatory ordering, but official files
tend to follow a recognizable structure.

Common top-level parameters:

- `set Dimension = ...`
- global run controls such as timing, CFL, solver, and output cadence

Common top-level subsections:

- `subsection Geometry model`
- `subsection Boundary temperature model`
- `subsection Boundary velocity model`
- `subsection Initial temperature model`
- `subsection Initial composition model`
- `subsection Gravity model`
- `subsection Material model`
- `subsection Mesh refinement`
- `subsection Postprocess`
- `subsection Solver parameters`
- `subsection Termination criteria`
- `subsection Compositional fields`
- `subsection Heating model`

Typical pattern:

```text
set Dimension = 2

subsection Geometry model
  set Model name = box
  subsection Box
    set X extent = 1000000
    set Y extent = 660000
  end
end

subsection Material model
  set Model name = simple
  subsection Simple model
    set Reference viscosity = 1e21
  end
end

subsection Boundary temperature model
  set Fixed temperature boundary indicators = top, bottom
  set List of model names = box
  subsection Box
    set Bottom temperature = 1600
    set Top temperature = 273
  end
end
```

Structural generation advice:

- Start from geometry and dimension first.
- Then set the main physics blocks:
  material, gravity, temperature, velocity, composition, heating.
- Then set numerical and mesh controls.
- Then set postprocessing and output.

Structural reverse-engineering advice:

- extract the domain geometry and dimension
- identify the primary formulation and physics
- identify active fields such as temperature, composition, melt, free surface,
  particles, strain, or reactions
- summarize boundary and initial conditions
- summarize mesh refinement and postprocessing separately

What not to do:

- do not flatten nested configuration into one pseudo-section
- do not rename subsections casually
- do not omit child subsections for the chosen model when they are required
