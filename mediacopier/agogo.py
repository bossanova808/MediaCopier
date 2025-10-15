import os
import re

from base.console import console
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
        first_unwatched_episodes = {}

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
        with console.status('Getting unwatched episodes list from Kodi\n'):

            shows_with_unwatched = store.kodi.VideoLibrary.GetTVShows(filter=filter_dict, properties=properties_list)
            # console.print(shows_with_unwatched)

            for show in shows_with_unwatched['result']['tvshows']:
                # console.log(f"Show [{show['title']}] Year: [{show['year']}]")

                # Shows are in Showname (Year) folders, but may also have a country...
                # E.g. Doc (US) (2025)
                # Match the occasional shows with the disambiguating year already at the end...
                pattern = r'^(.*?)\s*\((\d{4})\)$'
                match = re.match(pattern, show['title'])
                if match:
                    folder = show['title']
                # (General case) - no year at end of the show, so add it...
                else:
                    folder = f"{show['title']} ({show['year']})"

                # console.log(f"Folder: [{folder}]")

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
                # if show["title"] == 953 or show['tvshowid'] == 953:
                #     console.print(show["title"])
                # console.print(unwatched_episodes)

                if unwatched_episodes:
                    first_unwatched_episodes[folder] = (
                            {
                                    "showId": show["tvshowid"],
                                    "season": unwatched_episodes[0]["season"],
                                    "episode": unwatched_episodes[0]["episode"],
                                    "folder": folder
                            }
                    )

        # Now create on-the-fly config for name 'agogo' based on the list of unwatched episodes
        do_init(first_unwatched_episodes)

    # Now, run a normal library update based on this on-the-fly config
    do_update()

    # clean up the on-the-go config files
    if store.update_tv:
        console.rule("Cleaning Up agogo files...")
        console.log("Removing agogo on-the-fly tv config")
        try:
            os.remove(f"{store.mediacopier_path}/config/Subscribers/config.agogo.tv.txt")
        except Exception:
            console.log(f"Error deleting on-the-fly tv config file - please manually delete {store.mediacopier_path}/config/Subscribers/config.agogo.tv.txt", style="danger")


