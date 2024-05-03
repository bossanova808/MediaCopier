from dataclasses import dataclass


@dataclass
class CopyItem:
    file_name: str = None
    file_size: int = None
    source_folder: str = None
    destination_folder: str = None
    source_file: str = None
    destination_file: str = None
    # Below here are extras to help with TV show processing
    wanted_show: str = None
    show_id: int = None
    season: int = None
    episode: int = None
    kodi_playcount = None


