# Parameter File Structure

Source focus:

- ASPECT user documentation
- official repository examples

ASPECT parameter files are organized around:

- top-level scalar parameters
- named subsections
- nested child subsections for specific models

Core structural ideas:

- `Dimension` is usually declared near the top
- feature families are configured by top-level subsections
- many configurable areas use a dispatch pattern:
  `set Model name = ...` followed by a child subsection named for that model

Examples of dispatch-style structure:

- geometry model selection followed by geometry-specific subsection
- material model selection followed by material-model-specific subsection
- initial or boundary model selection followed by the chosen model subsection

Sections commonly needed in generation:

- geometry
- material model
- gravity
- thermal boundary and initial conditions
- velocity boundary conditions
- compositional fields
- heating
- mesh refinement
- solver and termination behavior
- postprocessing and output

Practical implication for LLM generation:

- retrieving only syntax is not enough
- retrieval must include both parameter documentation and working examples
- the chosen model family determines which child subsection names are valid
