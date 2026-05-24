import os
import re

from base.console import console, log
from models.store import store
from mediacopier.init import do_init
from mediacopier.update import do_update


def do_agogo(kids=False):
    """
    Run an on-the-fly init for the special 'user' agogo (or agogo_kids), using a live Kodi instance to work out:
    - all unwatched tv
    - new movies since the last update

    ...then, call 'update' based on this on-the-fly config
    """

    if store.update_tv:

        if not kids:
            console.rule(f'[green]Agogo[/green] - copy unwatched TV & selected new movies')
        else:
            console.rule(f'[green]Agogo (KIDS!)[/green] - copy unwatched TV & selected new movies')

        console.log("First, an one-the-fly [green]init[/green] for the user [dodger_blue1]agogo")
        console.log("Then, an [green]update[/green] with the resulting dynamic configuration for [dodger_blue1]agogo")

        # First we need to get our list of unwatched material from Kodi
        first_unwatched_episodes = []

        filter_dict = {
            "field": "playcount",
            "operator": "is",
            "value": "0"
        }

        properties_list = [
            "title",
            "season",
            "episode",
            "playcount",
            "file",
            "year",
        ]

        console.log("")
        missing_folders = []
        unwatched_log = []
        with console.status('Getting unwatched episodes list from Kodi\n'):

            shows_with_unwatched = store.kodi.VideoLibrary.GetTVShows(filter=filter_dict, properties=properties_list)
            # console.print(shows_with_unwatched)

            for show in shows_with_unwatched['result']['tvshows']:
                # console.log(f"Show [{show['title']}] Year: [{show['year']}]")

                # Shows are in Showname (Year) folders, but may also have a country
                # E.g. Showname -> stored in solder Showname (Showyear)
                # Doc (US) -> Doc (US) (2025)
                # Blah (1997) -> Blah (1997)
                # Therefore we must handle the occasional shows with the disambiguating year already at the end of the title

                # (General case) - no year at end of the show, so we add it to get the show folder from the name
                if not re.search(r'\(\d{4}\)$', show['title']):
                    folder = f"{show['title']} ({show['year']})"
                # Show already has the year at the end
                else:
                    folder = show['title']

                # console.log(f"Folder: [{folder}]")
                folder_exists = False
                for path in store.tv_input_paths:
                    folders = os.listdir(path)
                    auto_folder = store.kodi_name_to_folder_name(folder)
                    if auto_folder in folders:
                        folder = auto_folder
                        folder_exists = True
                        break
                    mapped_folder = store.map_show_name_to_folder.get(folder, folder)
                    if mapped_folder in folders:
                        folder = mapped_folder
                        folder_exists = True
                        break

                if not folder_exists:
                    log(f"Folder [{folder}] not found in tv_input_paths — skipping. A mapping in store.py or metadata correction is needed.", indent=1, style="error")
                    missing_folders.append(folder)
                    continue

                filter_dict = {"and": [
                    {
                        "field": "playcount",
                        "operator": "is",
                        "value": "0"
                    },
                    {
                        "field": "season",
                        "operator": "greaterthan",
                        "value": "0"
                    }
                ]}

                json_sort = {
                    "order": "ascending",
                    "method": "episode"
                }
                properties_list = [
                    "title",
                    "season",
                    "episode",
                ]
                unwatched_episodes = store.kodi.VideoLibrary.GetEpisodes(tvshowid=show["tvshowid"], season=None, filter=filter_dict, properties=properties_list, sort=json_sort)['result']['episodes']
                # console.log(unwatched_episodes)

                if unwatched_episodes:
                    first_ep = unwatched_episodes[0]
                    unwatched_log.append(f"[green]{folder}[/green] -> first unwatched [yellow]S{first_ep['season']:02d}E{first_ep['episode']:02d}[/yellow]")
                    first_unwatched_episodes.append({
                        "kodi": show["title"],
                        "showId": show["tvshowid"],
                        "season": first_ep["season"],
                        "episode": first_ep["episode"],
                        "folder": folder
                    })

        first_unwatched_episodes = sorted(first_unwatched_episodes, key=lambda k: k['kodi'])
        for line in sorted(unwatched_log):
            log(line, indent=0)
        console.log(f"Kodi reports [yellow]{len(first_unwatched_episodes)}[/yellow] shows with unwatched episodes.", style="warning")
        if missing_folders:
            console.log(f"[red]{len(missing_folders)} show folder(s) not found in tv_input_paths — these were skipped:[/red]", style="danger")
            for mf in sorted(missing_folders):
                log(f"{mf}", indent=1, style="danger")

        # Now create on-the-fly config for name 'agogo' based on the list of unwatched episodes
        do_init(first_unwatched_episodes)

    # Now, run a normal library update based on this on-the-fly config
    do_update()

    # clean up the on-the-go config files
    if store.update_tv:
        console.rule("Cleaning Up agogo files...")
        console.log("Removing agogo on-the-fly tv config")
        try:
            os.remove(f"{store.mediacopier_path}/config/Subscribers/config.{store.name}.tv.txt")
        except Exception:
            console.log(f"Error deleting on-the-fly tv config file - please manually delete {store.mediacopier_path}/config/Subscribers/config.{store.name}.tv.txt", style="danger")
