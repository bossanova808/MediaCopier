import glob
import operator
import os
import shutil
from thefuzz import fuzz, process

from base.console import console
from models.store import store
from base import utils


def do_delete_watched():
    """
    Clean watched media from an agogo machine to make room for more!

    Connect to Kodi and get access to the main library
    Loop through each show(/movie?) found, and work out from the Kodi library if watched
    If so -> remove the  tv file
    Finally, recursively re-scan tv folders for size -> any less than ?35mb, delete the folder entirely
    """
    console.rule("[green]Agogo[/green] - cleaning watched media")
    # Get all TV shows from Kodi, sort by name
    sort = {
            'method': 'label',
    }
    kodi_shows = store.kodi.VideoLibrary.GetTVShows(sort=sort)
    console.log(kodi_shows)

    # Gives:
    #  'id': 'fb7f0280da0a4fdbad0b7812c43c0e94',
    #  'jsonrpc': '2.0',
    #  'result': {
    #      'limits': {'end': 323, 'start': 0, 'total': 323},
    #      'tvshows': [
    #          {'label': 'Your Garden Made Perfect', 'tvshowid': 769}, etc

    tv_folders = utils.subfolders_of_path(store.tv_output_path)

    manual_deletes = []

    for folder in tv_folders:
        console.log(f"Handling '{folder.name}' (at path '{folder.path}')")

        # Get the Kodi TV show ID, falling back to fuzzy matching if required
        kodi_show = None
        match_quality = 0

        # Try and directly match show folder to showname
        # *** Add common transformation rules here if need be!  E.g. ' - ' -> ": " etc  ***
        for tvshow in kodi_shows['result']['tvshows']:
            if tvshow['label'] == folder.name:
                kodi_show = tvshow
                match_quality = 100
            # Bosch: legacy <> Bosch - Legacy etc.
            elif tvshow['label'] == folder.name.replace(" - ",": "):
                kodi_show = tvshow
                match_quality = 100

        # Otherwise, fall back to fuzzy matching...
        if not kodi_show:

            good_fuzzy = True
            fuzzy_match = None
            fuzzy_match2 = None

            folder_name_to_match = folder.name
            if folder.name[-1] == ")":
                folder_name_to_match = folder.name[:-7]

            fuzzy_match = process.extractOne(folder_name_to_match, kodi_shows['result']['tvshows'])
            #  ({'label': 'Trigger Point (2022)', 'tvshowid': 1150}, 90)
            # Skip low quality matches - probably shows removed from libary...print a message and manually delete
            # Short name shows seem to throw a spanner in the works so just handle manually...
            if fuzzy_match[1] < 86 and fuzzy_match[0]['label'] not in folder.name:
                console.log(f"Low quality match for {folder_name_to_match}, found {fuzzy_match}")
                good_fuzzy = False

                # Is there a (year) on the end?  try matching without it
                if folder_name_to_match != folder.name:
                    fuzzy_match2 = process.extractOne(folder.name, kodi_shows['result']['tvshows'])
                    console.log(f"Match 2 is {fuzzy_match2}")
                    if fuzzy_match2[1] > 89 or fuzzy_match2[0]['label'] in folder.name:
                        console.log("Good quality match, so using")
                        good_fuzzy = True
                        fuzzy_match = fuzzy_match2

            if not good_fuzzy:
                console.log("No good match!  Has show been removed from the library?", style="danger")
                console.log(fuzzy_match, style="danger")
                manual_deletes.append(folder.name)
                continue

            kodi_show = fuzzy_match[0]
            match_quality = fuzzy_match[1]

        kodi_tvshow_name = kodi_show['label']
        kodi_tvshow_id = kodi_show['tvshowid']
        console.log(f"Matched to Kodi show [{kodi_tvshow_name}] (id: {kodi_tvshow_id}), score: {match_quality})",
                    style="info")

        # Now find the video files with playcount > 1, to delete
        video_files = utils.video_files_in_path_recursive(folder.path)
        for video in video_files:
            # console.log(f"Considering: '{video}'", style="info")
            try:
                sxxexx, season_string, season_int, episode_string, episode_int = utils.extract_sxxexx(
                        video.name)

                properties_list = [
                        # "season",
                        "episode",
                        "playcount",
                ]

                episodes_details = store.kodi.VideoLibrary.GetEpisodes(tvshowid=kodi_tvshow_id,
                                                                       season=season_int,
                                                                       properties=properties_list)

                kodi_episode = None
                kodi_episodes_details = episodes_details['result']['episodes']
                for kodi_episode_details in kodi_episodes_details:
                    if kodi_episode_details['episode'] == episode_int:
                        kodi_episode = kodi_episode_details

                if not kodi_episode:
                    console.log(
                            f"Couldn't find Kodi episode for {kodi_tvshow_name} {sxxexx} - Season {season_int} Episode {episode_int}", style="danger")
                    console.log(kodi_episodes_details)
                    manual_deletes.append(folder.name)
                    continue

                # Cache the results to speed things up later...
                store.playcount_cache[f"{kodi_tvshow_id}-{season_int}-{episode_int}"] = kodi_episode['playcount']

                # console.log(kodi_episode, style="info")
                if kodi_episode['playcount'] > 0:
                    if store.pretend:
                        console.log(f"Would have deleted: '{video.name}'", style="warning")
                    else:
                        console.log(f"Deleting watched episode: '{video.name}'", style="warning")
                        os.remove(video.path)

            except Exception:
                console.log("Error!")
                console.print_exception()
                exit(1)

    console.rule("Deleting Small (<35mb) folders....")
    # Now tidy up small folders
    all_subfolders = utils.subfolders_of_path_recursive(store.tv_output_path)
    # reverse the list so that subfolders are deleted before parent folders
    all_subfolders.reverse()
    for folder in all_subfolders:
        # console.log(f"Folder {folder} size {utils.get_directory_size_in_bytes(folder)}")
        if utils.folder_size_in_bytes(folder.path) < 36700160:
            if store.pretend:
                console.log(f"Would have deleted: '{folder.path}'", style="warning")
            else:
                console.log(f"Deleting small (<35mb) folder '{folder.path}'", style="warning")
                shutil.rmtree(folder.path)

    if manual_deletes:
        console.rule("Issues")
        console.log("Failed to handle these folders, consider manual deletion?", style="danger")
        unqiues = set(manual_deletes)
        console.log(unqiues, style="danger")

    console.rule(f'Finished cleaning Agogo drive of watched material!')


def do_delete_lower_quality_duplicates():
    """
    Remove lower quality duplicates from an Agogo machine

    We may have copied lower quality files to an Agogo previously (better quality now available, propers etc)
    If there are two versions of a file (determined by the same sxxexx) - then delete the eldest of the files.
    """

    console.rule(f"Detecting duplicates and delete lower quality versions in {store.tv_output_path}")

    tv_folders = utils.subfolders_of_path(store.tv_output_path)

    if store.pretend:
        console.log(f"*** (Files to delete will appear multiple times when --pretend is used) ***", style="danger")

    for folder in tv_folders:
        # Isolate one folder for testing with mc --pretend delete-dupes
        # if folder.name != "Bad Sisters":
        #     continue

        console.log(f"Handling '{folder.name}' (at path '{folder.path}')")
        video_files = utils.video_files_in_path_recursive(folder.path)

        for video in video_files:
            sxxexx, season_string, season_int, episode_string, episode_int = utils.extract_sxxexx(video.name)
            # console.log(f"Globbing for video files with: {sxxexx} in: {folder.path}")
            files_with_same_sxxexx = utils.sxxexx_video_files_in_path(folder.path, sxxexx)

            if len(files_with_same_sxxexx) == 1:
                # console.log(f"Only one video file found for {sxxexx}")
                continue
            else:
                sorted_files_with_same_sxxexx = sorted(files_with_same_sxxexx, key=operator.attrgetter('mtime'), reverse = True)
                for sxxexx_file in sorted_files_with_same_sxxexx[1:]:
                    # console.log(f" Found file to remove: {sxxexx_file.name}")
                    if store.pretend:
                        console.log(f"Would have deleted: {sxxexx_file.name}", style="warning")
                    else:
                        console.log(f"Deleting lower quality duplicate: {sxxexx_file.name}", style="warning")
                        os.remove(sxxexx_file.path)

    console.rule(f'Finished cleaning Agogo drive of lower quality duplicates!')
