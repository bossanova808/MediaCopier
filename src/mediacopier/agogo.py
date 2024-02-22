import os

from console.console import console
from data.store import store
from mediacopier.init import do_init
from mediacopier.update import do_update


def do_agogo():
    """
    Run an on-the-fly init for the special 'user' agogo, using a live Kodi instance to work out:
    - all unwatched tv
    - new movies since the last update

    ...then, call 'update' based on this on-the-fly config
    """

    if store.update_tv:
        
        console.rule(f'[green]Agogo[/green] - copy unwatched TV & selected new movies')
        console.log("First, an one-the-fly [green]init[/green] for the user 'agogo'")
        console.log("Then, an [green]update[/green] with the resulting dynamic configuration for 'agogo'")

        # First we need to get our list of unwatched material from Kodi
        first_unwatched_episodes = {}

        filter_dict = {
                "field": "playcount",
                "operator": "is",
                "value": "0"
        }
        properties_list = [
                "title",
                "playcount",
                "file"
        ]

        console.log("")
        with console.status('Getting unwatched episodes list from Kodi\n'):

            shows_with_unwatched = store.kodi.VideoLibrary.GetTVShows(filter=filter_dict, properties=properties_list)
            # console.print(shows_with_unwatched)

            for show in shows_with_unwatched['result']['tvshows']:

                # console.log(show)

                # nfs://192.168.1.51/TVLibrary05/PLUTO/ -> PLUTO
                folder = show["file"].split('/')[-2]

                filter_dict = {
                        "field": "playcount",
                        "operator": "lessthan",
                        "value": "1"
                }
                json_sort = {
                        "order": "ascending",
                        "method": "episode"
                }
                unwatched_episodes = store.kodi.VideoLibrary.GetEpisodes(tvshowid=show["tvshowid"], season=None, filter=filter_dict, sort=json_sort)['result']['episodes']
                # console.print(unwatched_episodes)

                # for episode in unwatched_episodes:
                #    print episode["label"]
                # 3x07. MagicHour (2)
                cut = unwatched_episodes[0]["label"].split(".", 1)
                episode_string = cut[0]
                parts = episode_string.split("x")
                try:
                    season_number = parts[0]
                    episode_number = parts[1]
                # Deal with specials returned as S09
                except Exception:
                    season_number = "0"
                    episode_number = (parts[0])[1:]

                first_unwatched_episodes[folder] = (
                    {
                        "showId": show["tvshowid"],
                        "season": season_number,
                        "episode": episode_number,
                        "folder": folder
                    }
                )

        # Now create on-the-fly config for name 'agogo' based on the list of unwatched episodes ...
        do_init(first_unwatched_episodes)

    # ...and then run a normal library update based on this created config
    do_update()

    # clean up the on-the-go config files
    if store.update_tv:
        console.rule("Cleaning Up agogo files...")
        console.log("Removing agogo on-the-fly tv config")
        try:
            os.remove("config/Subscribers/config.agogo.tv.txt")
        except Exception:
            console.log("Error deleting on-the-fly tv config file - please manually delete config/Subscribers/config.agogo.tv.txt", style="danger")

    # ...and, finally, we're done!
    console.rule(f'Finished Media Library [green]Update[/green] for [blue]{store.name}!')
