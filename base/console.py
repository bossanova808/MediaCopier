from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "error": "bold red",
    "success": "bold green"
})

console = Console(record=True, theme=custom_theme)

INDENT = "  "


def log(message, indent: int = 0, style: str = None):
    """
    Indented console.log wrapper for structured output.
    indent=0 top-level (show name, section headers)
    indent=1 show-level (matched path, wanted, will copy)
    indent=2 season-level (episodes added, base files, season folder messages)
    """
    console.log(f"{INDENT * indent}{message}", style=style)
