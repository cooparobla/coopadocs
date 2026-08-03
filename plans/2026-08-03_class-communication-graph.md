# Implementation Plan: Class Communication Graph Generation and Visualization

**Date**: 2026-08-03
**Status**: Draft

This plan details the implementation steps to generate a visual graph depicting class communication and dependencies (method calls, instantiations) in a codebase, rendering it directly inside the `coopadocs` static HTML website.

---

## Introduction

Understanding how classes communicate throughout different tracks of a CLI tool (e.g. `PackageManager` calling `StateManager`, `DesktopIntegration`, `ShellIntegration` in `sww`) is highly valuable. 

To achieve this without executing client code, `coopadocs` will perform static analysis during parsing, build a graph representation, and visualize it using Mermaid.js embedded dynamically into the generated HTML.

---

## Implementation Phases

### Phase 1: Extend Data Models
Extend `coopadocs.model` to capture edge data:
- Add a `communicates_with` list to `Class` and `Function` dataclasses in `src/coopadocs/model.py`.

### Phase 2: Python AST Parser Updates
Extend `src/coopadocs/parser_python.py`:
- In the class parser, traverse the AST bodies of all class methods.
- Scan for `ast.Call` nodes to find:
  - Class instantiation calls (e.g. constructor name matches a class name parsed in the codebase).
  - Method calls on objects that can be associated with classes.
- Populate `communicates_with` attributes on classes accordingly.

### Phase 3: C++ Doxygen Parser Updates
Extend `src/coopadocs/parser_cpp.py`:
- Configure the temporary `Doxyfile` to capture references:
  ```ini
  REFERENCES_RELATION = YES
  REFERENCED_BY_RELATION = YES
  ```
- Parse `<references>` tags from Doxygen XML output to identify calls between functions and classes, and map them into the `communicates_with` field.

### Phase 4: Mermaid.js Graph Generator
Implement graph assembly in `src/coopadocs/generator.py`:
- Build a helper that converts class communication lists into standard Mermaid class diagram/flowchart syntax:
  ```mermaid
  classDiagram
      ClassA --> ClassB : uses
  ```
- Inject a script tag to load the Mermaid.js rendering engine in templates.
- Update `index.html` (overview page) to include a project-wide class interaction graph.
- Update `class.html` (class template) to render localized class interaction flowcharts.

---

## Testing and Validation

### Automated Validation
- Add unit tests in `tests/test_coopadocs.py` that parse mock Python files with class dependency relations and check that `Class.communicates_with` is populated correctly.

### Manual Validation
- Run `coopadocs build` in the `sww` repository.
- Verify that `sww/.docs/index.html` renders a correct communication graph of `sww`'s components (e.g. showing `PackageManager` connecting to `StateManager`, `DesktopIntegration`, etc.).
- Inspect individual class HTML files (e.g. `class_PackageManager.html`) to ensure localized interaction graphs render successfully.
