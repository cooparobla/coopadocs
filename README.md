# Coopadocs

**Coopadocs** is a uniform, static API documentation generator for projects containing Python and C++ source code. It scans your repository, parses structures from both languages, and builds a premium, fully searchable responsive static HTML website for your codebase's API.

---

## Features

- **Dual-Language Support**: Scans and aggregates Python modules and C++ namespaces into a unified API catalog.
- **Python AST Parsing**: Extracts classes, functions, decorators, attributes, and constructors directly from the Abstract Syntax Tree (no runtime imports needed).
- **C++ Doxygen Integration**: Automates Doxygen execution to extract namespaces, templates, classes, and public members from C++ source files.
- **Searchable static site**: Bundles client-side search indexing and navigation sidebar for easy codebase exploration.
- **Configuration-driven**: Filter directories and customize paths using a simple configuration file.

---

## Installation

To install `coopadocs` locally during development:

```bash
# Clone the repository
git clone <repo_url>
cd coopadocs

# Install using pip in editable mode
pip install -e .

# Or using uv (recommended)
uv pip install -e .
```

### System Requirements
* **Python**: `>= 3.12`
* **Doxygen**: Required for C++ parsing (must be installed and available in your system `PATH`).
  * *Ubuntu/Debian:* `sudo apt-get install doxygen`
  * *macOS:* `brew install doxygen`

---

## CLI Usage & Example Commands

`coopadocs` exposes two main command-line operations:

### 1. Build Documentation: `coopadocs build`
Scan the codebase, extract documentation comments, and compile the static HTML website.

```bash
# Build documentation for the current directory (outputs to ./.docs by default)
coopadocs build

# Build documentation for a target repository
coopadocs build /path/to/my_project

# Build and write output to a custom location
coopadocs build /path/to/my_project -o /path/to/output_dir
```

### 2. View Documentation: `coopadocs show`
Open the generated static website in your web browser (attempts Google Chrome, falling back to default browser).

```bash
# Open default documentation (./.docs/index.html)
coopadocs show

# Open documentation for a target repository
coopadocs show /path/to/my_project

# Open documentation from a custom build path
coopadocs show /path/to/my_project -o /path/to/output_dir
```

---

## Configuration (`.coopadocs`)

Configure the generator by adding a `.coopadocs`, `.coopadocs.yaml`, or `.coopadocs.yml` file to the root of your target repository:

```yaml
# Specify directory paths or source files to include in the scan
include:
  - src
  - include/my_project
```

### Default Exclusions
Directories containing build artifacts, environments, or version control details are ignored automatically:
` .git`, `.venv`, `venv`, `build`, `dist`, `__pycache__`, `node_modules`, `.idea`, `.vscode`, `html`, `latex`, `xml`

---

## Style Formatting Guidelines

### Python Style Guidelines

Python files are parsed using AST. The parser supports Google-Style docstrings and Markdown rendering for the description blocks.

#### 1. Module-Level Docstring
Place module-level documentation at the very top of a `.py` file before imports:
```python
"""
This is a module-level docstring describing the overall module responsibilities.
"""
import sys
```

#### 2. Class & Constructor Docstring
Place class docstrings directly below the class definition. You can document the parameters under the `Args:` section.
* **Auto-merging feature**: If a parameter in the class-level `Args:` section is omitted from the `__init__` constructor docstring, it will be automatically merged into the constructor's parameters list.
```python
class DatabaseConnection:
    """ Manages connections to the database.

    Args:
        host (str): Database host address.
        port (int): Port to connect to.
    """
    def __init__(self, host: str, port: int = 5432):
        self.host = host
```

#### 3. Functions & Methods
Functions and methods parse descriptions, parameters, returns, and raises sections (case-insensitive headers).
* **Self/Cls removal**: First parameters like `self` and `cls` are automatically ignored in the parameter list.
* **Parameters**: Under `Args:`, `Parameters:`, or `Arguments:` list parameters in the format `name: description` or `name (type): description`. Multiline parameter descriptions are supported as long as they are indented under the parameter.
* **Returns**: Under `Returns:` or `Return:` document the return value.
* **Raises**: Under `Raises:` or `Exceptions:` document errors that might be thrown.
```python
def query_data(sql: str, timeout: int = 30) -> list:
    """Executes a SQL query against the connected database.

    Args:
        sql: The SQL string to be executed.
        timeout (int): Seconds to wait before throwing a timeout exception.
            Supports multiline description lines as long as they
            remain indented.

    Returns:
        list: A list of dicts representing database rows.

    Raises:
        DatabaseError: If connection fails or query syntax is invalid.
    """
    pass
```

#### 4. Member / Class Attributes
Document class-level fields and attributes by adding a string literal directly after their assignment:
```python
class AppConfig:
    max_retries: int = 3
    """The maximum number of connection attempts before failing."""
    
    debug_mode: bool = False
    """Toggle verbose debug logging across the application."""
```

#### 5. Method Decorators
- `@staticmethod`: Methods decorated with `@staticmethod` are documented as `static_method`.
- `@classmethod`: Methods decorated with `@classmethod` are documented as `class_method`.

---

### C++ Style Guidelines

C++ code is analyzed through Doxygen. Markdown syntax inside brief and detailed descriptions is fully supported.

#### 1. Comments Syntax
Write comments using standard Doxygen structures:
```cpp
/**
 * Javadoc-style documentation block.
 */
```
*Or:*
```cpp
/// Triple-slash line comments.
/// This style is also parsed.
```

#### 2. Doxygen Tags
Use tags to structure function details:
* `@brief <text>` (or `\brief`): Summary snippet of the symbol.
* `@param <name> <description>` (or `\param`): Document parameters.
* `@return <description>` (or `\return`): Document return values/types.

```cpp
/**
 * @brief Performs a fast Fourier transform on raw signal.
 * 
 * @param signal Vector of float values representing input signal.
 * @param filter_noise Boolean to filter high-frequency noise.
 * @return std::vector<float> The processed signal values.
 */
std::vector<float> process_signal(const std::vector<float>& signal, bool filter_noise = true);
```

#### 3. Visibility Restrictions
* **Public Interface only**: Only declarations marked as **`public`** inside classes/structs or globally in namespaces are exported to the documentation. Protected or private members/methods are automatically skipped to keep the API documentation clean.

#### 4. Advanced Language Features
- **Namespaces**: Symbols are nested under their respective namespaces (e.g. `namespace project::core { ... }`).
- **Templates**: Template signatures and type constraints are parsed and shown (e.g. `template <typename T> class Stack`).
- **Const & Static specifiers**: Methods declared with `const` or `static` keywords are labeled as such in the documentation website.
- **Default Arguments**: Extracted and rendered alongside parameter names in the method signature.
- **Members, Typedefs & Enums**: Public fields, typedef aliases, and enumerated values are parsed, including any associated comments.