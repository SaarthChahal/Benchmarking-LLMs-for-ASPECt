# Blog post

# Round-Trip Generation of ASPECT Parameter Files with Retrieval and Validation-Guided Repair

Scientific software is a tough target for large language models. It is not enough to produce something that looks plausible. The output must also satisfy strict syntax, preserve the structure of the original artifact, and remain faithful to the underlying scientific setup.

That is the problem we studied in our ASPECT project.

ASPECT is a geodynamics simulation code that uses structured `.prm` parameter files to define geometry, material models, gravity, boundary conditions, initial conditions, mesh refinement, solver behavior, and postprocessing. These files are compact and expressive, but they are also brittle: one unsupported parameter name, one misplaced subsection, or one incompatible plugin choice can make the whole configuration unusable.

Our project asks a simple but demanding question:

Can a large language model read an existing ASPECT parameter file, describe its modeling intent in natural language, and then regenerate a faithful ASPECT configuration from that description?

We frame this as a **round-trip generation** task.

1. Start with a source ASPECT `.prm` file.
2. Reverse-engineer it into a natural-language prompt.
3. Regenerate a new `.prm` file from that prompt using retrieved ASPECT documentation and examples.
4. Validate the regenerated file with ASPECT.
5. If validation fails, use the validator feedback in a repair loop.

This setup lets us evaluate two different things at once:

- whether the model preserves the scientific setup
- whether it can express that setup in exact ASPECT-compliant form

## Why this is harder than ordinary code generation

ASPECT parameter files are not just configuration snippets. They encode modeling decisions. A file may specify domain geometry, gravity, thermal or compositional structure, material laws, solver settings, and output behavior, all through nested sections with plugin-conditioned options.

That creates a useful distinction between **semantic plausibility** and **operational validity**.

- A semantically plausible file looks like the right geodynamic model.
- An operationally valid file is accepted by ASPECT and can be used as a simulation input.

The gap between those two is the heart of the project.

## The pipeline

The reported pipeline is retrieval-oriented. It uses:

- ASPECT syntax and structure guides
- feature-area notes
- documentation indexes
- example families
- validation traps from earlier runs

The model first produces a reverse prompt from the source file. A second generation step then reconstructs the `.prm` file using the reverse prompt plus retrieved local context. Validation is external: a file is only considered parse-valid if ASPECT accepts it.

If validation fails, the model gets the validator output and attempts a repair. The maximum number of repair attempts observed was four.

## Dataset and evaluation

The study evaluates **97 source ASPECT `.prm` files** across **seven model backends**:

- Claude-3-Haiku
- Claude-3.5-Haiku
- DeepSeek-V3.2
- LLaMA-3.1-8B-Instruct
- GPT-4o
- GPT-4o-mini
- Qwen3-32B

This yields **679 source-model pairs**.

The evaluation does not stop at whether the generated file looks reasonable. It measures:

- **attempts used**
- **parameter omission**
- **hallucination**
- **category alignment loss**
- **structural retention**
- **physics retention**
- **delta PPS** (change in physics plausibility score)

These metrics are designed to separate parser validity from source fidelity and physics preservation.

## What the aggregate results show

Across the 679 evaluated pairs, the average outcomes are:

- **Attempts used:** 3.8910
- **Parameter omission:** 0.0600
- **Hallucination:** 0.1129
- **Category alignment loss:** 0.1739
- **Structural retention:** 0.8547
- **Physics retention:** 0.9644
- **Delta PPS:** +0.0100

The headline result is a clear split between **fidelity** and **executability**.

On average, the regenerated files preserve much of the original structure and much of the physics signal. But that does not mean they are easy to run. The files are often recognizably close to the source problem while still failing ASPECT's exact parser and plugin constraints.

## Repair saturation is the rule

One of the strongest findings in the report is how heavily the repair loop saturates.

Out of 679 runs:

- **654** consumed the full four-attempt budget
- **24** succeeded in one attempt
- **1** terminated in two attempts

That means **96.3%** of runs hit the repair maximum.

This is important because it changes how we should interpret repair. Validator feedback does help produce better final artifacts for analysis, but it rarely rescues a generation into an early clean solution. In practice, most examples require maximal repair effort.

## Physics retention is stronger than executability

Physics retention measures how closely the regenerated file preserves the source file's physics plausibility score. Because it is normalized as a ratio, a value close to 1 means the regenerated file remains close to the source under the scorer.

The model-level results show that:

- **Qwen3-32B** has the highest average physics retention at **0.982**
- **GPT-4o** follows closely at **0.981**
- **GPT-4o-mini** reaches **0.979**
- **Claude-3.5-Haiku** reaches **0.975**

But high physics retention does not automatically imply better category fidelity.

For example:

- **DeepSeek-V3.2** has lower physics retention (**0.950**) but the lowest category alignment loss (**0.144**)
- **GPT-4o** has higher physics retention but worse alignment loss (**0.202**)

So preserving plausible physical settings and preserving the intended problem category are related, but not identical, capabilities.

At the category level, the report finds that:

- **Free Surface and Topography** has the highest average physics retention (**0.989**)
- **Melt Transport** and **Planetary and Tectonic Geodynamics** are harder in alignment terms, with category alignment losses of **0.397** and **0.230**
- **Thermal Convection** combines relatively low alignment loss (**0.063**) with lower physics retention (**0.954**) than the easier categories

## Structural retention tells a different story

Structural retention is the project's main structural similarity score. It is based on equal-weight overlap between:

- subsection-path Jaccard
- parameter-key Jaccard

So a high score means the regenerated file preserves both the **section skeleton** and the **parameter inventory** of the source.

The structural comparison highlights a different set of trade-offs:

- **GPT-4o** has the best structural retention (**0.919**) and the lowest hallucination rate (**0.071**)
- **Qwen3-32B** is close behind on structure (**0.893**) and has strong omission control (**0.018**)
- **Claude-3.5-Haiku** and **GPT-4o-mini** form a second cluster near **0.88**
- **DeepSeek-V3.2** has the lowest omission (**0.005**) but a relatively high hallucination rate (**0.153**)
- **LLaMA-3.1-8B-Instruct** is the weakest structurally, with omission **0.187**, hallucination **0.160**, and structural retention **0.743**

The category-level picture matters here too. The report identifies:

- **Composition Transport** and **Cookbook Inspired** as the easiest families structurally
- **Thermo-Mechanical Deformation** as the hardest, with structural retention **0.766** and hallucination **0.195**

## Residual-based physics check

The report does not stop at PRM-level metrics. It also includes a focused ASPECT execution comparison on three representative source files and their regenerated counterparts across all 7 models.

For the runs that terminated cleanly, the extracted end-of-run summaries matched exactly between source and regenerated runs on:

- RMS velocity
- maximum velocity
- temperature summary
- heat-flux terms where present
- composition mass summaries where present

That gives a valuable nuance to the main story.

When regenerated runs do converge, they can preserve the same physical endpoint as the source. The bigger problem is getting the configuration into a form that ASPECT will accept and run reliably.

The runtime comparison adds another layer. In the converged-only execution subset:

- **Claude-3.5-Haiku** and **DeepSeek-V3.2** are slightly faster than the corresponding sources on average
- **GPT-4o**, **GPT-4o-mini**, and **Qwen3-32B** are slower on average

The report notes that this difference is driven mainly by the `muparser_temperature_example` case. So even when two configurations converge to the same endpoint, the path to convergence can still differ in cost.

## The central conclusion

The report's main takeaway is not that LLMs fail to understand scientific systems.

It is almost the opposite.

The regenerated files often preserve broad scientific intent, meaningful structure, and high physics similarity. The real bottleneck lies in the final layer of simulator-specific correctness:

- exact parameter names
- exact subsection placement
- plugin-dependent option structure
- strict ASPECT-compliant syntax

This is why the paper argues for evaluation protocols that separate:

- operational validity
- category faithfulness
- structural overlap
- physics preservation

A generated scientific configuration can be physically close, structurally recognizable, and still unusable.

## What this means for AI in scientific computing

The project suggests that better prompts or bigger models alone will not fully solve the problem.

The more promising direction is to combine retrieval with stronger symbolic support:

- schema-aware decoding
- constrained generation over ASPECT's parameter grammar
- plugin-conditioned validation
- repair methods over structured representations instead of free-form text alone

The broader lesson is that ASPECT parameter files make a useful benchmark for scientific software generation precisely because they expose a realistic gap between **knowing the science** and **producing a valid executable artifact**.

That gap is where today's systems still struggle.

## Limits of the result

The report is careful about its limitations.

- The 97 files do not cover the full ASPECT parameter space.
- The run allows up to four attempts, so some failures may reflect repair-budget exhaustion.
- Physics plausibility is a proxy score, not a substitute for full scientific validation.
- Results depend on externally hosted model APIs and may shift with provider-side changes.
- Small prompt or retrieval differences can change the regenerated files.

So the findings are strong, but they should be read as measurements of the evaluated pipeline and API snapshots, not as timeless properties of model families.

---

# Twitter/X thread series

**Post 1**  
We studied whether LLMs can reconstruct real ASPECT geodynamics configuration files through a round-trip pipeline: read a source `.prm`, reverse-engineer it into natural language, regenerate a new `.prm`, validate it with ASPECT, and repair it using validator feedback.

This is a much stricter test than ordinary code generation because the output has to preserve scientific intent *and* satisfy exact simulator syntax.

ASPECT parameter files are not just settings files. They encode geometry, gravity, material models, boundary conditions, initial conditions, mesh refinement, solver settings, and postprocessing through nested, plugin-conditioned sections.

That means a file can look scientifically plausible and still fail operationally.

---

**Post 2**  
We evaluated the pipeline on **97 source ASPECT files** across **7 model backends**, yielding **679 source-model pairs**.

The backends were:
- Claude-3-Haiku
- Claude-3.5-Haiku
- DeepSeek-V3.2
- LLaMA-3.1-8B-Instruct
- GPT-4o
- GPT-4o-mini
- Qwen3-32B

---

**Post 3**  
Across all 679 runs, the average results were:

- attempts used: **3.8910**
- parameter omission: **0.0600**
- hallucination: **0.1129**
- category alignment loss: **0.1739**
- structural retention: **0.8547**
- physics retention: **0.9644**
- delta PPS: **+0.0100**

So the files often stayed close to the source structurally and physically, even when execution remained difficult.

---

**Post 4**  
The repair loop saturated hard.

Out of 679 runs:
- **654** used all 4 attempts
- **24** succeeded in 1 attempt
- **1** ended in 2 attempts

So **96.3%** of runs hit the repair maximum. Validator feedback helped, but it rarely produced an early clean solution.

---

**Post 5**  
Physics retention was stronger than executability.

At the model level:
- **Qwen3-32B** had the highest average physics retention (**0.982**)
- **GPT-4o** was close behind (**0.981**)

But high physics retention did not always mean better category fidelity.  
Example: **DeepSeek-V3.2** had lower physics retention (**0.950**) but the lowest category alignment loss (**0.144**).

---

**Post 6**  
Structural retention told a different story.

- **GPT-4o** had the best structural retention (**0.919**) and the lowest hallucination (**0.071**)
- **Qwen3-32B** was close behind on structure (**0.893**) and had strong omission control (**0.018**)
- **DeepSeek-V3.2** had the lowest omission (**0.005**) but relatively high hallucination (**0.153**)

So different models were strong on different dimensions.

---

**Post 7**  
We also ran a focused execution comparison on 3 representative source files and their regenerated counterparts across all 7 models.

For the runs that terminated cleanly, the extracted end-state summaries matched exactly between source and regenerated runs on velocity, temperature, heat-flux, and composition summaries.

So when the regenerated runs converge, they can preserve the same physical endpoint.

---

**Post 8**  
The main lesson is a split between **scientific fidelity** and **operational validity**.

The models often preserved broad scientific intent, meaningful structure, and high physics similarity. But they still failed on the exact details required by ASPECT: exact parameter names, exact subsection placement, plugin-dependent option structure, and strict syntax.

That is the real bottleneck.

---

**Post 9**  
The paper argues that scientific configuration generation should be evaluated as a bundle of capabilities:

- operational validity
- category faithfulness
- structural overlap
- physics preservation

A generated configuration can be physically close, structurally recognizable, and still unusable.

---

**Post 10**  
The forward path is not just “better prompting.”

The report points toward:
- schema-aware decoding
- constrained generation over ASPECT’s grammar
- plugin-conditioned validation
- more structured repair methods

More broadly, ASPECT parameter files are a useful benchmark because they expose the gap between *knowing the science* and *producing a valid executable artifact*.
