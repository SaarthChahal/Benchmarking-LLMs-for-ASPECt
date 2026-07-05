# Feature Areas

Use these categories to classify a user request before retrieval.

Core categories:

- thermal convection
- Stokes or flow-only problems
- free surface
- melt transport
- compositional advection
- particles
- phase transitions
- plasticity and viscoplastic flow
- shell or chunk geometry
- spherical or global mantle flow
- subduction
- continental extension or lithosphere deformation
- benchmark validation cases

For each category, retrieval should prefer:

1. closest official examples
2. matching geometry documentation
3. matching material model documentation
4. matching special physics documentation

Examples:

- `box convection`:
  geometry model `box`, thermal boundary conditions, simple or cookbook
  convection examples
- `subduction`:
  subduction cookbooks, compositional fields, rheology, boundary velocity
  conditions, phase transitions if present
- `melt transport`:
  melt-enabled examples, compositional fields, heating, material models that
  expose melt-related parameters
