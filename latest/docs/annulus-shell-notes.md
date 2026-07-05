# Annulus And Spherical Shell Notes

Use this guide for `2d_annulus_visualization` and similar spherical shell cases.

## Geometry

- `set Dimension = 2`
- `subsection Geometry model`
- `set Model name = spherical shell`
- child subsection: `subsection Spherical shell`

## Boundary Indicators

For the official annulus example in this bundle:

- temperature boundaries use `bottom, top`
- tangential velocity boundaries use `bottom, top`

Do not rewrite these to `inner, outer` just because the geometry is spherical
shell. Preserve the source file's actual indicator convention.

## Initial Temperature

The official example uses:

- `subsection Initial temperature model`
- `set Model name = function`
- child subsection `Function`
- `set Coordinate system = spherical`
- `set Variable names = r,phi`

## Boundary Temperature

The official example uses:

- `set Fixed temperature boundary indicators = bottom, top`
- `set List of model names = spherical constant`
- child subsection `Spherical constant`

## Boundary Velocity

The official example uses:

- `subsection Boundary velocity model`
- `set Tangential velocity boundary indicators = bottom, top`

No prescribed-velocity map is used in this example.
