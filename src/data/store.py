from dataclasses import dataclass
from kodipydent import Kodi
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table


@dataclass
class _Store:
    """
    A global storage class for key things that need to be shared around MediaCopier
    Other modules use: 'from data.store import store' to access the actual instance
    """

    # Pretend mode runs the whole thing but prevents the actual copying of the media
    pretend: bool = False
    # The name to update the library for - 'agogo' or e.g. 'kathrex'
    name: str = None
    # Update TV or Movies or (default) both?
    update_tv: bool = True
    update_movies: bool = True
    # The lists of paths that contain TV shows or movies
    tv_input_paths: list = None
    movie_input_paths: list = None
    # The output paths for this subscriber
    tv_output_path = None
    movie_output_path = None
    # Kodi details (only for agogo updates)
    kodi_ip = None
    kodi_jsonrpc_port = None
    kodi_username = None
    kodi_password = None
    # The Kodi connection, once established
    kodi: Kodi = None
    # The wanted media gets loaded into these
    # For TV - one version with all the subscription info, another one just a list of the shows
    # For movies this is a list of unwanted movies (i.e. seen or not wanted)
    tv_subscriptions: list = None
    tv_subscriptions_basic_show_list: list = None
    movies_available: list = None
    unwanted_movies: list = None
    original_show_list: dict = None
    output_show_list: dict = None
    # Copying things
    tv_needed_space_bytes = 0
    tv_needed_space_gb = 0.0
    tv_available_space_bytes = 0
    tv_available_space_gb = 0.0
    movies_needed_space_bytes = 0
    movies_needed_space_gb = 0.0
    movies_available_space_bytes = 0
    movies_available_space_gb = 0.0
    total_needed_space_bytes = 0
    total_needed_space_gb = 0.0

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """
        Overload the console logging of this Store to how we like it
        """
        yield f"[b]Store:[/b]"
        my_table = Table("Attribute", "Value")
        my_table.add_row("Name", "[blue]" + self.name)
        my_table.add_row("Pretend Mode",
                         "[green]ON (no changes will be made)[/green]" if self.pretend else "[red]OFF (changes [i]will[/i] be made!)[/red]")
        my_table.add_row("Update TV?", "[green]Yes[/green]" if self.update_tv else "[red]No[/red]")
        my_table.add_row("Update Movies?", "[green]Yes[/green]" if self.update_movies else "[red]No[/red]")
        my_table.add_section()
        my_table.add_row("TV Input Paths", str(self.tv_input_paths))
        my_table.add_row("Movie Input Paths", str(self.movie_input_paths))
        my_table.add_section()
        my_table.add_row("TV Output Path", str(self.tv_output_path))
        my_table.add_row("Movie Output Path", str(self.movie_output_path))
        if store.name == 'agogo':
            my_table.add_section()
            my_table.add_row("Kodi IP", self.kodi_ip)
            my_table.add_row("Kodi JSONRPC Port", str(self.kodi_jsonrpc_port))
            my_table.add_row("Kodi username", self.kodi_username)
            my_table.add_row("Kodi password", self.kodi_password)
        yield my_table


store = _Store()
