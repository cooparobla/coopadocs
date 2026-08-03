import ast
import markdown
from pathlib import Path
from typing import List, Dict, Tuple, Any

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from coopadocs.model import Scope, Class, Function, Argument, Member

def get_module_name(file_path: Path, repo_path: Path) -> str:
    """Resolve the module name from the file path relative to repo path.

    Args:
        file_path: Absolute path to the python file.
        repo_path: Absolute path to the repository root.

    Returns:
        str: Resolved module name using dot-notation.
    """
    rel_path = file_path.relative_to(repo_path)
    parts = list(rel_path.parts)
    
    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = file_path.stem
        
    if len(parts) > 1 and parts[0] == "src":
        parts = parts[1:]
        
    return ".".join(parts)

def highlight_code(code: str, lang: str) -> str:
    """Highlight code using Pygments and output HTML.

    Args:
        code: Raw source code string.
        lang: Programming language string.

    Returns:
        str: Pygments HTML highlighted code.
    """
    lexer = get_lexer_by_name(lang)
    formatter = HtmlFormatter(nowrap=True)
    return highlight(code, lexer, formatter)

def render_markdown(text: str) -> str:
    """Convert markdown text to HTML with code highlighting support.

    Args:
        text: Raw markdown text string.

    Returns:
        str: HTML rendered string.
    """
    if not text:
        return ""
    # We use extra for markdown tables/attributes and codehilite for pygments integration
    return markdown.markdown(text, extensions=["extra", "codehilite"])

def parse_google_docstring(docstring: str) -> Tuple[str, Dict[str, str], str]:
    """Parse Google-style docstrings into description, parameters, and returns.

    Args:
        docstring: Raw docstring text.

    Returns:
        Tuple[str, Dict[str, str], str]: A tuple containing the clean description,
        a dictionary of parsed parameter descriptions, and the return description.
    """
    if not docstring:
        return "", {}, ""
        
    lines = docstring.split("\n")
    clean_lines = []
    param_desc = {}
    return_desc = ""
    
    current_section = None
    current_param = None
    
    for line in lines:
        stripped = line.strip()
        lower_stripped = stripped.lower()
        
        if lower_stripped in ("args:", "parameters:", "arguments:"):
            current_section = "args"
            continue
        elif lower_stripped in ("returns:", "return:"):
            current_section = "returns"
            continue
        elif lower_stripped in ("raises:", "exceptions:"):
            current_section = "raises"
            # we skip raises in detailed table but keep it in description if needed
            continue
        elif stripped and not line.startswith(" ") and not line.startswith("\t"):
            current_section = None
            
        if current_section == "args":
            if ":" in stripped:
                parts = stripped.split(":", 1)
                name_part = parts[0].strip()
                desc_part = parts[1].strip()
                param_name = name_part.split("(")[0].strip()
                param_desc[param_name] = desc_part
                current_param = param_name
            elif current_param and stripped:
                param_desc[current_param] += " " + stripped
        elif current_section == "returns":
            if return_desc:
                return_desc += " " + stripped
            else:
                return_desc = stripped
        elif current_section is None:
            clean_lines.append(line)
            
    clean_doc = "\n".join(clean_lines).strip()
    return clean_doc, param_desc, return_desc.strip()

def make_python_sig(name: str, args_node: ast.arguments, returns_node: Any) -> str:
    """Build a beautiful highlighted signature using ast.unparse.

    Args:
        name: Name of the function.
        args_node: AST arguments node.
        returns_node: AST return node.

    Returns:
        str: Highlighted HTML signature.
    """
    dummy = ast.FunctionDef(
        name=name,
        args=args_node,
        decorator_list=[],
        returns=returns_node,
        body=[ast.Pass()],
        lineno=1,
        col_offset=0
    )
    ast.fix_missing_locations(dummy)
    sig = ast.unparse(dummy).split("\n")[0]
    if sig.endswith(":"):
        sig = sig[:-1]
    return highlight_code(sig, "python")

def parse_python_file(file_path: Path, repo_path: Path) -> Scope:
    """Parse a single python file and extract its module Scope.

    Args:
        file_path: Path to the Python file.
        repo_path: Path to the repository root directory.

    Returns:
        Scope: The parsed module Scope object.
    """
    module_name = get_module_name(file_path, repo_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    try:
        root_node = ast.parse(content, filename=str(file_path))
    except Exception as e:
        print(f"Error parsing python file {file_path}: {e}")
        return Scope(name=module_name, kind="python_module", file_path=str(file_path))
        
    module_doc = ast.get_docstring(root_node) or ""
    clean_mod_doc, _, _ = parse_google_docstring(module_doc)
    
    scope = Scope(
        name=module_name,
        kind="python_module",
        docstring=render_markdown(clean_mod_doc),
        file_path=str(file_path.relative_to(repo_path))
    )
    
    # Iterate through module children
    for idx, node in enumerate(root_node.body):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node) or ""
            clean_class_doc, class_param_desc, _ = parse_google_docstring(class_doc)
            
            parents = [ast.unparse(base) for base in node.bases]
            
            cls = Class(
                name=node.name,
                kind="python_class",
                docstring=render_markdown(clean_class_doc),
                parents=parents,
                file_path=str(file_path.relative_to(repo_path))
            )
            class_deps = set()
            
            # Find class members and methods
            for c_idx, c_node in enumerate(node.body):
                if isinstance(c_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_doc = ast.get_docstring(c_node) or ""
                    clean_method_doc, m_param_desc, m_return_desc = parse_google_docstring(method_doc)
                    
                    # Merge class-level param description if method is init and parameter is not documented in init
                    if c_node.name == "__init__":
                        for k, v in class_param_desc.items():
                            if k not in m_param_desc:
                                  m_param_desc[k] = v
                                  
                    is_static = any(isinstance(dec, ast.Name) and dec.id == "staticmethod" for dec in c_node.decorator_list)
                    is_class = any(isinstance(dec, ast.Name) and dec.id == "classmethod" for dec in c_node.decorator_list)
                    
                    kind = "method"
                    if c_node.name == "__init__":
                        kind = "constructor"
                    elif is_static:
                        kind = "static_method"
                    elif is_class:
                        kind = "class_method"
                        
                    # Extract args
                    args = []
                    # Positional & keyword args
                    for idx, arg in enumerate(c_node.args.args):
                        arg_name = arg.arg
                        if idx == 0 and not is_static:
                            if arg_name in ("self", "cls"):
                                continue
                        type_str = ast.unparse(arg.annotation) if arg.annotation else ""
                        args.append(Argument(
                            name=arg_name,
                            type_str=type_str,
                            description=m_param_desc.get(arg_name, "")
                        ))
                        
                    # Return type
                    ret_type = ast.unparse(c_node.returns) if c_node.returns else "Any"
                    
                    sig = make_python_sig(c_node.name, c_node.args, c_node.returns)
                    
                    method_deps = set()
                    for child in ast.walk(c_node):
                        if isinstance(child, ast.Name) and child.id and child.id[0].isupper():
                            method_deps.add(child.id)
                    method_communicates = sorted(list(method_deps))
                    for dep in method_communicates:
                        if dep != cls.name:
                            class_deps.add(dep)

                    cls.methods.append(Function(
                        name=c_node.name,
                        kind=kind,
                        docstring=render_markdown(clean_method_doc),
                        args=args,
                        return_type=ret_type,
                        signature=sig,
                        is_static=is_static,
                        communicates_with=method_communicates
                    ))
                    
                elif isinstance(c_node, (ast.Assign, ast.AnnAssign)):
                    # Check for docstring comment directly after attribute assignment
                    attr_doc = ""
                    if c_idx + 1 < len(node.body):
                        next_node = node.body[c_idx + 1]
                        if isinstance(next_node, ast.Expr) and isinstance(next_node.value, ast.Constant) and isinstance(next_node.value.value, str):
                            attr_doc = next_node.value.value.strip()
                            
                    # Extract target name(s)
                    names = []
                    if isinstance(c_node, ast.Assign):
                        for target in c_node.targets:
                            if isinstance(target, ast.Name):
                                names.append(target.id)
                    else:  # AnnAssign
                        if isinstance(c_node.target, ast.Name):
                            names.append(c_node.target.id)
                            
                    type_str = ""
                    if isinstance(c_node, ast.AnnAssign) and c_node.annotation:
                        type_str = ast.unparse(c_node.annotation)
                        
                    default_str = ""
                    if c_node.value:
                        try:
                            default_str = ast.unparse(c_node.value)
                        except Exception:
                            default_str = "..."
                            
                    for name in names:
                        cls.members.append(Member(
                            name=name,
                            type_str=type_str,
                            docstring=render_markdown(attr_doc),
                            default_str=default_str
                        ))
                    
                    for child in ast.walk(c_node):
                        if isinstance(child, ast.Name) and child.id and child.id[0].isupper():
                            class_deps.add(child.id)
            if cls.name in class_deps:
                class_deps.remove(cls.name)
            cls.communicates_with = sorted(list(class_deps))
            scope.classes.append(cls)
            
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_doc = ast.get_docstring(node) or ""
            clean_func_doc, f_param_desc, f_return_desc = parse_google_docstring(func_doc)
            
            # Extract args
            args = []
            for arg in node.args.args:
                arg_name = arg.arg
                type_str = ast.unparse(arg.annotation) if arg.annotation else ""
                args.append(Argument(
                    name=arg_name,
                    type_str=type_str,
                    description=f_param_desc.get(arg_name, "")
                ))
                
            ret_type = ast.unparse(node.returns) if node.returns else "Any"
            sig = make_python_sig(node.name, node.args, node.returns)
            
            func_deps = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id and child.id[0].isupper():
                    func_deps.add(child.id)

            scope.functions.append(Function(
                name=node.name,
                kind="function",
                docstring=render_markdown(clean_func_doc),
                args=args,
                return_type=ret_type,
                signature=sig,
                communicates_with=sorted(list(func_deps))
            ))
            
    return scope
