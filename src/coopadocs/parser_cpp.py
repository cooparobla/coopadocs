import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional

from coopadocs.model import Scope, Class, Function, Argument, Member
from coopadocs.parser_python import highlight_code, render_markdown

def xml_to_text(node: Optional[ET.Element]) -> str:
    """Recursively converts doxygen XML description node to markdown text."""
    if node is None:
        return ""
    
    parts = []
    if node.text:
        parts.append(node.text)
        
    for child in node:
        tag = child.tag
        if tag == "para":
            parts.append("\n\n" + xml_to_text(child).strip() + "\n\n")
        elif tag in ("computeroutput", "programlisting"):
            parts.append("`" + xml_to_text(child) + "`")
        elif tag == "bold":
            parts.append("**" + xml_to_text(child) + "**")
        elif tag == "emphasis":
            parts.append("*" + xml_to_text(child) + "*")
        elif tag == "ref":
            parts.append(xml_to_text(child))
        elif tag in ("parameterlist", "simplesect"):
            # skip in main text description as we parse these separately
            pass
        else:
            parts.append(xml_to_text(child))
            
        if child.tail:
            parts.append(child.tail)
            
    text = "".join(parts)
    # Clean up double newlines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()

def parse_doxygen_docs(member_def: ET.Element) -> Tuple[str, Dict[str, str], str]:
    """Extracts description, params, and return details from doxygen member def."""
    brief = member_def.find("briefdescription")
    detail = member_def.find("detaileddescription")
    
    brief_text = xml_to_text(brief)
    detail_text = xml_to_text(detail)
    
    # Combine brief and detail descriptions
    desc_parts = []
    if brief_text:
        desc_parts.append(brief_text)
    if detail_text:
        desc_parts.append(detail_text)
    full_desc = "\n\n".join(desc_parts).strip()
    
    # Parse parameter list
    param_desc = {}
    if detail is not None:
        for plist in detail.findall(".//parameterlist"):
            if plist.attrib.get("kind") == "param":
                for item in plist.findall("parameteritem"):
                    names = [n.text for n in item.findall(".//parametername") if n.text]
                    desc_para = item.find(".//parameterdescription/para")
                    desc = xml_to_text(desc_para).strip() if desc_para is not None else ""
                    for name in names:
                        param_desc[name] = desc
                        
    # Parse return list
    return_desc = ""
    if detail is not None:
        for simplesect in detail.findall(".//simplesect"):
            if simplesect.attrib.get("kind") == "return":
                desc_para = simplesect.find("para")
                if desc_para is not None:
                    return_desc = xml_to_text(desc_para).strip()
                    
    return full_desc, param_desc, return_desc

def clean_cpp_definition(definition: str, class_name: Optional[str]) -> str:
    """Strips class names or namespace scopes from definition to show clean method names."""
    if not definition:
        return ""
    if class_name and class_name + "::" in definition:
        definition = definition.replace(class_name + "::", "")
    return definition

def parse_cpp_member(member_def: ET.Element, class_name: Optional[str] = None) -> Tuple[Optional[Function], Optional[Member]]:
    """Parses a doxygen C++ memberdef and returns either a Function or a Member variable."""
    kind = member_def.attrib.get("kind")
    name = member_def.find("name").text
    
    prot = member_def.attrib.get("prot", "public")
    if prot != "public":
        # We only document public members/methods for C++ APIs
        return None, None
        
    doc_text, param_desc, return_desc = parse_doxygen_docs(member_def)
    
    if kind in ("function", "signal", "slot"):
        ret_type_node = member_def.find("type")
        ret_type = xml_to_text(ret_type_node).strip() if ret_type_node is not None else "void"
        
        args_str = member_def.find("argsstring").text or ""
        definition_node = member_def.find("definition")
        definition = xml_to_text(definition_node).strip() if definition_node is not None else ""
        definition = clean_cpp_definition(definition, class_name)
        
        # Build arguments list
        args = []
        for p in member_def.findall("param"):
            p_type_node = p.find("type")
            p_type = xml_to_text(p_type_node).strip() if p_type_node is not None else ""
            p_name_node = p.find("declname")
            p_name = p_name_node.text.strip() if p_name_node is not None else ""
            
            p_defval_node = p.find("defval")
            p_defval = xml_to_text(p_defval_node).strip() if p_defval_node is not None else ""
            
            if p_name:
                args.append(Argument(
                    name=p_name,
                    type_str=p_type,
                    default_str=p_defval,
                    description=param_desc.get(p_name, "")
                ))
                
        # Build signature
        temp_params = []
        tpl = member_def.find("templateparamlist")
        if tpl is not None:
            for p in tpl.findall("param"):
                ptype = xml_to_text(p.find("type")).strip()
                pname_node = p.find("declname")
                pname = pname_node.text.strip() if pname_node is not None else ""
                temp_params.append(f"{ptype} {pname}".strip())
                
        sig = ""
        if temp_params:
            sig += f"template <{', '.join(temp_params)}>\n"
        if definition:
            sig += f"{definition}{args_str}"
        else:
            sig += f"{ret_type} {name}{args_str}"
            
        is_static = member_def.attrib.get("static") == "yes"
        is_const = member_def.attrib.get("const") == "yes"
        
        func_kind = "method"
        if class_name and name == class_name:
            func_kind = "constructor"
            
        return Function(
            name=name,
            kind=func_kind,
            docstring=render_markdown(doc_text),
            args=args,
            return_type=ret_type,
            signature=highlight_code(sig, "cpp"),
            is_static=is_static,
            is_const=is_const
        ), None
        
    elif kind in ("variable", "typedef", "enum"):
        type_node = member_def.find("type")
        type_str = xml_to_text(type_node).strip() if type_node is not None else ""
        if kind == "enum":
            type_str = "enum"
            
        initializer_node = member_def.find("initializer")
        default_str = xml_to_text(initializer_node).strip() if initializer_node is not None else ""
        if default_str.startswith("="):
            default_str = default_str[1:].strip()
            
        return None, Member(
            name=name,
            type_str=type_str,
            docstring=render_markdown(doc_text),
            default_str=default_str
        )
        
    return None, None

def parse_cpp_xml(xml_dir: Path) -> List[Scope]:
    """Parses all C++ XML compounds generated by Doxygen and converts them to Scope trees."""
    index_path = xml_dir / "index.xml"
    if not index_path.exists():
        return []
        
    tree = ET.parse(index_path)
    root = tree.getroot()
    
    compounds = root.findall("compound")
    
    # Store raw mapping and build scopes
    scopes_map: Dict[str, Scope] = {}
    classes_map: Dict[str, Class] = {}
    
    # Pass 1: Parse namespaces, classes and record parents
    for compound in compounds:
        refid = compound.attrib.get("refid")
        kind = compound.attrib.get("kind")
        name = compound.find("name").text
        
        compound_file = xml_dir / f"{refid}.xml"
        if not compound_file.exists():
            continue
            
        comp_tree = ET.parse(compound_file)
        comp_root = comp_tree.getroot()
        compounddef = comp_root.find("compounddef")
        if compounddef is None:
            continue
            
        doc_text, _, _ = parse_doxygen_docs(compounddef)
        
        location = compounddef.find("location")
        file_path = location.attrib.get("file", "") if location is not None else ""
        
        if kind == "namespace":
            scopes_map[refid] = Scope(
                name=name,
                kind="cpp_namespace",
                docstring=render_markdown(doc_text),
                file_path=file_path
            )
        elif kind in ("class", "struct"):
            parents = [base.text for base in compounddef.findall("basecompoundref") if base.text]
            
            # Template parameters
            temp_params = []
            tpl = compounddef.find("templateparamlist")
            if tpl is not None:
                for p in tpl.findall("param"):
                    ptype = xml_to_text(p.find("type")).strip()
                    pname_node = p.find("declname")
                    pname = pname_node.text.strip() if pname_node is not None else ""
                    temp_params.append(f"{ptype} {pname}".strip())
                    
            cls = Class(
                name=name,
                kind="cpp_class",
                docstring=render_markdown(doc_text),
                parents=parents,
                template_params=temp_params,
                file_path=file_path
            )
            
            # Parse members/methods inside class
            for section in compounddef.findall("sectiondef"):
                for memberdef in section.findall("memberdef"):
                    func, memb = parse_cpp_member(memberdef, class_name=name)
                    if func:
                        cls.methods.append(func)
                    if memb:
                        cls.members.append(memb)
                        
            classes_map[refid] = cls
            
    # Pass 2: Map child structures to their parent scopes or resolve namespace tree
    # XML index lists nested namespaces and members inside compounds
    root_scopes: List[Scope] = []
    
    for compound in compounds:
        refid = compound.attrib.get("refid")
        kind = compound.attrib.get("kind")
        
        compound_file = xml_dir / f"{refid}.xml"
        if not compound_file.exists():
            continue
            
        comp_tree = ET.parse(compound_file)
        comp_root = comp_tree.getroot()
        compounddef = comp_root.find("compounddef")
        if compounddef is None:
            continue
            
        if kind == "namespace":
            current_scope = scopes_map.get(refid)
            if not current_scope:
                continue
                
            # Add child namespaces
            for innerns in compounddef.findall("innernamespace"):
                inner_refid = innerns.attrib.get("refid")
                inner_scope = scopes_map.get(inner_refid)
                if inner_scope and inner_scope not in current_scope.subscopes:
                    current_scope.subscopes.append(inner_scope)
                    
            # Add classes declared in this namespace
            for innerclass in compounddef.findall("innerclass"):
                class_refid = innerclass.attrib.get("refid")
                inner_class = classes_map.get(class_refid)
                if inner_class:
                    # Clean up nested namespace prefix from class name for local rendering
                    clean_name = inner_class.name
                    if "::" in clean_name:
                        clean_name = clean_name.split("::")[-1]
                    inner_class.name = clean_name
                    if inner_class not in current_scope.classes:
                        current_scope.classes.append(inner_class)
                        
            # Parse namespace-level global functions / variables
            for section in compounddef.findall("sectiondef"):
                for memberdef in section.findall("memberdef"):
                    func, memb = parse_cpp_member(memberdef)
                    if func and func not in current_scope.functions:
                        current_scope.functions.append(func)
                        
    # Find root namespaces (those that are not child subscopes of any other namespace)
    non_root_refids = set()
    for ns_refid, ns_scope in scopes_map.items():
        for sub in ns_scope.subscopes:
            for ref, scope in scopes_map.items():
                if scope == sub:
                    non_root_refids.add(ref)
                    
    for ns_refid, ns_scope in scopes_map.items():
        if ns_refid not in non_root_refids:
            root_scopes.append(ns_scope)
            
    # Fallback: if classes exist that are not under any namespace, place them in a global Scope
    global_classes = []
    for cls_refid, cls in classes_map.items():
        # Check if this class is mapped inside any namespace scope
        is_in_ns = False
        for ns in scopes_map.values():
            if cls in ns.classes:
                is_in_ns = True
                break
        if not is_in_ns:
            global_classes.append(cls)
            
    if global_classes:
        global_scope = Scope(
            name="Global Namespace",
            kind="cpp_namespace",
            docstring="<p>Global C++ symbols.</p>",
            classes=global_classes
        )
        root_scopes.append(global_scope)
        
    return root_scopes

def load_coopadocs_config(repo_path: Path) -> dict:
    config_files = [".coopadocs", ".coopadocs.yaml", ".coopadocs.yml"]
    for cf in config_files:
        cf_path = repo_path / cf
        if cf_path.exists():
            try:
                import yaml
                with open(cf_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to parse config {cf}: {e}")
    return {}

def parse_cpp(repo_path: Path) -> List[Scope]:
    """Orchestrates C++ parsing using Doxygen and returns parsed scopes."""
    if not shutil.which("doxygen"):
        raise FileNotFoundError(
            "Doxygen binary not found in PATH. Please install Doxygen to generate C++ documentation."
        )
        
    config = load_coopadocs_config(repo_path)
    includes = config.get("include", [])
    if isinstance(includes, str):
        includes = [includes]
        
    input_paths = []
    if includes:
        for inc in includes:
            inc_path = repo_path / inc
            if inc_path.exists():
                input_paths.append(f"\"{inc_path}\"")
    else:
        input_paths.append(f"\"{repo_path}\"")
        
    input_str = " ".join(input_paths)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        doxyfile_path = temp_path / "Doxyfile"
        xml_out_dir = temp_path / "xml"
        
        # Write temporary Doxyfile
        with open(doxyfile_path, "w", encoding="utf-8") as f:
            f.write(f"PROJECT_NAME = \"Coopadocs C++\"\n")
            f.write(f"INPUT = {input_str}\n")
            f.write(f"OUTPUT_DIRECTORY = \"{temp_path}\"\n")
            f.write("GENERATE_XML = YES\n")
            f.write("GENERATE_HTML = NO\n")
            f.write("GENERATE_LATEX = NO\n")
            f.write("RECURSIVE = YES\n")
            f.write("EXTRACT_ALL = YES\n")
            f.write("EXTRACT_PRIVATE = YES\n")
            f.write("EXTRACT_STATIC = YES\n")
            f.write("QUIET = YES\n")
            f.write("WARNINGS = NO\n")
            f.write("FILE_PATTERNS = *.h *.hpp *.cpp *.cc *.cxx *.c\n")
            
        print(f"Running doxygen parser in {temp_path}...")
        try:
            subprocess.run(
                ["doxygen", str(doxyfile_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"Doxygen compilation failed: {e}")
            return []
            
        return parse_cpp_xml(xml_out_dir)

import shutil
