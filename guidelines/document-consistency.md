> ### Confidential & Proprietary
>
> **Author:** Younghoon
> **Copyright:** © 2026 Younghoon
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-24

---

# Document Consistency Verification Guidelines (Specification)

---

## 0. Abstract

Defines deterministic rules for verifying internal consistency, cross-document consistency,
and authority-conformance consistency of documents by forcing a structured but compact pipeline:
claim extraction, normalization, indexed grouping, comparison planning, in-group comparison,
inter-group comparison, adjudication, and evidence-backed reporting.

This guideline is not a generic reading guide. It is a comparison and verification guide.

---

## 1. Scope

Applies when the user's primary objective is to validate document consistency, including:

* contradiction detection
* terminology drift detection
* procedure/dependency consistency checking
* example-vs-rule consistency checking
* cross-document rule alignment
* validation against a declared authoritative source

This guideline covers two related but distinct verification tasks:

* `Consistency Detection` — detect and classify inconsistencies within or across the declared source scope
* `Authority-Based Adjudication` — determine which conflicting claim governs when the task requires an authority-conformance or authority-priority verdict

`Consistency Detection` and `Authority-Based Adjudication` MUST NOT be treated as interchangeable tasks.
The second depends on the first, but the first does not always require the second.

This guideline MUST be used together with `guidelines/document-reading.md`.

If the target source is an academic paper, the agent MUST additionally load and apply
`guidelines/paper-reading.md`, but consistency verification obligations in this file
remain active for the verification component.

---

## 2. Entry Conditions

Before comparison, the agent MUST establish:

* `source_scope`
* `consistency_scope` (`INTRA_DOC | CROSS_DOC | AUTHORITY_CONFORMANCE`)
* `authority_order` when the requested outcome requires authority-based adjudication
* `version_scope`
* `unit_of_check`

If scoped comparison cannot be performed because any required item above is missing, the agent MUST emit
`UNCERTAINTY:: BLOCK` and stop.

If the requested outcome requires authority-based adjudication and `authority_order` is missing, the agent MUST emit
`UNCERTAINTY:: BLOCK` and stop.

The agent MUST lock source scope before claim extraction.
The agent MUST NOT compare against undeclared or out-of-scope material.

---

## 3. Required Analysis Pipeline

The agent MUST execute document consistency verification in this order:

1. extract claims from source scope
2. normalize claims into comparison-ready fields
3. emit `CLAIM_INDEX::`
4. partition claims into deterministic groups and define bounded comparisons
5. emit `CONSISTENCY_PLAN::`
6. run in-group comparison
7. run inter-group comparison
8. if the task requires authority-based adjudication, adjudicate findings using `authority_order`
9. emit `CONSISTENCY_FINDINGS::`
10. produce final report

The agent MUST NOT skip normalization, grouping, or comparison planning when performing
consistency verification.
The agent MUST NOT skip adjudication when the requested outcome requires authority-based adjudication.

---

## 4. Claim Extraction and Normalization

The agent MUST treat the following as eligible claim units when present:

* definitions
* normative statements
* procedural steps
* examples and counterexamples
* schema/table entries
* metadata and status labels
* references used as governing links

Each extracted claim MUST include, at minimum:

* claim id
* source location
* a normalized summary suitable for bounded comparison
* modality
* topic
* scope/version when available

The external IR for this step SHOULD remain compact.
The agent SHOULD emit a claim index rather than a full claim dump unless strict audit needs
require fuller payloads.

When the source materially supports it, the agent SHOULD also normalize:

* subject
* predicate
* object
* conditions
* authority basis

The agent MUST preserve traceability from each normalized claim back to source wording.
The agent MUST NOT duplicate full source text in IR when a stable location plus normalized
summary is sufficient for traceability.

---

## 5. Deterministic Grouping

The agent MUST partition claims into deterministic groups before comparison.

Allowed grouping bases:

* topic
* subject
* procedure
* schema
* mixed, if a single basis would lose comparison-critical structure

Grouping MUST be reproducible from the same source scope and ordering.
The agent MUST NOT use ad hoc or opaque grouping labels.

Each group MUST have:

* group id
* label
* member claims

When authority materially governs comparison or adjudication for a group, the agent MUST preserve that basis in a traceable compact form within the comparison plan or related findings.

---

## 6. Comparison Planning

The agent MUST define explicit bounded comparisons before adjudication.

The compact IR for this step MUST identify:

* grouping basis
* in-group checks actually performed
* compared claim pairs or equivalent bounded comparison targets
* inter-group edges used for comparison

Allowed inter-group relation labels:

* `depends_on`
* `example_of`
* `overrides`
* `supports`
* `refines`

The agent MUST include a short basis for each declared check or edge.
The agent MUST NOT perform inter-group comparison without first establishing
the relevant dependency or governance edge in `CONSISTENCY_PLAN::`.

---

## 7. In-Group Comparison

For each group, the agent MUST compare claims that share a comparison axis such as:

* same term under definition
* same subject-predicate pair
* same procedure step or stage
* same status-bearing object
* same rule and its examples

The agent MUST detect and classify at least the following when present:

* `CONTRADICTION`
* `AMBIGUITY`
* `TERM_DRIFT`
* `SCOPE_MISMATCH`
* `STATUS_MISMATCH`
* `EXAMPLE_MISMATCH`

The agent MUST NOT collapse distinct in-group issues into one generic inconsistency record.

---

## 8. Inter-Group Comparison

The agent MUST compare linked groups across explicit dependency or governance edges.

Inter-group comparison MUST be used to verify at least:

* definitions -> rules
* rules -> procedures
* procedures -> examples
* policy -> exception
* schema -> procedure
* authority source -> subordinate source

The agent MUST detect and classify at least the following when present:

* `CONTRADICTION`
* `MISSING_DEPENDENCY`
* `REFERENCE_ERROR`
* `SCOPE_MISMATCH`
* `AUTHORITY_MISMATCH`

The agent MUST NOT perform all-pairs comparison across unrelated groups.
Comparison MUST be bounded by declared checks and edges in `CONSISTENCY_PLAN::`.

---

## 9. Adjudication and Authority

If the task requires authority-based adjudication and two claims conflict, the agent MUST resolve them using declared `authority_order`.

If no authority rule resolves the conflict and the outcome materially affects the final result,
the agent MUST:

* mark the finding as unresolved
* set `needs_human_decision` to `YES`
* use `UNDETERMINABLE` or an equivalent bounded status if required by impact

The lower-priority claim MUST still be reported as inconsistent rather than silently ignored.

---

## 10. Issue Types and Severity

Each finding MUST be classified as exactly one of:

* `CONTRADICTION`
* `AMBIGUITY`
* `MISSING_DEPENDENCY`
* `REFERENCE_ERROR`
* `TERM_DRIFT`
* `SCOPE_MISMATCH`
* `EXAMPLE_MISMATCH`
* `AUTHORITY_MISMATCH`
* `STATUS_MISMATCH`

Each finding MUST also be assigned exactly one severity:

* `CRITICAL`
* `MAJOR`
* `MINOR`

Severity MUST be based on operational impact, not prose preference.

---

## 11. Output Contract

This output contract is the specific final-report contract for document consistency verification.
It supersedes the generic `guidelines/document-reading.md` Section 7 output list for the
consistency-verification component, while the evidence-discipline obligations from
`guidelines/document-reading.md` remain active.

Unless the user requests another format, final output MUST include:

* Verification Boundary
* Claim Group Summary
* In-Group Findings
* Inter-Group Findings
* Unresolved Questions
* Overall Consistency Status

If the task requires authority-based adjudication, final output MUST additionally include:

* Authority Order

Every material finding MUST include:

* finding id
* issue type
* severity
* related claim ids
* explanation
* resolution basis
* whether human decision is required

The output MUST remain traceable back to `CLAIM_INDEX::` and `CONSISTENCY_PLAN::`, which together provide the source-linked evidence path for each finding.

---

## 12. Non-Goals

The agent MUST NOT silently expand this task into:

* internet fact-checking
* style rewriting
* whole-document rewriting
* implementation review
* speculative intent reconstruction without source support

---

## 13. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
