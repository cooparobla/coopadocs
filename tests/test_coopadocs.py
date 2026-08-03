import ast
import tempfile
from pathlib import Path

from coopadocs.detector import scan_repo
from coopadocs.parser_python import parse_python_file, get_module_name, parse_google_docstring

def test_detector():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mock files
        (temp_path / "src").mkdir()
        (temp_path / "src" / "main.py").write_text("print('hello')")
        (temp_path / "include").mkdir()
        (temp_path / "include" / "vector.h").write_text("class Vector {};")
        (temp_path / ".git").mkdir()
        (temp_path / ".git" / "config").write_text("")
        
        py_files, cpp_files = scan_repo(temp_path)
        
        assert len(py_files) == 1
        assert py_files[0].name == "main.py"
        assert len(cpp_files) == 1
        assert cpp_files[0].name == "vector.h"

def test_module_name_resolver():
    repo = Path("/home/user/project")
    file1 = Path("/home/user/project/src/coopadocs/cli.py")
    file2 = Path("/home/user/project/bar.py")
    
    assert get_module_name(file1, repo) == "coopadocs.cli"
    assert get_module_name(file2, repo) == "bar"

def test_google_docstring_parser():
    doc = """
    A sample class docstring.
    
    Args:
        arg1: First parameter.
        arg2: Second parameter
            with multiline description.
            
    Returns:
        True if success.
    """
    clean_doc, params, returns = parse_google_docstring(doc)
    assert "A sample class docstring." in clean_doc
    assert params["arg1"] == "First parameter."
    assert "Second parameter" in params["arg2"]
    assert "multiline description" in params["arg2"]
    assert returns == "True if success."

def test_python_ast_parser():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        py_file = temp_path / "sample.py"
        py_file.write_text('''
"""Module level doc."""

class Target:
    """Class level doc.
    
    Args:
        x: An integer.
    """
    def __init__(self, x: int):
        self.x = x
        
    def get_x(self) -> int:
        """Returns x.
        
        Returns:
            The integer value.
        """
        return self.x
''')
        scope = parse_python_file(py_file, temp_path)
        assert scope.name == "sample"
        assert "Module level doc." in scope.docstring
        
        assert len(scope.classes) == 1
        cls = scope.classes[0]
        assert cls.name == "Target"
        assert "Class level doc." in cls.docstring
        
        assert len(cls.methods) == 2
        init_m = next(m for m in cls.methods if m.name == "__init__")
        assert init_m.kind == "constructor"
        assert init_m.args[0].name == "x"
        assert init_m.args[0].description == "An integer."
        
        get_m = next(m for m in cls.methods if m.name == "get_x")
        assert get_m.kind == "method"
        assert get_m.return_type == "int"

def test_cli_commands(monkeypatch):
    from click.testing import CliRunner
    from coopadocs.cli import main
    import tempfile
    from pathlib import Path
    
    runner = CliRunner()
    
    # Test without command prints help and exits with 2 (missing command)
    res = runner.invoke(main)
    assert res.exit_code == 2
    assert "build" in res.output
    assert "show" in res.output
    
    # Test --help exits with 0
    res_help = runner.invoke(main, ["--help"])
    assert res_help.exit_code == 0
    assert "build" in res_help.output
    
    # Test show command when docs don't exist
    with tempfile.TemporaryDirectory() as temp_dir:
        res = runner.invoke(main, ["show", temp_dir])
        assert res.exit_code != 0
        assert "Error: Documentation not found" in res.output
        
        # Test build and show
        temp_path = Path(temp_dir)
        (temp_path / "sample.py").write_text("def f(): pass")
        
        # Build docs
        res_build = runner.invoke(main, ["build", temp_dir])
        assert res_build.exit_code == 0
        assert "Build successful!" in res_build.output
        
        # Show docs
        opened_url = None
        def mock_open(url):
            nonlocal opened_url
            opened_url = url
            return True
            
        import webbrowser
        monkeypatch.setattr(webbrowser, "open", mock_open)
        monkeypatch.setattr(webbrowser, "get", lambda name: None)
        
        res_show = runner.invoke(main, ["show", temp_dir])
        assert res_show.exit_code == 0
        assert "Opening" in res_show.output
        assert opened_url is not None
        assert "index.html" in opened_url

def test_coopadocs_config():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directories
        (temp_path / "included_dir").mkdir()
        (temp_path / "excluded_dir").mkdir()
        
        # Create files
        (temp_path / "included_dir" / "file1.py").write_text("def f(): pass")
        (temp_path / "excluded_dir" / "file2.py").write_text("def g(): pass")
        
        # Write config
        (temp_path / ".coopadocs").write_text("include:\n  - included_dir\n")
        
        py_files, cpp_files = scan_repo(temp_path)
        
        assert len(py_files) == 1
        assert py_files[0].name == "file1.py"
