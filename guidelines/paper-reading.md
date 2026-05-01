> ### Confidential & Proprietary
>
> **Author:** Younghoon
> **Copyright:** © 2026 Younghoon
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-23

---

# Paper Reading Guidelines (Specification)

---

## 1. Scope

Applies to academic paper reading tasks, including:

* research paper summary
* method/mechanism analysis
* result interpretation
* reproducibility assessment
* cross-paper comparison

This guideline is an extension of `guidelines/document-reading.md` and MUST be used together with it.

Application model:

* This guideline **[MUST]** be applied by content/evidence mode, not by assigning the whole paper a single exclusive type.
* A single paper **[MAY]** contain theoretical, empirical, numerical, simulation-based, and statistical support simultaneously.
* The agent **[MUST]** determine for each major claim which support mode is actually doing the justificatory work.
* If a conclusion relies on multiple support modes, the agent **[MUST]** apply all relevant checks rather than choosing only one subprofile.

---

## 2. Scientific Reporting Baseline

* **[MUST]** separate claims from evidence.
* **[MUST]** identify paper metadata where available: venue, year/date, version.
* **[MUST]** report explicit limitations and assumptions stated by authors.
* **[MUST NOT]** present hypothesis or discussion text as validated finding.
* **[MUST]** treat statements unsupported by cited section/table/figure as unresolved, not established.

---

## 3. Anti-Hallucination Contract

* **[MUST]** enforce claim-evidence pairing for all core conclusions.
* **[MUST]** keep extraction within provided paper scope unless user explicitly requests external comparison.
* **[MUST]** separate `Paper Facts` from `Agent Inferences` in output.
* **[MUST]** label each inference with confidence (`LOW | MED | HIGH`) and basis.
* **[MUST]** use `UNCERTAINTY::` for missing or ambiguous paper evidence before proceeding.
* **[MUST]** use the deterministic evidence locator schema defined in `guidelines/document-reading.md` Section 3.
* **[MUST NOT]** invent theorem statements, metric values, dataset details, or experimental settings.
* **[MUST NOT]** report as `Paper Fact` any claim not directly locatable in the provided source, regardless of agent prior knowledge.
* **[MUST NOT]** treat claims in abstract or introduction as validated unless supporting evidence is present elsewhere in the paper (e.g., proof section, derivation, evaluation, case study, or appendix).
* **[MUST NOT]** fabricate section numbers, figure labels, table identifiers, or equation references; if location cannot be confirmed, mark as unverified.
* **[MUST NOT]** escalate the epistemic status of a claim beyond what the source text asserts (e.g., `suggests` must not become `demonstrates`, `is consistent with` must not become `proves`).
* **[MUST]** label each major claim with its active support mode when the paper mixes evidence types (`theoretical | empirical | numerical | simulation | statistical | hybrid` or a comparably precise label).
* **[MUST NOT]** silently apply a single support mode to the whole paper when major claims are justified by different evidence types.
* **[MUST NOT]** omit a materially active support mode from analysis when a conclusion depends on multiple modes.

---

## 4. Support and Evaluation Extraction

* **[MUST]** summarize problem setup, method, and evaluation protocol separately.
* **[MUST]** include dataset/benchmark, metrics, and comparison baseline when provided.
* **[MUST]** distinguish empirical evidence from theoretical argument.
* **[MUST]** flag missing reproducibility details (code/data/seed/environment) as open risk.
* **[MUST]** identify the active support mode for each major claim when support comes from experiment, simulation, numerical analysis, statistical study, theoretical argument, or a mixture of evidence types.
* **[MUST]** evaluate claims of superiority against the actual comparison protocol: baseline choice, tuning fairness, training/inference budget, sample size, hardware, wall-clock cost, memory, data requirements, and human or engineering overhead when such details are available.
* **[MUST]** report improvement magnitude together with the extra resources, constraints, or assumptions required to obtain it.
* **[MUST]** distinguish absolute improvement from cost-adjusted improvement; if cost-adjusted comparison is impossible from the source, state that explicitly as an unresolved evaluation gap.
* **[MUST]** check whether the empirical gain appears robust across datasets, seeds, ablations, problem sizes, regimes, or statistical intervals when the paper provides such evidence.
* **[MUST]** identify whether the result appears likely to generalize beyond the tested setting or whether support is narrow, benchmark-specific, regime-specific, or assumption-sensitive.
* **[MUST NOT]** describe an approach as simply "better" when the paper only shows a tradeoff, such as accuracy for compute, robustness for latency, or quality for data scale.

For claims centered on empirical superiority, the agent MUST additionally:

* **[MUST]** ask whether the reported gain is practically meaningful relative to added cost, not only whether it is numerically positive.
* **[MUST]** identify whether comparisons are apples-to-apples with respect to model size, search budget, preprocessing, external data, hyperparameter tuning effort, and stopping criteria.
* **[MUST]** note when the method's gain may depend on privileged resources, specialized hardware, extra annotations, stronger priors, or hidden implementation complexity.
* **[MUST]** separate evidence for average-case improvement, worst-case improvement, and statistically significant improvement instead of merging them.
* **[MUST]** flag missing uncertainty quantification, variance reporting, confidence intervals, or significance testing when the paper makes strong empirical superiority claims.
* **[MUST]** identify whether the paper demonstrates scalability in the dimensions that matter for adoption, such as data size, runtime, memory, parameter count, experimental throughput, or deployment constraints.
* **[MUST NOT]** describe performance gains as simply `better` when the evidence shows only a costed tradeoff or a benchmark-limited advantage.

For claims supported primarily by empirical, numerical, simulation, or statistical evidence, the agent MUST additionally:

* **[MUST]** separate what is shown directly by measured results from what is extrapolated beyond the tested regime.
* **[MUST]** identify the exact evidence scope for each claim: benchmark set, parameter regime, sample population, discretization range, simulation setup, or statistical model assumptions.
* **[MUST]** flag when a broad scientific or methodological conclusion appears to rest on narrow experimental coverage.

### 4.1 Scientific Hypothesis-Testing and Inference

For claims supported by scientific hypothesis-testing, experimental science, or observational scientific inference, the agent MUST additionally:

* **[MUST]** reconstruct the chain `background theory or hypothesis -> observable prediction -> study or experiment -> result -> interpretation`.
* **[MUST]** distinguish the hypothesis itself from the operationalized prediction used in measurement or experiment.
* **[MUST]** state whether the evidence supports, is merely consistent with, weakens, or does not decisively test the stated hypothesis.
* **[MUST]** separate causal claims from correlational or associational claims and report when the study design does not justify causal language.
* **[MUST]** audit whether the design meaningfully addresses confounders, controls, intervention validity, and measurement validity when the claim depends on them.
* **[MUST]** distinguish effect size, uncertainty, and statistical significance rather than collapsing them into a single notion of support.
* **[MUST]** flag missing or weak reporting on sample size, power, uncertainty intervals, multiple testing control, preregistration, replication, or robustness checks when those omissions weaken inference.
* **[MUST]** identify plausible competing explanations or alternative hypotheses that the presented evidence does not clearly rule out.
* **[MUST]** assess internal validity, external validity, and construct validity when the paper's conclusion depends on general scientific interpretation.
* **[MUST NOT]** summarize a hypothesis as established if the evidence is only indirect, proxy-based, undercontrolled, or narrowly conditioned.
* **[MUST NOT]** present an unverified hypothesis, mechanistic story, or explanatory model as established fact unless the paper explicitly demonstrates that stronger conclusion.

---

## 5. Summary and Argument Reconstruction

* **[MUST]** produce a paper summary that reconstructs the authors' argument, not just a compressed topic overview.
* **[MUST]** identify the paper's central claim or thesis before summarizing supporting details.
* **[MUST]** organize the summary so that each major claim is paired with the evidence, reasoning, or experimental result the authors use to support it.
* **[MUST]** make the logical flow explicit where the paper depends on stepwise reasoning, such as `problem -> method -> claim -> evidence -> conclusion`.
* **[MUST]** make clear when different parts of the same conclusion are supported by different modes, such as theorem for correctness and experiment for practical advantage.
* **[MUST]** distinguish between what the authors directly establish and what remains suggestive, limited, or conditional.
* **[MUST]** explain why each cited piece of evidence matters to the claim it supports, not merely list sections, figures, or metrics.
* **[MUST NOT]** flatten multi-step arguments into isolated bullet facts when doing so obscures how the conclusion is justified.

---

## 6. Definitions, Theorems, and Formal Objects

* **[MUST]** extract and explain key definitions, formal problem statements, theorem/lemma/proposition claims, and named assumptions when they are material to understanding the paper.
* **[MUST]** describe each such item in plain language in addition to any formal phrasing, focusing on what concept it introduces and why it matters in the argument.
* **[MUST]** connect each definition or theorem to the role it plays in the paper, such as enabling the method, constraining the setting, or supporting a correctness/result claim.
* **[MUST]** distinguish formal statement, intuition, and proof status (`stated`, `proved`, `sketched`, or `used without proof in scope`) when that status is visible from the source.
* **[MUST NOT]** restate formal content without clarifying its conceptual function unless the user explicitly requests verbatim-form emphasis.

---

## 7. Logical Flow Reconstruction and Consistency Checks

* **[MUST]** reconstruct the paper's argument as an ordered dependency chain rather than a flat list of claims.
* **[MUST]** identify the minimal logical path from assumptions and definitions to each main conclusion.
* **[MUST]** state which intermediate lemmas, propositions, constructions, experiments, simulations, statistical analyses, or derivations each major claim depends on.
* **[MUST]** check whether quantifiers, domains, and scope conditions in the summary match the source claim rather than a weaker or stronger paraphrase.
* **[MUST]** distinguish necessity from sufficiency when the paper's reasoning depends on that distinction.
* **[MUST]** detect and report jumps in logic, deferred proof obligations, hidden assumptions, or claims whose support appears incomplete within the provided source.
* **[MUST]** include at least one explicit self-check pass that asks whether each summarized conclusion still holds after tracing back through its cited dependencies.
* **[MUST]** verify that the evidence mode attached to each claim is appropriate to the strength of the summarized conclusion; for example, an empirical trend alone does not establish a universal theorem-like statement.
* **[MUST NOT]** silently smooth over proof gaps, derivation gaps, or scope mismatches for the sake of readability.

Recommended double-check procedure:

* Re-read each main claim after drafting the summary and verify that the cited support is sufficient for the exact claim as stated.
* Re-check all direction-sensitive statements, such as implications, equivalences, reductions, bounds, and conservation or invariance claims.
* Re-check whether omitted assumptions would invalidate the summarized conclusion.

---

## 8. Reading Strategy and Guidance

* **[MUST]** provide a concrete reading strategy for the target paper unless the user explicitly requests summary-only output.
* **[MUST]** structure the strategy so a reader can recover the paper's core claims and supporting evidence efficiently.
* **[MUST]** include a recommended reading order, such as abstract/introduction, problem setup, main method, key figures/tables, evaluation, and limitations, adjusted to the active evidence modes when needed.
* **[MUST]** identify what the reader should extract at each stage: main question, claimed contribution, supporting evidence, assumptions, and unresolved gaps.
* **[MUST]** include checkpoints or guiding questions that help the reader verify whether they have understood the paper's argument correctly.
* **[SHOULD]** distinguish a fast first pass from a deeper second pass when the paper is technically dense.
* **[SHOULD]** point the reader to the highest-yield sections, figures, tables, equations, or appendices for validating the main claim.
* **[MUST]** tell the reader where to switch verification mode inside a mixed paper, such as from proof validation to experimental-audit validation.
* **[MUST NOT]** provide generic study advice that could apply to any paper without tying it to claim tracking, evidence tracking, or conceptual dependency.

---

## 9. Theoretical-Mode Subprofile

For claims supported primarily by theoretical argument, the agent MUST additionally:

* **[MUST]** identify the exact main theorem, law, principle, reduction, impossibility claim, or formal conclusion the paper is trying to establish.
* **[MUST]** list the dependency structure among assumptions, definitions, lemmas, and final results in proof order or derivation order.
* **[MUST]** separate statement, intuition, proof idea, and proof status for each principal result.
* **[MUST]** track the scope of every major claim, including domain restrictions, asymptotic regime, model assumptions, regularity assumptions, or boundary conditions.
* **[MUST]** flag places where the argument relies on nontrivial imported results, omitted derivations, appendix-only proofs, or phrases such as "it is easy to see" without local justification.
* **[MUST]** identify whether the contribution is a new theorem, sharper bound, new construction, new reduction, new interpretation, or unification of prior results.
* **[MUST]** test summarized logical flow against at least two failure modes, such as missing assumptions, reversed implication, invalid generalization, hidden regularity condition, or unjustified asymptotic step.
* **[MUST]** state what would need to be true for the main result to fail, weaken, or stop applying when such conditions are inferable from the paper.

For claims in mathematics and theoretical computer science, the agent MUST additionally:

* **[MUST]** preserve quantifier order, existence/uniqueness conditions, and reduction direction in the summary.
* **[MUST]** separate correctness, completeness, soundness, optimality, and complexity claims instead of merging them.
* **[MUST]** identify invariants, adversarial models, oracle models, or computational model assumptions when they are relevant.

For theoretically supported claims in physics, the agent MUST additionally:

* **[MUST]** distinguish physical assumptions, mathematical idealizations, and derived consequences.
* **[MUST]** track units, dimensional consistency, limiting regimes, symmetry principles, conservation laws, and approximation conditions when they are central to the argument.
* **[MUST]** identify whether a derivation is exact, perturbative, heuristic, effective-field, numerical, or conjectural in scope.

---

## 10. Logical Audit Output Requirements

When the paper contains claims that rely materially on the theoretical-mode subprofile, the final output MUST additionally include:

* Main Result Statement
* Dependency Chain or Proof Skeleton
* Assumption and Scope Audit
* Logical Consistency Check
* Failure Modes or Where the Argument Could Break

Recommended semantics for these sections:

* `Main Result Statement` SHOULD restate the central result at the highest faithful precision the source supports.
* `Dependency Chain or Proof Skeleton` MUST show how the result depends on prior definitions, lemmas, constructions, or physical premises.
* `Assumption and Scope Audit` MUST enumerate the conditions under which the result is claimed to hold.
* `Logical Consistency Check` MUST report whether the summarized reasoning survived a deliberate double-check for scope drift, implication direction, and missing support.
* `Failure Modes or Where the Argument Could Break` MUST identify concrete points where the conclusion would weaken, fail, or require extra justification.

---

## 11. Math/Algorithm Content Subprofile

For math or algorithm content, the agent MUST additionally:

* **[MUST]** list key assumptions, definitions, theorem/lemma dependencies.
* **[MUST]** distinguish proof sketch from full proof coverage.
* **[MUST]** report correctness argument and complexity bounds separately.
* **[MUST]** state required computation model or input constraints for complexity claims.
* **[SHOULD]** include edge cases, boundary behavior, and potential counterexample conditions when discussed.

---

## 12. Scientific Inference Output Requirements

When the paper contains claims that rely materially on scientific hypothesis-testing or scientific inference, the final output MUST additionally include:

* Hypothesis and Prediction Chain
* Study Design and Measurement Audit
* Causal vs Correlational Interpretation
* Validity and Confound Audit
* Alternative Explanations

Recommended semantics for these sections:

* `Hypothesis and Prediction Chain` MUST show how the paper maps theory or hypothesis into observable tests.
* `Study Design and Measurement Audit` MUST identify what was actually measured, how it was operationalized, and where design limits weaken interpretation.
* `Causal vs Correlational Interpretation` MUST state what level of inference the design justifies.
* `Validity and Confound Audit` MUST report whether internal, external, and construct validity appear strong, weak, or unresolved from the source.
* `Alternative Explanations` MUST identify major rival interpretations not clearly eliminated by the evidence.

---

## 13. Output Contract

As the more specific guideline, this output schema takes precedence over `guidelines/document-reading.md` Section 7 for paper reading tasks per AGENTS.md Section 4 (most restrictive rule applies at equal priority).

Unless user requests another format, output MUST include:

* Paper Metadata
* Executive Summary
* Argument Map (`claim -> support mode -> supporting basis -> evidence`)
* Key Definitions and Formal Objects
* Paper Facts
* Agent Inferences (if any, with confidence)
* Evidence and Where Found
* Method/Evaluation Summary
* Reading Strategy and Efficient Reading Guide
* Limitations and Threats to Validity
* Reproducibility Status
* (Empirical-comparison content only) Resource vs Benefit Assessment
* (Empirical-comparison content only) Generalization and Scalability Assessment
* (Scientific-inference content only) Hypothesis and Prediction Chain
* (Scientific-inference content only) Study Design and Measurement Audit
* (Scientific-inference content only) Causal vs Correlational Interpretation
* (Scientific-inference content only) Validity and Confound Audit
* (Scientific-inference content only) Alternative Explanations
* (Theoretical-mode content only) Main Result Statement
* (Theoretical-mode content only) Dependency Chain or Proof Skeleton
* (Theoretical-mode content only) Assumption and Scope Audit
* (Theoretical-mode content only) Logical Consistency Check
* (Theoretical-mode content only) Failure Modes or Where the Argument Could Break
* (Math/Algorithm content only) Assumptions, Correctness Basis, Complexity Basis
* Evidence Coverage Check (all core conclusions anchored)

---

Recommended semantics for required sections:

* `Executive Summary` MUST give the shortest complete explanation of what the paper claims, why the authors think it is true, and under what conditions the claim holds.
* `Argument Map` MUST make the claim-support structure explicit enough that a reader can trace each major conclusion back to its support mode, supporting evidence, and reasoning path.
* `Key Definitions and Formal Objects` MUST explain terms, assumptions, definitions, and theorem-like statements needed to understand the argument.
* `Reading Strategy and Efficient Reading Guide` MUST be actionable, staged, and optimized for recovering the paper's main claim, support, and limitations.
* `Resource vs Benefit Assessment` MUST state what performance gain was claimed, what additional resources or constraints were required, and whether the tradeoff appears practically favorable from the evidence shown.
* `Generalization and Scalability Assessment` MUST state how far the evidence supports extension beyond the tested setup and where generalization or deployment claims remain weak.
* `Hypothesis and Prediction Chain` MUST make explicit whether the experiment directly tests the stated hypothesis or only a proxy consequence.
* `Causal vs Correlational Interpretation` MUST explicitly state what level of causal interpretation is justified by the design and reported controls.
* `Logical Consistency Check` MUST explicitly state what was double-checked and whether any unresolved gap or scope-risk remains.

---

## 14. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
