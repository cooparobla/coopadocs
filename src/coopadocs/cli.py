import click
import sys
from pathlib import Path

from coopadocs.detector import scan_repo
from coopadocs.parser_python import parse_python_file
from coopadocs.parser_cpp import parse_cpp
from coopadocs.generator import generate_docs
from coopadocs.model import Project

@click.group()
def main():
    """
    Uniform Python and C++ Documentation Generator CLI.
    """
    pass

@main.command(name="build")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option(
    "-o", "--output", 
    type=click.Path(file_okay=False, writable=True, path_type=Path), 
    help="Output directory (defaults to <repo_path>/.docs)"
)
def build(repo_path: Path, output: Path):
    """Generate uniform API documentation for Python and C++ files.

    Args:
        repo_path: Path to the repository directory to scan.
        output: Custom output directory for the built documentation.
    """
    repo_path = repo_path.resolve()
    
    # Defaults output path to <repo_path>/.docs
    if not output:
        output_dir = repo_path / ".docs"
    else:
        output_dir = output.resolve()
        
    click.echo(f"Scanning repository at: {repo_path}")
    python_files, cpp_files = scan_repo(repo_path)
    
    if not python_files and not cpp_files:
        click.echo("Error: No Python or C++ source files detected.", err=True)
        sys.exit(1)
        
    project = Project(
        name=repo_path.name,
        scopes=[],
        languages=[]
    )
    
    # Process Python files
    if python_files:
        click.echo(f"Found {len(python_files)} Python source files. Parsing...")
        project.languages.append("Python")
        for f in python_files:
            scope = parse_python_file(f, repo_path)
            project.scopes.append(scope)
            
    # Process C++ files
    if cpp_files:
        click.echo(f"Found {len(cpp_files)} C++ source files. Parsing via Doxygen...")
        project.languages.append("C++")
        try:
            cpp_scopes = parse_cpp(repo_path)
            project.scopes.extend(cpp_scopes)
        except FileNotFoundError as e:
            click.echo(f"Warning: {e} C++ documentation generation will be skipped.", err=True)
        except Exception as e:
            click.echo(f"Error parsing C++ files: {e}", err=True)
            
    # Sort scopes alphabetically for clean sidebar navigation
    project.scopes.sort(key=lambda s: s.name.lower())
    
    # Generate HTML documentation
    click.echo(f"Generating static site at: {output_dir}")
    try:
        generate_docs(project, output_dir)
        click.echo("Build successful!")
    except Exception as e:
        click.echo(f"Error generating documentation: {e}", err=True)
        sys.exit(1)

@main.command(name="show")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option(
    "-o", "--output", 
    type=click.Path(file_okay=False, writable=True, path_type=Path), 
    help="Output directory (defaults to <repo_path>/.docs)"
)
def show(repo_path: Path, output: Path):
    """Open the generated documentation in Chrome.

    Args:
        repo_path: Path to the repository directory to locate documentation.
        output: Custom output directory where documentation was built.
    """
    repo_path = repo_path.resolve()
    
    # Defaults output path to <repo_path>/.docs
    if not output:
        output_dir = repo_path / ".docs"
    else:
        output_dir = output.resolve()
        
    index_html = output_dir / "index.html"
    if not index_html.exists():
        click.echo(f"Error: Documentation not found at {index_html}. Run 'coopadocs build' first.", err=True)
        sys.exit(1)
        
    url = index_html.as_uri()
    click.echo(f"Opening {url} in Chrome...")
    
    import webbrowser
    # Try to launch with chrome browser
    try:
        browser = None
        for name in ['google-chrome', 'chrome', 'chromium']:
            try:
                browser = webbrowser.get(name)
                break
            except webbrowser.Error:
                continue
        if browser:
            browser.open(url)
        else:
            webbrowser.open(url)
    except Exception as e:
        click.echo(f"Failed to open browser specifically: {e}. Attempting default browser...", err=True)
        try:
            webbrowser.open(url)
        except Exception:
            pass

if __name__ == "__main__":
    main()
