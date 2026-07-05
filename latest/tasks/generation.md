# Generate From Prompt

Goal:

- convert a concise natural-language model description into a complete ASPECT
  `.prm` file

Required output behavior:

- return only `.prm` content
- use strict `set ` syntax
- use `subsection <name>` and `end`
- do not emit prose, headings, bullets, or code fences

Generation priorities:

1. pick the correct dimension and geometry
2. select the right major physics blocks
3. use official ASPECT naming for subsections and parameters
4. fill in the material model and its required child subsection
5. add boundary and initial conditions
6. add mesh refinement and output settings
7. add postprocessors needed by the described task

Retrieval targets for generation:

- syntax guide
- structure guide
- parameter documentation for the requested feature area
- one to three similar official examples

When multiple examples exist:

- prefer the closest geometry
- then prefer the closest physics
- then prefer the closest material model

Common failure modes:

- using invalid subsection names
- omitting a required child subsection
- mixing prose into the output
- generating plausible but undocumented parameter names
- copying a model name but not its required parameters

Recommended prompt framing:

- user prompt describing the model
- syntax guide
- one short structural guide
- retrieved official examples
- retrieved parameter documentation snippets

Validation expectation:

- generated output should be parsed or run against ASPECT
- if validation fails, feed the error into a repair step
