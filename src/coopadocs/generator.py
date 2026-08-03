import json
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any
from jinja2 import Environment, FileSystemLoader

from coopadocs.model import Project, Scope, Class, Function

def clean_html_summary(html_text: str) -> str:
    """Strips HTML tags to create a clean text summary snippet."""
    if not html_text:
        return ""
    clean = re.sub(r'<[^>]+>', '', html_text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > 120:
        return clean[:117] + "..."
    return clean

def sanitize_id(name: str) -> str:
    """Sanitizes names to create safe HTML IDs and file names."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

def decorate_scopes_and_classes(scopes: List[Scope]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Flattens and decorates scopes and classes with presentation-specific helper fields.
    Returns:
        (flat_scopes, flat_classes, search_items)
    """
    flat_scopes = []
    flat_classes = []
    search_items = []
    
    def recurse(scope_list: List[Scope]):
        for s in scope_list:
            sc_id = sanitize_id(s.name)
            decorated_scope = {
                "id": sc_id,
                "name": s.name,
                "kind": s.kind,
                "kind_label": "Module" if s.kind == "python_module" else "Namespace",
                "lang_badge": "PY" if s.kind == "python_module" else "C++",
                "docstring": s.docstring,
                "docstring_summary": clean_html_summary(s.docstring),
                "url": f"scope_{sc_id}.html",
                "file_path": s.file_path,
                "classes": [], # populated below
                "functions": [], # populated below
                "subscopes": [], # populated below
                "raw_scope": s  # reference to original object
            }
            flat_scopes.append(decorated_scope)
            
            # Index scope in search
            search_items.append({
                "name": s.name,
                "kind": decorated_scope["kind_label"],
                "url": decorated_scope["url"],
                "desc": decorated_scope["docstring_summary"]
            })
            
            # Index global functions
            for fn in s.functions:
                decorated_fn = {
                    "name": fn.name,
                    "kind": fn.kind,
                    "docstring": fn.docstring,
                    "args": fn.args,
                    "return_type": fn.return_type,
                    "signature": fn.signature,
                    "is_static": fn.is_static
                }
                decorated_scope["functions"].append(decorated_fn)
                search_items.append({
                    "name": f"{s.name}.{fn.name}" if s.kind == "python_module" else f"{s.name}::{fn.name}",
                    "kind": "Function",
                    "url": f"{decorated_scope['url']}#func_{fn.name}",
                    "desc": clean_html_summary(fn.docstring)
                })
                
            # Parse classes in scope
            for c in s.classes:
                cl_id = sanitize_id(c.name)
                decorated_class = {
                    "id": cl_id,
                    "name": c.name,
                    "kind": c.kind,
                    "lang_badge": "PY" if c.kind == "python_class" else "C++",
                    "docstring": c.docstring,
                    "docstring_summary": clean_html_summary(c.docstring),
                    "url": f"class_{cl_id}.html",
                    "parents": c.parents,
                    "template_params": c.template_params,
                    "file_path": c.file_path,
                    "methods": [],
                    "members": c.members,
                    "raw_class": c
                }
                flat_classes.append(decorated_class)
                decorated_scope["classes"].append(decorated_class)
                
                # Index class in search
                search_items.append({
                    "name": c.name,
                    "kind": "Class",
                    "url": decorated_class["url"],
                    "desc": decorated_class["docstring_summary"]
                })
                
                # Index methods
                for fn in c.methods:
                    decorated_m = {
                        "name": fn.name,
                        "kind": fn.kind,
                        "docstring": fn.docstring,
                        "args": fn.args,
                        "return_type": fn.return_type,
                        "signature": fn.signature,
                        "is_static": fn.is_static,
                        "is_const": fn.is_const
                    }
                    decorated_class["methods"].append(decorated_m)
                    
                    anchor_prefix = "ctor" if fn.kind == "constructor" else "method"
                    search_items.append({
                        "name": f"{c.name}.{fn.name}" if c.kind == "python_class" else f"{c.name}::{fn.name}",
                        "kind": fn.kind.replace("_", " ").capitalize(),
                        "url": f"{decorated_class['url']}#{anchor_prefix}_{fn.name}",
                        "desc": clean_html_summary(fn.docstring)
                    })
            
            # Recursive pass for nested namespaces / submodules
            if s.subscopes:
                recurse(s.subscopes)
                # Map subscope decos
                for sub in s.subscopes:
                    sub_deco = next((item for item in flat_scopes if item["raw_scope"] == sub), None)
                    if sub_deco:
                        decorated_scope["subscopes"].append(sub_deco)
                        
    recurse(scopes)
    return flat_scopes, flat_classes, search_items

def generate_docs(project: Project, output_dir: Path) -> None:
    """Renders the HTML documentation site into the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate templates folder
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates folder not found at {templates_dir}")
        
    # Copy static assets
    shutil.copy2(templates_dir / "style.css", output_dir / "style.css")
    shutil.copy2(templates_dir / "search.js", output_dir / "search.js")
    
    # Flatten and decorate
    flat_scopes, flat_classes, search_items = decorate_scopes_and_classes(project.scopes)
    
    # Save search index
    with open(output_dir / "search_index.json", "w", encoding="utf-8") as f:
        json.dump(search_items, f, indent=2)
        
    # Setup Jinja2 Environment
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    base_context = {
        "project_name": project.name,
        "languages": project.languages,
        "all_scopes": flat_scopes,
        "all_classes": flat_classes
    }
    
    # 1. Render index.html landing page
    index_template = env.get_template("index.html")
    index_context = {
        **base_context,
        "current_title": "Overview",
        "active_id": "index"
    }
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_template.render(index_context))
        
    # 2. Render each Scope page
    scope_template = env.get_template("module.html")
    for sc in flat_scopes:
        scope_context = {
            **base_context,
            "current_title": sc["name"],
            "active_id": f"scope_{sc['id']}",
            "scope": sc
        }
        with open(output_dir / sc["url"], "w", encoding="utf-8") as f:
            f.write(scope_template.render(scope_context))
            
    # 3. Render each Class page
    class_template = env.get_template("class.html")
    for cl in flat_classes:
        class_context = {
            **base_context,
            "current_title": cl["name"],
            "active_id": f"class_{cl['id']}",
            "cls": cl
        }
        with open(output_dir / cl["url"], "w", encoding="utf-8") as f:
            f.write(class_template.render(class_context))
            
    print(f"Documentation site built successfully at: file://{output_dir.resolve()}/index.html")
