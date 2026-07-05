# Parameter Documentation Index

Use this file as a routing map for retrieval, not as full documentation.

High-priority documentation areas:

- geometry models
- material models
- initial temperature models
- boundary temperature models
- boundary velocity models
- gravity models
- heating models
- mesh refinement
- postprocess
- compositional fields
- solver parameters

Questions to answer during retrieval:

- which subsection names are valid for this feature?
- which `Model name` values are valid?
- which child subsection corresponds to that model?
- which parameters are commonly required to make the setup meaningful?

When generating from a user prompt:

- map the prompt to one or more documentation areas first
- retrieve the matching example family second

When repairing:

- look up the specific feature area where the parse error or missing parameter
  occurs

Primary upstream references:

- ASPECT docs index:
  `https://aspect-documentation.readthedocs.io/en/stable/user/index.html`
- ASPECT repository:
  `https://github.com/geodynamics/aspect`
