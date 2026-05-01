> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-12

---

# Documentation Guidelines (Specification)

---

## 1. Scope

This document defines **documentation constraints** for all agent-generated content, including READMEs, CHANGELOGs, API docs, and inline comments.

Apply this guideline when the task involves:
* `README.md` or any `README.*` file
* `CHANGELOG.md`
* `.md` files under `/docs` or similar documentation directories
* API documentation (docstrings, OpenAPI/Swagger comments)
* Inline code comments where the task is comments-only

---

## 2. General Principles

* **[MUST]** Define the intended audience (user, developer, or contributor) before writing and maintain a consistent tone.
* **[MUST NOT]** document features that have not been implemented. 
* **[MUST]** Mark planned features explicitly with `(planned)` or `(coming soon)`.
* **[SHOULD]** Adhere to the "Minimal but Complete" principle—omit unnecessary fluff while retaining all essential info.
* **[MUST]** Follow the Single Source of Truth (SSOT) principle; use cross-references instead of duplicating data across files.
* **[MUST]** Include timestamp and authorship metadata at the top of new AGENTS.md suite documents.
* **[SHOULD]** Preserve existing project documentation conventions for non-suite documents, including README, CHANGELOG, and `/docs` files.
* **[SHOULD]** Add timestamp and authorship metadata to non-suite documents only when it fits the local convention or when the task creates a new standalone document.
* **[MUST]** Record AI authorship and date when an AI agent creates a new standalone document or rewrites a document substantially, unless doing so conflicts with the repository's established documentation format.

---

## 3. README

* **[MUST]** Keep the top-level `README.md` focused on: purpose, quickstart, and links to further docs.
* **[SHOULD]** Maintain this section order where applicable:
  1. Project name & one-line description
  2. Prerequisites
  3. Installation
  4. Usage
  5. Configuration
  6. Contributing
  7. License
* **[MUST NOT]** Include internal implementation details—those belong in code comments or `/docs`.

---

## 4. CHANGELOG

* **[MUST]** Follow [Keep a Changelog](https://keepachangelog.com) format.
* **[MUST]** Group entries under: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
* **[MUST]** Every user-facing change must have a CHANGELOG entry.
* **[MUST NOT]** Log internal refactors, test-only changes, or formatting fixes unless they affect behavior.

---

## 5. API Documentation (Docstrings)

* **[MUST]** Provide a docstring for every public function, class, and module.
* **[MUST]** Include Purpose, Parameters, Return Value, and Raised Exceptions in all docstrings.
* **[MUST]** Update docstrings immediately upon implementation changes to prevent "outdated doc" debt.
* **[MUST]** Explicitly identify the agent as the author if the documentation was AI-generated.
* **[MUST]** Specify when the doc is written.

---

## 6. Inline Comments

* **[MUST]** Focus comments on explaining **"Why"** (intent) rather than **"What"** (the code itself).
* **[MUST NOT]** leave commented-out code blocks in the repository; remove them before committing.
* **[MUST]** Use `# TODO:` or `# FIXME:` tags for unresolved documentation/comment issues and include specific context for the next action.
* **[MUST NOT]** Use this rule to justify leaving `TODO`/`FIXME` markers in implementation code at delivery time.

---

## 7. Explicit Prohibitions

* **[MUST NOT]** copy-paste external documentation without proper attribution.
* **[MUST NOT]** leave placeholder text (e.g., `Lorem ipsum`, `TBD`, `...`) in any committed document.
* **[MUST NOT]** document private or internal APIs unless specifically requested by the user.

---

## 8. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

## Appendix


### Appendix A. Examples (Non-Normative)

- timestamp and authorship
```markdown
  # Document Title
  > Last updated: 2025-04-11
  > Author: John Doe
```

- If written or modified by an AI agent, specify the agent explicitly
```markdown
  # Document Title
  > Last updated: 2025-04-11
  > Author: Claude (Anthropic) — reviewed by John Doe
```

- For partial updates (e.g., adding a section), append both date and author inline:
```markdown
  ## New Feature (added: 2025-04-11, author: Claude (Anthropic))
```

- ChangeLog
```markdown
  ## [1.2.0] - 2025-04-11
  ### Added
  * Support for dark mode in the dashboard.
  ### Fixed
  * Resolved crash when uploading files larger than 10MB.
```

- Python docstring (Google style)
```python
  def parse_config(path: str) -> dict:
      """Parse a YAML config file and return it as a dictionary.

      Args:
          path: Absolute or relative path to the YAML file.

      Returns:
          A dictionary representation of the config file.

      Raises:
          FileNotFoundError: If the file does not exist.
          ValueError: If the file is not valid YAML.
      """
```

---

© 2026 Younghoon. All rights reserved.
