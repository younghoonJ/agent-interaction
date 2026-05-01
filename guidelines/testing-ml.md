> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-19

---

# Testing & Verification Guidelines (ML / Numerical Extension)

---

## 1. Scope

This document extends `guidelines/testing.md` for numerical/ML operator and graph-transform tasks.

It MUST be loaded in addition to core testing rules when the task includes:

* operator implementation or optimization
* quantization/fusion/layout transformation
* tensor shape or memory-layout transformation
* graph rewrite or compiler pass affecting numeric behavior

---

## 2. Numerical Parity

* **[MUST]** verify output parity against a golden reference implementation (e.g., NumPy/PyTorch baseline).
* **[MUST]** use `np.allclose` or `torch.allclose` (or equivalent deterministic comparator).
* **[SHOULD]** define `atol`/`rtol` explicitly by precision target (FP32, FP16, INT8).
* **[MAY]** add cosine similarity as supplementary metric for high-dimensional tensors.

---

## 3. Structural & Shape Integrity

* **[MUST]** verify tensor shape invariants after transforms.
* **[MUST]** assert memory layout consistency when layout-sensitive optimization is applied (e.g., NCHW/NHWC).
* **[MUST NOT]** leave dangling nodes or broken edges in transformed graph topology.

---

## 4. Edge Case Matrix

* **[MUST]** include min/max supported input sizes.
* **[MUST]** verify NaN/Inf propagation rules when numerically applicable.
* **[MUST]** validate failure behavior for invalid dtype/shape/input-type combinations.

---

## 5. Reporting Requirements

Per run or test batch, report at minimum:

* reference baseline used
* comparison metric(s) and threshold(s)
* pass/fail summary
* observed max deviation (when applicable)

---

## 6. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
