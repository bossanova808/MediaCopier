from dataclasses import dataclass
from kodipydent import Kodi
from base.console import console
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table


@dataclass
class _Store:
    """
    A global storage class for key things that need to be shared around MediaCopier
    Other modules use: 'from models.store import store' to access the actual instance
    """

    # Pretend mode runs the whole thing but prevents the actual copying of the media
    pretend: bool = False
    # Running this as bossanova808
    bossanova808: bool = False
    # The name to update the library for - 'agogo' or e.g. 'kathrex'
    name: str = None
    # The commans that was called, e.g. update or init
    command: str = None
    # Set to True when mc init <name> --first-run is passed, to force agogo movies config generation
    agogo_first_run: bool = False
    # Update TV or Movies or (default) both?
    update_tv: bool = True
    update_movies: bool = True
    # The root path of the mediacopier tool, usually /home/user/mediacopier
    mediacopier_path: str = None
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
    # What file extension qualify as videos?
    video_file_extensions = [".avi", ".mkv", ".mp4", ".divx", ".mov", ".flv", ".wmv"]
    # The wanted media gets loaded into these
    # For TV - one version with all the subscription info, another one just a list of the shows
    # For movies this is a list of unwanted movies (i.e. seen or not wanted)
    tv_subscriptions: list = None
    tv_subscriptions_basic_show_list: list = None
    movies_available: list = None
    unwanted_movies: list = None
    original_show_list: dict = None
    output_show_list: dict = None
    shows_not_matched_to_library: list = None
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
    # Optional speed limiting to protect SLC cache on QLC drives (e.g. Crucial X9).
    # Set copy_speed_limit_mbps and copy_speed_limit_threshold_gb in the subscriber's paths YAML.
    # active_speed_limit_mbps is set at runtime by check_disk_space based on transfer size vs threshold.
    copy_speed_limit_mbps: int = None
    copy_speed_limit_threshold_gb: int = None
    active_speed_limit_mbps: int = None
    # Set to True during an update run if any movies were selected for copying
    movies_were_selected: bool = False
    # Reduce calls to Kodi for speed's sake
    playcount_cache = {}
    # Cache of interactive answers (TV show subscriptions, movie selections) for resuming incomplete runs
    pending_answers_cache: dict = None
    # Store the sesssion results here (set in load_media_library_paths)
    session_archive_path: str = ""

    # Manual overrides for show name -> folder name mappings that cannot be derived automatically.
    # Manual overrides only for cases that cannot be derived automatically.
    # ": " -> " - " and trailing "? (" -> "! (" are handled by kodi_name_to_folder_name().
    map_show_name_to_folder = {
        'The Traitors (2022)': 'The Traitors (UK) (2022)',
    }
    map_folder_to_show_name = {value: key for key, value in map_show_name_to_folder.items()}

    @staticmethod
    def kodi_name_to_folder_name(kodi_name: str) -> str:
        """
        Derive the likely filesystem folder name from a Kodi show name.
        Applies standard automatic transformations that cover the majority of
        cases where Kodi and the filesystem disagree:
          - ": " -> " - "  (subtitle separator)
          - "? (" -> "! ("  (trailing question mark before year becomes exclamation)
        """
        result = kodi_name.replace(": ", " - ")
        result = result.replace("? (", "! (")
        return result

    @staticmethod
    def folder_name_to_kodi_name(folder_name: str) -> str:
        """
        Inverse of kodi_name_to_folder_name — derive the likely Kodi show name from a
        filesystem folder name. Used when matching folder names back to Kodi labels.
          - " - " -> ": "  (subtitle separator)
          - "! (" -> "? ("  (exclamation before year becomes question mark)
          - trailing "!" -> "?"  (handles year-stripped names like "Would I Lie to You!")
        """
        result = folder_name.replace(" - ", ": ")
        result = result.replace("! (", "? (")
        if result.endswith("!"):
            result = result[:-1] + "?"
        return result

    def set_media_limits(self, limit_to):
        """
        Limit the media types we're handling
        :param limit_to: 'tv' or 'movies'
        """
        match limit_to:
            case 'tv':
                console.log("[red]Only TV will be updated[/red]")
                self.update_movies = False
            case 'movies':
                console.log("[red]Only Movies will be updated[/red]")
                self.update_tv = False
            case _:
                console.log("[green]Both TV & Movies will be updated[/green]")

    # noinspection PyUnusedLocal
    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """
        Overload the console logging of this Store to how we like it
        """
        yield f"[b]Store:[/b]"
        my_table = Table("Attribute", "Value")
        my_table.add_row("Name", f"[dodger_blue1]{self.name}")
        my_table.add_row("Pretend Mode",
                         "[green]ON (no changes will be made)[/green]" if self.pretend else "[red]OFF (changes [i]will[/i] be made!)[/red]")
        if self.bossanova808:
            my_table.add_row("Bossanova808", "[red]Bossanova808 mode is ON")
        my_table.add_row("Update TV?", "[green]Yes[/green]" if self.update_tv else "[red]No[/red]")
        my_table.add_row("Update Movies?", "[green]Yes[/green]" if self.update_movies else "[red]No[/red]")
        my_table.add_section()
        my_table.add_row("TV Input Paths", str(self.tv_input_paths))
        my_table.add_row("Movie Input Paths", str(self.movie_input_paths))
        my_table.add_section()
        my_table.add_row("TV Output Path", str(self.tv_output_path))
        my_table.add_row("Movie Output Path", str(self.movie_output_path))
        my_table.add_row("Session Archive Path", str(self.session_archive_path))
        if self.copy_speed_limit_mbps and self.copy_speed_limit_threshold_gb:
            my_table.add_section()
            my_table.add_row("[red]Copy Speed Limit[/red]",
                             f"[yellow]{self.copy_speed_limit_mbps} MB/s[/yellow] (applies when transfer exceeds [yellow]{self.copy_speed_limit_threshold_gb} GB[/yellow])")
        elif self.copy_speed_limit_mbps or self.copy_speed_limit_threshold_gb:
            my_table.add_section()
            my_table.add_row("[red]Copy Speed Limit[/red]", "[red]Misconfigured — both copy_speed_limit_mbps and copy_speed_limit_threshold_gb must be set[/red]")
        if 'agogo' in store.name:
            my_table.add_section()
            my_table.add_row("Kodi IP", self.kodi_ip)
            my_table.add_row("Kodi JSONRPC Port", str(self.kodi_jsonrpc_port))
            my_table.add_row("Kodi username", self.kodi_username)
            my_table.add_row("Kodi password", self.kodi_password)
        yield my_table


store = _Store()
