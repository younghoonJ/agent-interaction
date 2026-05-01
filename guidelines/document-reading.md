> ### Confidential & Proprietary
>
> **Author:** Younghoon
> **Copyright:** © 2026 Younghoon
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-23

---

# Document Reading Guidelines (Specification)

---

## 1. Scope

Applies when the user asks the agent to read existing documents and produce a derived output, including:

* summaries
* fact extraction
* question answering from documents
* comparison between documents
* policy/rule extraction

This guideline is for reading/analysis tasks, not authoring new documentation.
For documentation authoring, use `guidelines/docs.md`.

Paper extension rule:

* When the target document is an academic paper, the agent **[MUST]** additionally load and apply `guidelines/paper-reading.md`.
* When `guidelines/paper-reading.md` applies, its output contract and reading-strategy requirements supersede this file's generic defaults where they are more specific.
* Academic-paper analysis **[MUST NOT]** assume the whole paper belongs to one exclusive evidence type if different claims are supported in different ways.

---

## 2. Entry Conditions

* **[MUST]** identify the reading objective before analysis (e.g., summarize, extract, compare, validate).
* **[MUST]** classify missing objective/scope as uncertainty and follow `guidelines/uncertainty.md`.
* **[MUST]** establish document boundary: path/source, version/snapshot, and relevant range if provided.
* **[MUST]** perform a lightweight document-type pre-scan before synthesis (e.g., title/abstract/venue/reference cues) to determine whether paper extension applies.
* The pre-scan **[MUST]** remain classification-only: read-only, bounded to minimal metadata, and non-synthesizing.
* If pre-scan is inconclusive, the agent **[MUST]** mark provisional classification as inference and continue with declaration (`UNCERTAINTY:: INFER`) or stop (`UNCERTAINTY:: BLOCK`) based on impact.
* **[MUST]** lock source scope before synthesis (explicit source list and snapshot time).
* **[MUST NOT]** introduce facts from outside the locked source scope unless the user explicitly requests external augmentation.
* For read-only tasks, the agent **[MUST NOT]** perform unrelated code/file modifications.
* If paper status is discovered only during execution, the agent **[MUST]** follow the late guideline discovery protocol in `AGENTS.md` Section 3.1.2 before continuing.

---

## 3. Evidence Discipline

* **[MUST]** separate observed facts from interpretation.
* **[MUST]** attach traceable evidence location (file/section/line where available) to key claims.
* **[MUST]** use a deterministic evidence locator schema. Preferred order: source path or identifier → page/section → figure/table/equation label → line span if available.
* **[MUST NOT]** state conclusions without source support.
* **[MUST]** mark uncertain interpretation using `UNCERTAINTY::` (`INFER` or `BLOCK`) before using it.
* **[MUST]** enforce claim-evidence pairing for every material statement in final output.
* **[MUST]** ensure each key finding has at least one explicit source anchor.
* **[MUST NOT]** report as fact any claim that is not directly locatable in the provided source scope.
* **[MUST NOT]** fabricate evidence locations; if exact location cannot be confirmed, the agent MUST mark the claim as unverified or unresolved.
* **[MUST NOT]** strengthen the epistemic status of source language during summarization (for example, `suggests` to `demonstrates`).

---

## 4. Fact vs Inference Contract

* **[MUST]** output facts and inferences in separate sections.
* **[MUST]** label each inference with confidence (`LOW | MED | HIGH`) and rationale.
* **[MUST]** escalate unresolved high-impact interpretation to `UNCERTAINTY:: BLOCK` and stop.
* **[MUST NOT]** present `INFER` content as confirmed fact.

---

## 5. Multi-Document Handling

* **[MUST]** use deterministic source ordering (explicit user order, otherwise lexical path order).
* **[MUST]** detect and report conflicts between sources.
* **[MUST]** apply an explicit precedence rule when conflicts exist:
  1. User-specified source priority
  2. Newer timestamp/version
  3. Canonical/primary source over derived summaries
* **[MUST]** stop and ask when conflict remains unresolved after precedence.

---

## 6. Safety and Privacy

* **[MUST]** follow `guidelines/security.md`.
* **[MUST NOT]** reprint secrets, credentials, or private personal data from source documents.
* **[MUST]** redact sensitive values when reference is necessary.

---

## 7. Output Contract

Unless user asks for a different schema, output MUST include:

* Objective
* Key Facts
* Inferences (if any, with confidence)
* Open Questions
* Evidence Map (claim -> source location)
* Risks/Limitations

For academic paper tasks, the agent **[MUST]** also ensure the output enables the reader to recover:

* the core claim or thesis
* the supporting evidence or reasoning path for each major claim
* the evidence mode active for each major claim when the paper mixes proof, experiment, simulation, numerical analysis, or statistical support
* the role of key definitions, assumptions, and theorem-like statements
* an efficient reading order or strategy for validating the paper's main argument
* the difference between author claim, verified support, and unresolved validation status

When major claims rely on empirical superiority over prior work, the agent **[MUST]** additionally preserve:

* what improvement is claimed
* what extra resources, constraints, or privileges were required to obtain it
* whether the comparison appears fair and cost-aware
* how well the evidence supports generalization and scaling beyond the tested setup

When major claims rely on scientific hypothesis-testing or scientific inference, the agent **[MUST]** additionally preserve:

* how the paper maps hypothesis to observable prediction
* whether the study design justifies causal or only correlational interpretation
* what confound, validity, or measurement risks remain
* what alternative explanations are still live after the reported evidence

When major claims rely on theoretical argument, the agent **[MUST]** additionally ensure the output preserves:

* the logical dependency chain from assumptions to main conclusion
* scope conditions and quantifier-sensitive phrasing
* explicit double-check results for logical consistency or unresolved support gaps

---

## 8. Determinism and Performance

* **[MUST]** keep extraction and ordering deterministic.
* **[SHOULD]** use section-first filtering for large documents before deep reading.
* **[MUST]** avoid skipping relevant sections without declaring criteria.
* **[MUST]** keep evidence locator formatting consistent within a run and across comparable sources.
* **[MUST]** run a final evidence-coverage check before delivery (no unanchored key claims).

---

## 9. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
