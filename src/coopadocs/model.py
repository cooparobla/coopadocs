"""Data models representing parsed programming structures."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Argument:
    """Represents a function or method argument."""

    name: str
    """The name of the argument."""

    type_str: str = ""
    """The type of the argument as a string representation."""

    default_str: str = ""
    """The default value of the argument as a string representation."""

    description: str = ""
    """Description of the argument's purpose and usage."""


@dataclass
class Member:
    """Represents a class attribute or member variable."""

    name: str
    """The name of the member variable."""

    type_str: str = ""
    """The type of the member as a string."""

    docstring: str = ""
    """The documentation string for the member."""

    default_str: str = ""
    """The default value of the member as a string."""


@dataclass
class Function:
    """Represents a function, method, or constructor."""

    name: str
    """The name of the function or method."""

    kind: str
    """The kind of the function (e.g., function, method, constructor, static_method, class_method)."""

    docstring: str = ""
    """HTML rendered docstring describing the function."""

    args: List[Argument] = field(default_factory=list)
    """List of arguments accepted by the function."""

    return_type: str = "None"
    """The return type of the function."""

    signature: str = ""
    """Pygments HTML highlighted signature of the function."""

    is_static: bool = False
    """Flag indicating if the function is a static method."""

    is_const: bool = False
    """Flag indicating if the method is const (for C++)."""

    communicates_with: List[str] = field(default_factory=list)
    """List of other classes this function communicates or interacts with."""


@dataclass
class Class:
    """Represents a class or struct structure."""

    name: str
    """The name of the class."""

    kind: str
    """The kind of the class (e.g., python_class, cpp_class)."""

    docstring: str = ""
    """HTML rendered docstring describing the class."""

    parents: List[str] = field(default_factory=list)
    """List of parent classes this class inherits from."""

    template_params: List[str] = field(default_factory=list)
    """List of template parameters for C++ templates."""

    methods: List[Function] = field(default_factory=list)
    """List of methods defined inside the class."""

    members: List[Member] = field(default_factory=list)
    """List of member variables or attributes defined inside the class."""

    file_path: str = ""
    """Path to the file where the class is defined."""

    communicates_with: List[str] = field(default_factory=list)
    """List of other classes this class communicates or interacts with."""


@dataclass
class Scope:
    """Represents a namespace or python module scope containing classes and functions."""

    name: str
    """The name of the scope."""

    kind: str
    """The kind of the scope (e.g., python_module, cpp_namespace)."""

    docstring: str = ""
    """HTML rendered docstring describing the scope."""

    classes: List[Class] = field(default_factory=list)
    """List of classes defined directly within this scope."""

    functions: List[Function] = field(default_factory=list)
    """List of global functions defined directly within this scope."""

    subscopes: List["Scope"] = field(default_factory=list)
    """List of nested sub-scopes (namespaces or submodules)."""

    file_path: str = ""
    """Path to the file representing this scope."""


@dataclass
class Project:
    """Represents the entire parsed codebase project."""

    name: str
    """The name of the project."""

    scopes: List[Scope] = field(default_factory=list)
    """List of top-level scopes inside the project."""

    languages: List[str] = field(default_factory=list)
    """List of detected programming languages (e.g., Python, C++)."""
