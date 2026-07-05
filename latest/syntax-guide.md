# ASPECT Syntax Guide

ASPECT parameter files use `deal.II` ParameterHandler-style syntax.

Core rules:

- Each parameter assignment line must begin with `set `.
- Nested blocks must begin with `subsection <name>`.
- Every opened subsection must close with `end`.
- Comments are allowed in real `.prm` files, but generated output should focus on
  valid parameters first.
- Final output should be plain `.prm` content only.

Minimal valid example:

```text
set Dimension = 2

subsection Geometry model
  set Model name = box
  subsection Box
    set X extent = 1
    set Y extent = 1
  end
end
```

Valid patterns:

- `set Dimension = 2`
- `set End time = 1e6`
- `subsection Boundary temperature model`
- nested subsections under top-level feature blocks

Invalid patterns:

- `dimension = 2`
- `geometry:`
- `{"Dimension": 2}`
- Markdown fences around the `.prm`
- free-form explanation mixed into parameter output

Generation guidance:

- Use exact subsection names when known.
- Prefer copying official subsection names from ASPECT documentation or working
  examples.
- If a feature requires nested configuration, include the parent subsection and
  the named child subsection.
- Do not invent alternative config syntaxes.

Repair guidance:

- convert loose `key = value` lines into `set Key = value`
- convert pseudo-blocks into `subsection` / `end`
- remove headings, bullets, and prose
- preserve intended physics and model setup
