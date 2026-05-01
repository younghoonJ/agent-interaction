> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-19

---

# JavaScript / TypeScript / React Guidelines (Specification)

---

## 1. Scope

This document defines **JavaScript/TypeScript-specific constraints** for AI-generated code.

It extends:

* AGENTS.md (execution model)
* code-style.md (global constraints)

---

## 2. Environment

* **[MUST]** Use TypeScript (strict mode)
* **[MUST]** Target ES2020+ or project-defined standard
* **[SHOULD]** Use modern tooling (Vite, Next.js, or equivalent)

---

## 3. Determinism & Execution

* **[MUST]** Avoid non-deterministic behavior
* **[MUST]** Do not rely on implicit object key ordering
* **[SHOULD]** Ensure reproducible outputs for identical inputs

---

## 4. Type System

* **[MUST]** Use TypeScript types for all public APIs
* **[MUST]** Avoid `any` unless explicitly justified
* **[MUST]** Define interfaces or types for all props and data structures
* **[MUST]** Ensure type consistency across component boundaries

---

## 5. No Hallucination

* **[MUST]** Do not assume undefined APIs, props, or fields
* **[MUST]** Do not invent component props or backend responses
* **[MUST]** Missing type or API definitions MUST trigger clarification

---

## 6. Imports

* **[MUST]** Use explicit imports
* **[MUST]** Avoid wildcard imports
* **[MUST]** Use deterministic import paths (no implicit resolution)

---

## 7. Code Structure

* **[MUST]** Use functional components only
* **[MUST]** Avoid class components
* **[SHOULD]** Keep files ≤ ~300 lines
* **[MUST]** Avoid deep nesting (>3 levels)
* **[MUST]** Prefer `async/await` over callbacks

---

## 8. React Component Design

* **[MUST]** Define explicit prop types
* **[MUST]** Keep components focused and single-purpose
* **[SHOULD]** Use composition over inheritance
* **[MUST]** Avoid unnecessary state lifting
* **[SHOULD]** Extract reusable logic into custom hooks

---

## 9. State Management

* **[SHOULD]** Keep state local when possible
* **[MUST]** Avoid global mutable state unless explicitly required
* **[SHOULD]** Use established patterns (Context, Zustand, Redux Toolkit)

---

## 10. Side Effects

* **[MUST]** Make side effects explicit
* **[MUST]** Handle all async operations safely
* **[MUST]** Define correct dependency arrays in `useEffect`
* **[SHOULD]** Isolate side effects from pure logic

---

## 11. Error Handling

* **[MUST]** Handle all Promise rejections
* **[MUST]** Never leave `.catch()` empty
* **[MUST]** Provide meaningful error states in UI
* **[SHOULD]** Use error boundaries for React components

---

## 12. Performance

* **[SHOULD]** Use `useMemo` / `useCallback` only when necessary
* **[MUST]** Avoid premature optimization
* **[SHOULD]** Use lazy loading for large components

---

## 13. Styling

* **[SHOULD]** Follow consistent styling system (CSS Modules, Tailwind, etc.)
* **[MUST]** Avoid inline styles unless necessary
* **[MUST]** Ensure accessibility (semantic HTML, ARIA)

---

## 14. Testing

* **[SHOULD]** Use React Testing Library
* **[MUST]** Test behavior, not implementation
* **[SHOULD]** Mock external dependencies
* **[MUST]** If task includes numerical/ML transform logic in JS/TS, load and follow `guidelines/testing-ml.md` in addition to core testing.

---

## 15. Anti-Patterns

The following are strictly prohibited:

* **[MUST NOT]** usage of `any` without justification
* **[MUST NOT]** implicit prop assumptions
* **[MUST NOT]** unhandled async errors
* **[MUST NOT]** deeply nested component logic

---

## 16. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
