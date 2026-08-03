# Project Implementation Plan: coopadocs Setup

This plan outlines the design and implementation of `coopadocs`, a Python and C++ documentation generator CLI. The tool will parse repositories, extract code structure and documentation, and generate a uniform, premium-designed static documentation website. It also covers integration into the `sww` package manager, adding dependency support to `sww`, and cleanup of deprecated documentation packages from `sww`.

## 1. Goal Description
Create a CLI tool named `coopadocs` that takes a path to a repository, automatically detects Python and/or C++ files, parses them (using AST for Python and Doxygen for C++), maps them into a unified intermediate documentation model, and outputs a highly polished, responsive static HTML site with uniform branding, layout, search, and styling. Make it compatible with the `sww` package manager as a `python_uv` package, and clean up deprecated `sphinx`, `doxygen`, and `mkdocs` packages from `sww`.

## 2. Implementation Phases

### Phase 1: Initialize Project and CLI
- Initialize a Python library/binary project with `uv` in `/home/coopa/git/coopadocs`.
- Configure dependencies in `pyproject.toml`:
  - `click` for CLI
  - `jinja2` for HTML templates
  - `markdown` for docstring conversion
  - `pygments` for code highlighting
- Implement `cli.py` to parse arguments and coordinate detection, parsing, and page rendering.

### Phase 2: SWW Compatibility and Package Dependency System
- Modify `sww/src/sww/config.py` to add `dependencies` list to `PackageConfig`.
- Modify `sww/src/sww/manager.py` to recursively resolve and install package dependencies first.
- Remove `doxygen`, `sphinx`, and `mkdocs` from `/home/coopa/git/sww/manifest.yaml`.
- Remove directories `/home/coopa/git/sww/packages/sphinx` and `/home/coopa/git/sww/packages/mkdocs`.
- Create `/home/coopa/git/sww/packages/coopadocs/package.yaml` pointing to `/home/coopa/git/coopadocs` with `strategy: "python_uv"`, declaring `doxygen` as a dependency.
- Add `coopadocs` to `manifest.yaml` in `sww`.

### Phase 3: Python and C++ Parsers
- Implement `parser_python.py` using standard `ast` module to build the unified doc model from `.py` files.
- Implement `parser_cpp.py` which:
  - Writes a temporary `Doxyfile` to parse C++ files in the source tree and generate XML.
  - Runs `doxygen`.
  - Parses the generated XML via `ElementTree` to build the unified doc model.
  - Cleans up the temporary files.

### Phase 4: Generator and Premium UI Templates
- Create HTML templates (`base.html`, `sidebar.html`, details) and sleek CSS/JS assets (dark mode, glassmorphism, responsive sidebar, client-side search indexing).
- Implement `generator.py` to render the unified model into output static HTML files.

### Phase 5: Verification and Testing
- Add unit tests for detection, Python parsing, C++ XML parsing, and generation.
- Manually run `coopadocs` on `libcoopa` and visually verify the generated docs.

## 3. Testing and Validation
- **Automated Tests**: Run `uv run pytest` to execute unit tests.
- **Manual Verification**: Run `coopadocs /home/coopa/git/libcoopa --output docs_build`, inspect the generated files, and test interactive UI features (search, theme toggle, responsiveness).
