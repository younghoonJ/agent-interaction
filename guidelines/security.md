> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-18

---

# Security Guidelines (Specification)

---

## 1. Scope

This document defines **security constraints for all AI-generated actions and code**.

It applies across:

* code generation
* system design
* orchestration
* tool usage

---

## 2. Core Principle

> The agent MUST minimize risk exposure by default.

Security is treated as a **hard constraint**, not a recommendation.

---

## 3. Data Security

### 3.1 Sensitive Information

The agent **MUST NOT**:

* expose secrets (API keys, tokens, credentials)
* hardcode sensitive environment values
* log sensitive data
* infer or reconstruct hidden credentials

---

### 3.2 Environment Variables

* **[MUST]** use environment variables for all secrets
* **[MUST]** never print or log env values
* **[SHOULD]** validate presence of required env variables early

---

## 4. Code Execution Security

### 4.1 Shell Execution

* **[MUST NOT]** execute arbitrary shell commands without explicit requirement
* **[MUST]** validate command safety before execution
* **[MUST]** avoid dynamic command string construction

---

### 4.2 Remote Execution

* **[MUST NOT]** access external systems without explicit instruction
* **[MUST]** avoid implicit network requests
* **[MUST]** treat external reads as bounded snapshots (source + timestamp recorded) before using them in execution
* **[SHOULD]** prefer local computation when possible

---

## 5. Input Validation

* **[MUST]** validate all external inputs
* **[MUST]** assume inputs are untrusted by default
* **[MUST]** sanitize user-provided data before use
* **[SHOULD]** enforce schema validation where possible

---

## 6. Dependency Security

* **[MUST]** avoid unknown or unverified dependencies
* **[SHOULD]** prefer well-maintained libraries
* **[MUST]** pin versions for reproducibility in critical systems

---

## 7. Hallucination as Security Risk

Hallucination is treated as a **security vulnerability**.

The agent **MUST NOT**:

* invent APIs
* assume external system behavior
* fabricate data structures
* guess missing backend contracts

Missing information **MUST trigger clarification**.

---

## 8. Data Leakage Prevention

* **[MUST]** avoid embedding sensitive data in outputs
* **[MUST]** prevent cross-context leakage between tasks
* **[MUST]** isolate unrelated task contexts
* **[SHOULD]** minimize retained state across operations

---

## 9. Tool Usage Security

* **[MUST]** only use tools explicitly required for the task
* **[MUST]** validate tool inputs before execution
* **[MUST NOT]** chain tools with unverified intermediate outputs

---

## 10. Logging & Observability

* **[MUST]** logs must exclude sensitive data
* **[SHOULD]** include structured logs for debugging
* **[MUST NOT]** log secrets, tokens, or user-sensitive input

---

## 11. Isolation Principle

* **[MUST]** separate logic, execution, and I/O layers
* **[MUST]** avoid shared mutable global state
* **[SHOULD]** enforce boundary isolation between modules

---

## 12. Failure Mode Security

* **[MUST]** fail securely (no partial unsafe execution)
* **[MUST]** on error, stop execution instead of fallback guessing
* **[SHOULD]** surface safe error messages only

Refer to: `guidelines/failure-recovery.md`

---

## 13. Prohibited Actions

The following are strictly forbidden:

* **[MUST NOT]** expose secrets or credentials
* **[MUST NOT]** execute unverified shell commands
* **[MUST NOT]** perform unauthorized network access
* **[MUST NOT]** assume missing security context
* **[MUST NOT]** bypass validation steps

---

## 14. Compliance

Any violation of **MUST rules** is considered a **security failure**, not a style issue.


---

© 2026 Younghoon. All rights reserved.
