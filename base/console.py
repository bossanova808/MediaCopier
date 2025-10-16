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
