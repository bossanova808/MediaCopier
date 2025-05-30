import os

from base.console import console
from models.store import store


def filter_tv_queue_by_kodi_watched_status(tv_copy_queue):
    """
    The built tv copy queue likely has watched episodes in it (e.g. for shows not being watched in order)
    Filter those out of the queue before the actual copying
    """
    console.rule("Filtering TV copy queue by Kodi watched status")
    console.log(f"Length of unfiltered copy queue: {len(tv_copy_queue)}")

    with console.status('Filtering by: Kodi Watched Status'):

        filtered_copy_queue = []

        for copy_item in tv_copy_queue:
            # Only video files have the id stuff at the end, not base files etc...
            # Copy those needed base files (as by definition there is _something_ unwatched for this series)
            tv_show_name = copy_item.wanted_show
            tv_show_id = copy_item.show_id
            tv_show_season = copy_item.season
            tv_show_episode = copy_item.episode

            # Deal with shows being watched in random order...
            if tv_show_id and tv_show_id > 0:
                # console.log("Checking playcount of %s id: %s season: %s episode: %s" % (tv_show_name, str(tv_show_id), str(tv_show_season), str(tv_show_episode)))

                kodi_playcount = 0
                filename, file_extension = os.path.splitext(copy_item.file_name)

                # Grab the playcount from our cache if it is already in there...
                try:
                    kodi_playcount = store.playcount_cache[f"{tv_show_id}-{tv_show_season}-{tv_show_episode}"]
                    # if tv_show_id == 836:
                    #     console.log(f"Using playcount_cache: {kodi_playcount}")

                # Otherwise, check this particular episode is _actually_ unwatched in Kodi's library...
                #  (if we're dealing with shows being watched in an adhoc order...)
                except KeyError:
                    filter_dict = {
                        "field": "episode",
                        "operator": "is",
                        "value": str(tv_show_episode)
                    }
                    properties_list = ['season', 'episode', 'playcount']

                    result = store.kodi.VideoLibrary.GetEpisodes(tvshowid=tv_show_id,
                                                                 season=tv_show_season,
                                                                 filter=filter_dict,
                                                                 properties=properties_list)

                    # if tv_show_id == 836:
                    #     console.log(result)

                    # Episode found in kodi... _should_ be only one but isn't always??
                    # 'result': {
                    #         'episodes': [
                    #                 {'episode': 10, 'episodeid': 43648, 'label': '3x10. Kalgoorlie - Danica and Luke', 'playcount': 0, 'season': 3},
                    #                 {'episode': 10, 'episodeid': 43649, 'label': '3x10. Kalgoorlie - Danica and Luke', 'playcount': 1, 'season': 3}
                    #         ],
                    #         'limits'  : {'end': 2, 'start': 0, 'total': 2}
                    # }
                    try:
                        count = 0
                        for episode in result["result"]["episodes"]:
                            if episode['season'] == tv_show_season and episode['episode'] == tv_show_episode:
                                if count > 0:
                                    console.log("Multiple episodes returned by Kodi? Will use highest playcount", style="warning")
                                    console.log(result["result"]["episodes"])
                                count+=1
                                # console.log("Matched: "+ str(episode))
                                store.playcount_cache[f"{tv_show_id}-{tv_show_season}-{tv_show_episode}"] = episode['playcount']
                                kodi_playcount = episode['playcount'] if episode['playcount'] > kodi_playcount else kodi_playcount


                    # Episode not found in Kodi?  Don't skip it, just to be safe...
                    except KeyError:
                        if file_extension in store.video_file_extensions:
                            console.log(
                                f"{tv_show_name} Season {tv_show_season} episode {tv_show_episode} not found in Kodi Library? Copying just to be safe...")

                # One way or another we should have a playcount now, or we've assumed zero...
                if int(kodi_playcount) > 0:
                    # if file_extension in store.video_file_extensions:
                    #     console.log(f"Skipping: {copy_item.file_name} as Kodi playcount {kodi_playcount} is > 0", highlight=False)
                    continue

            # add this file to the filtered queue if it hasn't been watched...
            filtered_copy_queue.append(copy_item)

        console.log(f"Length of filtered copy queue: {len(filtered_copy_queue)}")
        return filtered_copy_queue


def filter_copy_queue_by_already_copied_in_full(copy_queue: list):
    console.rule("Filtering copy queue by already exists on destination")
    filtered_copy_queue = []

    console.log(f"Length of unfiltered copy queue: {len(copy_queue)}")

    with console.status('Filtering by: Already on Destination Drive'):

        for potential_copy in copy_queue:
            if os.path.exists(potential_copy.destination_file):
                if os.path.getsize(potential_copy.source_file) == os.path.getsize(potential_copy.destination_file):
                    # console.log(f"Skipping {potential_copy.file_name} as EXISTS and SAME SIZE")
                    continue
            filtered_copy_queue.append(potential_copy)

        console.log(f"Length of filtered copy queue: {len(filtered_copy_queue)}")
        return filtered_copy_queue
