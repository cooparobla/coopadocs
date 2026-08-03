from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Argument:
    name: str
    type_str: str = ""
    default_str: str = ""
    description: str = ""

@dataclass
class Member:
    name: str
    type_str: str = ""
    docstring: str = ""
    default_str: str = ""

@dataclass
class Function:
    name: str
    kind: str  # "function", "method", "constructor", "static_method", "class_method"
    docstring: str = ""  # HTML rendered docstring
    args: List[Argument] = field(default_factory=list)
    return_type: str = "None"
    signature: str = ""  # Pygments HTML highlighted signature
    is_static: bool = False
    is_const: bool = False

@dataclass
class Class:
    name: str
    kind: str  # "python_class", "cpp_class"
    docstring: str = ""  # HTML rendered docstring
    parents: List[str] = field(default_factory=list)
    template_params: List[str] = field(default_factory=list)  # For C++
    methods: List[Function] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)
    file_path: str = ""

@dataclass
class Scope:
    name: str
    kind: str  # "python_module", "cpp_namespace"
    docstring: str = ""  # HTML rendered docstring
    classes: List[Class] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    subscopes: List["Scope"] = field(default_factory=list)
    file_path: str = ""

@dataclass
class Project:
    name: str
    scopes: List[Scope] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)  # ["python", "cpp"]
