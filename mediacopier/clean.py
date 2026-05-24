import operator
import os
import shutil
from pathlib import Path
from rich.markup import escape

from thefuzz import fuzz, process

from base.console import console, log
from models.store import store
from base import utils


# 2026-05-21 Improved both delete watched and delete dupes with Claude: https://claude.ai/chat/779c9b36-2353-48a3-9de4-8dfb5063f445
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

    # Build a year-stripped lookup dict for fuzzy matching, keyed by stripped label -> original show dict.
    # This prevents shared year tokens (e.g. "(2022)") from skewing fuzzy scores toward wrong shows.
    kodi_show_lookup = {
        (s['label'][:-7].strip() if s['label'].endswith(')') else s['label']): s
        for s in kodi_shows['result']['tvshows']
    }

    manual_deletes = []

    for folder in tv_folders:
        log(f"Handling [green]{folder.name}[/green]", indent=0)

        # Get the Kodi TV show ID, falling back to fuzzy matching if required
        kodi_show = None
        match_quality = 0

        folder_name_year_removed = folder.name
        if folder.name[-1] == ")":
            folder_name_year_removed = folder.name[:-7]

        # console.log(f'Folder Name: [{folder.name}] Year Removed: [{folder_name_year_removed}]')
        # console.log(store.map_folder_to_show_name)

        # Pre-compute all candidate Kodi labels from the folder name so the loop is clean.
        # folder_name_to_kodi_name() inverts the automatic transformations (" - "->": ", "! ("-> "? (")
        # covering cases like "Would I Lie to You! (2007)" -> "Would I Lie to You?" without manual map entries.
        kodi_name_auto = store.folder_name_to_kodi_name(folder.name)
        kodi_name_auto_year_removed = store.folder_name_to_kodi_name(folder_name_year_removed)
        # Also try year-stripped version of the auto-transformed full name
        # e.g. "Would I Lie to You? (2007)" -> "Would I Lie to You?"
        kodi_name_auto_full_year_removed = kodi_name_auto[:-7].strip() if kodi_name_auto.endswith(")") else kodi_name_auto
        # Manual map covers genuinely non-derivable cases (e.g. "The Traitors (UK)")
        kodi_name_from_map = store.map_folder_to_show_name.get(folder.name)
        kodi_name_from_map_year_removed = None
        if kodi_name_from_map:
            kodi_name_from_map_year_removed = kodi_name_from_map[:-7].strip() if kodi_name_from_map.endswith(")") else kodi_name_from_map

        # Try and directly match show folder to Kodi show name
        for tvshow in kodi_shows['result']['tvshows']:
            label = tvshow['label']
            if label in (folder.name, folder_name_year_removed,
                         kodi_name_auto, kodi_name_auto_year_removed,
                         kodi_name_auto_full_year_removed):
                kodi_show = tvshow
                match_quality = 100
            elif kodi_name_from_map and label in (kodi_name_from_map, kodi_name_from_map_year_removed):
                kodi_show = tvshow
                match_quality = 100

        # Otherwise, fall back to fuzzy matching...
        if not kodi_show:
            THRESHOLD_HIGH = 92
            THRESHOLD_LOW = 88

            # Deduplicated candidate strings to try in order, stopping at the first good hit.
            # Matching is done against year-stripped Kodi labels to avoid year tokens skewing scores.
            candidates = list(dict.fromkeys([
                folder_name_year_removed,
                folder_name_year_removed.replace(" - ", ": "),
                folder.name,
                folder.name.replace(" - ", ": "),
            ]))

            good_fuzzy = False
            fuzzy_match = None

            for candidate in candidates:
                matched_label, score = process.extractOne(candidate, kodi_show_lookup.keys())
                log(f"Fuzzy candidate '{candidate}' -> '{matched_label}' (score: {score})", indent=1)

                if score >= THRESHOLD_HIGH or matched_label in folder.name or folder.name in matched_label:
                    fuzzy_match = kodi_show_lookup[matched_label]
                    good_fuzzy = True
                    log(f"Accepted fuzzy match: '{matched_label}' (score: {score})", indent=1)
                    break

                # Keep the best low-quality match in case nothing better is found
                if fuzzy_match is None or score > fuzzy_match[1]:
                    fuzzy_match = (kodi_show_lookup[matched_label], score)

            # Last chance: accept the best candidate if it clears the lower threshold
            if not good_fuzzy and fuzzy_match and fuzzy_match[1] >= THRESHOLD_LOW:
                log(f"Accepted on lower threshold: '{fuzzy_match[0]['label']}' (score: {fuzzy_match[1]})", indent=1)
                good_fuzzy = True

            if not good_fuzzy:
                log("No good match! Has show been removed from the library?", indent=1, style="danger")
                console.log(fuzzy_match, style="danger")
                manual_deletes.append(folder.name)
                continue

            kodi_show = fuzzy_match[0] if isinstance(fuzzy_match, tuple) else fuzzy_match
            match_quality = fuzzy_match[1] if isinstance(fuzzy_match, tuple) else THRESHOLD_HIGH

        kodi_tvshow_name = kodi_show['label']
        kodi_tvshow_id = kodi_show['tvshowid']
        log(f"Matched: [bold]{kodi_tvshow_name}[/bold] (id: {kodi_tvshow_id}, score: {match_quality})", indent=1, style="info")

        # Now find the video files with playcount > 1, to delete
        video_files = utils.video_files_in_path_recursive(folder.path)
        for video in video_files:
            # console.log(f"  Considering: '{video}'", style="info")
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
                    log(f"Couldn't find Kodi episode for {kodi_tvshow_name} {sxxexx} - Season {season_int} Episode {episode_int}", indent=2, style="danger")
                    console.log(kodi_episodes_details)
                    manual_deletes.append(folder.name)
                    continue

                # Cache the results to speed things up later...
                store.playcount_cache[f"{kodi_tvshow_id}-{season_int}-{episode_int}"] = kodi_episode['playcount']

                # console.log(kodi_episode, style="info")
                if kodi_episode['playcount'] > 0:
                    if store.pretend:
                        log(f"Would have deleted: '{video.name}'", indent=2, style="warning")
                    else:
                        log(f"Deleting watched episode: '{video.name}'", indent=2, style="warning")
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

    console.rule(f'Finished cleaning of watched material!')


def do_delete_lower_quality_duplicates():
    """
    Remove lower quality duplicates from a destination

    We may have copied lower quality files to a destination (e.g. Agogo) previously (better quality now available, propers etc)
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

        log(f"Handling [green]{folder.name}[/green]", indent=0)
        video_files = utils.video_files_in_path_recursive(folder.path)
        already_handled = set()

        # Collect singles (no duplicates) grouped by season folder, and duplicates separately,
        # so we can log singles-per-season first, then duplicates, for each show folder.
        # singles_by_season: { season_folder_name: [sxxexx, ...] }
        singles_by_season = {}
        duplicates_to_process = []

        for video in video_files:
            sxxexx, season_string, season_int, episode_string, episode_int = utils.extract_sxxexx(video.name)
            files_with_same_sxxexx = utils.sxxexx_video_files_in_path(folder.path, sxxexx)
            season_folder = Path(video.path).parent.name

            if len(files_with_same_sxxexx) == 1:
                singles_by_season.setdefault(season_folder, []).append(sxxexx)
                continue

            if sxxexx in already_handled:
                continue
            already_handled.add(sxxexx)

            sorted_files = sorted(files_with_same_sxxexx, key=operator.attrgetter('mtime'), reverse=True)
            duplicates_to_process.append((sorted_files[0], sorted_files[1:]))

        # Log singles first, one line per season folder
        for season_folder, episodes in sorted(singles_by_season.items()):
            console.log(f"  No dupes [green]{season_folder}[/green]: {', '.join(sorted(episodes))}", style="info")

        # Then log and action duplicates
        for kept, to_delete in duplicates_to_process:
            for sxxexx_file in to_delete:
                stem = Path(sxxexx_file.path).stem
                parent = Path(sxxexx_file.path).parent
                sidecars = [
                    s for s in parent.iterdir()
                    if s.is_file() and s.name.startswith(stem + ".") and s.suffix.lower() not in store.video_file_extensions
                ]
                console.log(f"  [yellow]Dupe found[/yellow] - keeping: {kept.name}")
                if store.pretend:
                    console.log(f"  Would have deleted: {sxxexx_file.name}", style="warning")
                    for sidecar in sidecars:
                        console.log(f"  Would have deleted sidecar: {sidecar.name}", style="warning")
                else:
                    console.log(f"  Deleting lower quality duplicate: {sxxexx_file.name}", style="warning")
                    for sidecar in sidecars:
                        console.log(f"  Deleting sidecar: {sidecar.name}", style="warning")
                        os.remove(sidecar)
                    os.remove(sxxexx_file.path)

    console.rule(f'Finished cleaning of lower quality duplicates!')
