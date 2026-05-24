import json
import os
import re

from base.console import console, log
from mediacopier.finish import finish_update
from models.copy_item import CopyItem
from models.store import store
from mediacopier import config
from mediacopier.filter import filter_tv_queue_by_kodi_watched_status, filter_copy_queue_by_already_copied_in_full
from base import utils
from base.copy import copy, check_disk_space


def build_show_lists():
    """
    Build two lists:
     1. of all available TV shows in the path
     2. of new tv shows since the last update of this subscriber
    """
    all_available_tv_shows_list = []
    new_tv_shows_list = []

    for d in store.tv_input_paths:
        shows_in_this_path = os.listdir(d)
        # console.log(d + " contains:\n" + str(shows_in_this_path))
        for show_in_this_path in shows_in_this_path:
            if not show_in_this_path.startswith('.') and show_in_this_path not in ["lost+found"]:
                show_path = os.path.join(d, show_in_this_path)
                if os.path.isdir(show_path):
                    all_available_tv_shows_list.append(show_path)
                    if show_in_this_path not in store.tv_subscriptions_basic_show_list:
                        new_tv_shows_list.append(show_path)
                else:
                    console.log(show_in_this_path + " - is not a directory.", style="danger")

    with open(f'{store.mediacopier_path}/results/tv.library.all.txt', 'w', encoding='utf-8') as f:
        for show in all_available_tv_shows_list:
            f.write(f"{os.path.basename(show)}, at {show}\n")
    console.log(f"Wrote list of all tv shows to '{store.mediacopier_path}/results/tv.library.all.txt'")

    if new_tv_shows_list:
        with open(f'{store.mediacopier_path}/results/tv.library.new.txt', 'w', encoding='utf-8') as f:
            for show in new_tv_shows_list:
                f.write(f"{os.path.basename(show)}, at {show}\n")
        console.log(f"Wrote list of new-since-last-update tv shows to '{store.mediacopier_path}/results/tv.library.new.txt'")

    return all_available_tv_shows_list, new_tv_shows_list


def create_movie_copy_queue():
    """
    Create & return the list of movies to copy
    (much easier than for tv, simply prompts interactively for all movies not in the unwanted_movies list)
    """

    movie_copy_queue = []
    movies_available = []

    if store.movie_input_paths:
        for folder in store.movie_input_paths:
            # If doing agogo or agogo_kids, skip any movie libraries that are not relevant
            if store.name == "agogo" and "kids" in folder:
                continue
            elif store.name == "agogo-kids" and "adults" in folder:
                continue
            files_in_path = utils.list_of_folder_contents_as_paths(folder)
            for movie_file in files_in_path:
                if movie_file != ".deletedByTMM" and not (os.path.basename(movie_file).startswith(".") and os.path.basename(movie_file).endswith(".drive")):
                    movies_available.append(movie_file)

    # Save this to our store for later use when writing out the tracker file...
    # noinspection PyTypeChecker
    store.movies_available = sorted(map(os.path.basename, movies_available), key=str.lower)
    console.log(f"{len(movies_available)} Movies found in library")

    # Log these larger lists to separate files as it's too much/too slow for the console...
    movies_in_library_file = f"{store.mediacopier_path}/results/movies.library.txt"
    new_movies_file = f"{store.mediacopier_path}/results/movies.new.to.subscriber.txt"

    with open(movies_in_library_file, "w", encoding='utf-8') as movie_file:
        for movie in movies_available:
            movie_file.write(f"{os.path.basename(movie)}, at '{movie}\n")
    console.log(f"Wrote '{movies_in_library_file}'")

    console.log("\nInteractively process New Movies since last update...")
    cached_movies = store.pending_answers_cache.get("movies", {})

    with open(new_movies_file, "w", encoding='utf-8') as new_movie_file:
        for movie in movies_available:
            movie_name = os.path.basename(movie)
            if movie_name not in store.unwanted_movies and not movie_name.startswith(".") and movie_name not in ["lost+found"]:
                if movie_name in cached_movies:
                    answer = cached_movies[movie_name]
                    console.print("")
                    log(f"[bold]{movie_name}[/bold] -> [dodger_blue1](Cached)[/dodger_blue1] {'[red]Selected[/red]' if answer else '[green]Skip[/green]'}", indent=0)
                else:
                    console.print("")
                    raw = console.input("Add new movie [dodger_blue1]" + repr(movie_name) + "[/dodger_blue1] to copy list ([green]enter=no[/green], [red]y=yes[/red]) ")
                    answer = bool(raw and raw.lower() != "n")
                    cached_movies[movie_name] = answer
                    store.pending_answers_cache["movies"] = cached_movies
                    _save_pending_answers_cache()
                if not answer or answer.lower() == "n":
                    log(f"[green]{movie_name}[/green] -> Not selected", indent=1)
                    new_movie_file.write(f"{movie_name} - Not Selected\n")
                else:
                    log(f"[red]{movie_name}[/red] -> Selected", indent=1)
                    new_movie_file.write(f"{movie_name} - Selected\n")

                    # Add all the files from the movie folder - we don't bother with sub-dirs like '.actors' or 'extrafanart'
                    movie_files = [f for f in os.listdir(movie) if os.path.isfile(os.path.join(movie, f))]

                    for movie_file in movie_files:
                        movie_copy_queue.append(CopyItem(
                            file_name=movie_file,
                            file_size=os.path.getsize(os.path.join(movie, movie_file)),
                            source_folder=movie,
                            destination_folder=str(os.path.join(store.movie_output_path, movie_name)),
                            source_file=os.path.join(movie, movie_file),
                            destination_file=str(os.path.join(store.movie_output_path, movie_name, movie_file)),
                        ))

    console.log(f"Wrote '{new_movies_file}'")
    return movie_copy_queue


def create_tv_copy_queue():
    """
    Create & return the list of new tv to copy
    This is the most complex part of MediaCopier
    """

    # Our list to hold all the things we've worked out that we need to copy
    tv_copy_queue = []
    # the list of tv show subscription states, as parsed from the subscription file
    original_show_list = {}
    # will store the list of where we got up to with each show for outputting the done file
    output_show_list = {}
    # initalise this
    store.shows_not_matched_to_library = []

    # build lists of all available tv shows, and shows that are new for this subscriber
    all_available_tv_shows_list, new_tv_shows_list = build_show_lists()

    console.log(f"{len(store.tv_subscriptions_basic_show_list)} Shows found in the subscription file.")
    with open(f"{store.mediacopier_path}/results/tv.subscriptions.from.config.txt", "w", encoding='utf-8') as f:
        # noinspection PyTypeChecker
        for show in sorted(store.tv_subscriptions_basic_show_list, key=str.lower):
            f.write(f"{show}\n")
    console.log(f"Wrote '{store.mediacopier_path}/results/tv.subscriptions.from.config.txt'")

    if len(new_tv_shows_list) > 0:
        console.log(f"{len(new_tv_shows_list)} New (new since last update) shows found in library.")
        with open(f"{store.mediacopier_path}/results/tv.new.since.last.update.txt", "w", encoding='utf-8') as f:
            # noinspection PyTypeChecker
            for show in new_tv_shows_list:
                f.write(f"{os.path.basename(show)}\n")
        console.log(f"Wrote '{store.mediacopier_path}/results/tv.new.since.last.update.txt'")

    if store.name != 'agogo':
        cached_tv = store.pending_answers_cache.get("tv_shows", {})
        new_show_names = [os.path.basename(s) for s in new_tv_shows_list]
        cached_count = sum(1 for s in new_show_names if s in cached_tv)
        fresh_count = len(new_show_names) - cached_count
        if new_show_names:
            console.log(f"\nInteractively decide about [yellow]{len(new_show_names)}[/yellow] new TV show(s) "
                        f"([dodger_blue1]{cached_count} cached[/dodger_blue1], [green]{fresh_count} new question(s)[/green])\n")
        for show in sorted(new_tv_shows_list, key=lambda i: os.path.splitext(os.path.basename(i)[0])):
            show_name = os.path.basename(show)
            if show_name in cached_tv:
                answer = cached_tv[show_name]
                log(f"New show [bold]{show_name}[/bold] -> [dodger_blue1](Cached)[/dodger_blue1] {'[red]Subscribe[/red]' if answer else '[green]Skip[/green]'}", indent=0)
            else:
                raw = console.input(f"Subscribe to new TV show '{show_name}' ([green]enter = no[/green], [red]y = yes[/red]) ")
                answer = bool(raw and raw.lower() != "n")
                cached_tv[show_name] = answer
                store.pending_answers_cache["tv_shows"] = cached_tv
                _save_pending_answers_cache()
            if not answer:
                log(f"New show [bold]{show_name}[/bold] -> [green]Skip[/green]", indent=0)
                output_show_list[show_name] = [0, 0]
            else:
                log(f"New show [bold]{show_name}[/bold] -> [red]Subscribe[/red]", indent=0)
                store.tv_subscriptions.append(show_name + "|1|0\n")

    console.log("\nNow, process each wanted show.\n")

    # For each wanted show...
    for subscription in store.tv_subscriptions:

        wanted_show = None
        wanted_season_int = None
        wanted_episode = None
        original_wanted_episode = None
        wanted_season = None
        found_show = False
        origin_folder = ""
        output_folder = ""

        # parse config file
        try:
            values = subscription.split('|')
            wanted_show = values[0]
            wanted_season_int = int(values[1])
            wanted_season = format(wanted_season_int, "02d")
            wanted_episode = int(values[2])
            original_wanted_episode = wanted_episode
            show_id = int(values[3])
        except IndexError:
            # is this needed, could be left at None?
            show_id = 0

        # record where we started e.g. original_show_list['Bosch'] = [5,1] (i.e. [season, episode])
        original_show_list[wanted_show] = [wanted_season_int, wanted_episode]

        # Will be printed with skip reason appended if 0|0, or alone if we're processing it
        handling_msg = f"Handling [bold]{wanted_show}[/bold]"

        ############
        # First, do we recognise this show?  E.g. has it been removed from the library (or name change)
        # Apply name mapping once before the search loop (not inside it, to avoid remapping on every iteration)
        wanted_show_unmapped = wanted_show
        wanted_show = store.map_show_name_to_folder.get(wanted_show, wanted_show)
        remap_msg = f"Remapped: {wanted_show_unmapped} -> {wanted_show}" if wanted_show_unmapped != wanted_show else None

        for possible_show in all_available_tv_shows_list:
            if wanted_show == os.path.basename(possible_show):
                origin_folder = possible_show
                output_folder = os.path.join(store.tv_output_path, wanted_show)
                found_show = True
                # show has been found so no need to compare further
                break
        #######################
        # skip if set to 0,0 — log Handling inline and move on
        if wanted_season_int == 0 and wanted_episode == 0:
            original_show_list[wanted_show] = [0, 0]
            output_show_list[wanted_show] = [0, 0]
            console.log(f"{handling_msg} -> Skipped as 0|0.", style="info")
            # go back to the top of the loop for the next show
            continue

        # Show is not in the available list — log Handling header first, then the warning
        # (Remember - shows where we delete old season should still have a 'holder folder' left in place...so that shows continue to be tracked)
        # (A warning is now shown when we write out the updated tracker to make this very clear and give the opportunity to fix it)
        if not found_show:
            log(handling_msg, indent=0)
            log(f'WARNING: SHOW "{wanted_show}" NOT FOUND - so added to unfound list, and will be removed from tracker file', indent=1, style="danger")
            store.shows_not_matched_to_library.append(wanted_show)
            continue

        #######################
        # otherwise start processing — Handling header first, then match detail indented beneath
        log(handling_msg, indent=0)
        if remap_msg:
            log(remap_msg, indent=1, style="warning")
        log(f'[bold green]Matched:[/bold green] "{wanted_show}"', indent=1)
        log(f'[bold green]Source:[/bold green]  "{origin_folder}"', indent=1)
        log(f'[bold green]Dest:[/bold green]    "{output_folder}"', indent=1)
        log(f'[bold green]Wanted:[/bold green] "{wanted_show}", from S{wanted_season_int:02d}E{wanted_episode:02d}', indent=1, style="success")

        # OK, so the show is available, and we want some of it.  Let's find out if there are new episodes?
        start_season_int = int(wanted_season)
        start_season_folder = os.path.join(origin_folder, "Season " + wanted_season)
        start_season_folder_output = os.path.join(str(output_folder), "Season " + wanted_season)

        # set up for loop
        current_season_folder = start_season_folder
        current_season_folder_output = start_season_folder_output
        current_season_int = start_season_int
        episode_considering = 0

        season_folder_exists = True
        # Used to track when we miss two seasons in a row...
        missed_one_already = False
        found_new_episode = False

        # we loop through each season until we can't find two seasons in a row
        possible_output = []
        while season_folder_exists:
            if os.path.exists(current_season_folder):
                # If we found a season, reset this
                missed_one_already = False
                # the season folder exists
                # console.log(f"{indent}Handling {os.path.basename(current_season_folder)}", style="info")
                # make a list of files in the current season
                current_season_files = utils.list_of_folder_contents_as_paths(current_season_folder)
                # Now we want to match only the wanted episode and above and add them to the copy queue
                # keep track of them for logging
                episodes_added = []
                # and a queue to store files like folder.jpg that we will only copy if we found at least 1 new episode
                possible_queue = []

                for current_season_file in current_season_files:
                    # match the SXXEXX part of the filename
                    p = re.compile('S[0-9]*E[0-9]*')
                    match = p.search(current_season_file)
                    if match:
                        episode_string = match.group()
                        episode_string = episode_string.split('E')[1]
                        # console.log( f"episode_string is {episode_string}" )
                        episode_considering = int(episode_string)
                        # console.log( f"episode_considering is {episode_considering}" )
                        if episode_considering > wanted_episode:
                            found_new_episode = True
                            if episode_string not in episodes_added:
                                episodes_added.append(episode_string)
                            tv_copy_queue.append(CopyItem(
                                file_name=os.path.basename(current_season_file),
                                file_size=os.path.getsize(current_season_file),
                                source_folder=current_season_folder,
                                destination_folder=current_season_folder_output,
                                source_file=current_season_file,
                                destination_file=os.path.join(current_season_folder_output, os.path.basename(current_season_file)),
                                wanted_show=wanted_show,
                                show_id=show_id,
                                season=int(current_season_int),
                                episode=int(episode_considering)
                            ))

                    else:
                        # this queue not used anymore, see just below
                        # console.log(f"{indent}Did not match - add to possible queue: {current_season_file}")
                        possible_queue.append(CopyItem(
                            file_name=os.path.basename(current_season_file),
                            file_size=os.path.getsize(current_season_file),
                            source_folder=current_season_folder,
                            destination_folder=current_season_folder_output,
                            source_file=current_season_file,
                            destination_file=os.path.join(current_season_folder_output, os.path.basename(current_season_file)),
                        ))

                # Removed this Feb 24 as all it seems to copy is folder.jpgs in season folders
                # e.g. Survivor Season 17/folder.jpg - when no other files will be copied as all get filtered...
                # copy unmatched files if we're adding new things to this season (e.g. folder.jpg)
                # if found_new_episode_this_season and len(possible_queue) > 0:
                #     # console.log(f"{indent}Adding possible queue to tv copy queue, as we found a new episode")
                #     # console.log(possible_queue)
                #     tv_copy_queue.extend(possible_queue)

                # if we're moving up a season we want all episodes from the new season
                if len(episodes_added) > 0:
                    possible_output.append(f"Added S{current_season_int:02d} - {episodes_added}")
                else:
                    possible_output.append(f"No episodes to add from S{current_season_int:02d}")

                # get set up for the next season
                wanted_episode = 0
                current_season_int += 1
                current_season_folder = os.path.join(origin_folder, f"Season {current_season_int:02d}")
                current_season_folder_output = os.path.join(str(output_folder), f"Season {current_season_int:02d}")

            else:
                possible_output.append(f"There is no '{current_season_folder}'")
                # Because of some stupid shows/people, Location, Location, Location has seasons 31,33,34,35...so we skip
                # over one folder and check again just to be sure we should be stopping...
                if not missed_one_already:
                    # console.log(
                    #     f"Setting missed_one_already and incrementing current season from {current_season_int} to {current_season_int + 1}")
                    missed_one_already = True
                    current_season_int += 1
                    current_season_folder = os.path.join(origin_folder, f"Season {current_season_int:02d}")
                    current_season_folder_output = os.path.join(str(output_folder), f"Season {current_season_int:02d}")
                    wanted_episode = 0
                    continue
                # If we missed_one_already, then we've added one to the current_season_int so take that back off again so that
                # when we write the tracker file we're not one season forward...
                else:
                    current_season_int -= 1
                    # console.log(f"Two season folders in a row don't exist, stop looking for more & reset current_season_int to {current_season_int}")
                    break

        # if we copied anything from this season, record the last thing we copied
        # console.log(
        #    f"At this point, current_season_int ({current_season_int}) should be 1 more than what we want to record, so set output_show_int to {current_season_int - 1}")
        output_show_int = current_season_int - 1
        # don't decrement if we didn't copy a new season
        if output_show_int < wanted_season_int:
            # console.log(f"But we didn't copy a new season, so in fact set output_show_int to wanted_season_int ({wanted_season_int})")
            output_show_int = wanted_season_int
        output_show_list[wanted_show] = [output_show_int, episode_considering]

        # Nothing new?  We're done
        if not found_new_episode:
            log(f"No new episodes, show still at S{wanted_season_int:02d}E{original_wanted_episode:02d}", indent=1, style="info")
            # Issue - there were 6, now 3, which is right?:
            # OLD: Van der Valk(2020) | 4 | 6
            # NEW: Van der Valk(2020) | 4 | 3
            # Possible fix:
            # output_show_list[wanted_show] = [wanted_season_int, original_wanted_episode]
            output_show_list[wanted_show] = [wanted_season_int, original_wanted_episode]
            continue

        # But, if there are any new episodes, add the base files to the queue as well (e.g. folder.jpg)
        if found_new_episode:
            base_dir_files = utils.list_of_files(origin_folder)
            base_files = []
            for base_dir_file in base_dir_files:
                # tv_copy_queue.append([base_dir_file, output_folder])
                tv_copy_queue.append(CopyItem(
                    file_name=os.path.basename(base_dir_file),
                    file_size=os.path.getsize(base_dir_file),
                    source_folder=origin_folder,
                    destination_folder=str(output_folder),
                    source_file=base_dir_file,
                    destination_file=str(os.path.join(str(output_folder), os.path.basename(base_dir_file)))
                ))
                base_files.append(os.path.basename(base_dir_file))
            log(f"Base files (artwork etc) added to copy queue :white_check_mark:", indent=2, style="info")

            for line in possible_output:
                log(line, indent=2, style="info")
            log(f"WILL COPY {wanted_show} from [yellow]S{wanted_season_int:02d}E{original_wanted_episode + 1:02d}[/yellow] to [yellow]S{output_show_list[wanted_show][0]:02d}E{output_show_list[wanted_show][1]:02d}[/yellow]",
                indent=1, style="warning")

            # And if there are new episodes, always also attempt to copy the Specials (Season 00) folder, if there is one
            specials_path = os.path.join(origin_folder + "Season 00")
            output_specials_path = os.path.join(str(output_folder), "Season 00")
            if os.path.exists(specials_path):
                season00_files = utils.list_of_files(specials_path)
                for season00_file in season00_files:
                    p = re.compile('S[0-9]*E[0-9]*')
                    match = p.search(season00_file)
                    if match:
                        se_string = match.group()
                        season_string = "00"
                        episode_string = se_string[4:6]
                        log(f"Special (Season 00) file found and added to queue: '{season00_file}'", indent=2, style="info")
                        tv_copy_queue.append(CopyItem(
                            file_name=os.path.basename(season00_file),
                            file_size=os.path.getsize(season00_file),
                            source_folder=specials_path,
                            destination_folder=output_specials_path,
                            source_file=season00_file,
                            destination_file=os.path.join(output_specials_path,
                                                          os.path.basename(season00_file)),
                            wanted_show=wanted_show,
                            show_id=show_id,
                            season=int(season_string),
                            episode=int(episode_string)
                        ))
                    else:
                        log(f"Could not match season/episode of special so adding to queue anyway to be safe: '{season00_file}'", indent=2, style="warning")
                        tv_copy_queue.append(CopyItem(
                            file_name=os.path.basename(season00_file),
                            file_size=os.path.getsize(season00_file),
                            source_folder=specials_path,
                            destination_folder=output_specials_path,
                            source_file=season00_file,
                            destination_file=os.path.join(output_specials_path, os.path.basename(season00_file)),
                        ))

    store.original_show_list = original_show_list
    store.output_show_list = output_show_list
    return tv_copy_queue


def _pending_answers_cache_path() -> str:
    return f"{store.mediacopier_path}/results/cache.{store.name}.pending.json"


def _load_pending_answers_cache():
    """Load cached interactive answers from a previous incomplete run, if present."""
    cache_path = _pending_answers_cache_path()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                store.pending_answers_cache = json.load(f)
            tv_count = len(store.pending_answers_cache.get("tv_shows", {}))
            movie_count = len(store.pending_answers_cache.get("movies", {}))
            console.log(
                f"[dodger_blue1]Found saved answers from a previous incomplete run[/dodger_blue1] "
                f"({tv_count} TV show(s), {movie_count} movie(s) cached).",
                style="warning"
            )
            answer = console.input("Resume from saved answers? ([green]enter=yes[/green], [red]n=start fresh[/red]) ")
            if answer.lower() == "n":
                store.pending_answers_cache = {}
                console.log("Starting fresh — saved answers discarded.")
            else:
                console.log("Resuming from saved answers.")
        except Exception:
            console.log("Could not load pending answers cache — starting fresh.", style="warning")
            store.pending_answers_cache = {}
    else:
        store.pending_answers_cache = {}


def _save_pending_answers_cache():
    """Persist the current interactive answers to disk after each answer, so a partial run is recoverable."""
    try:
        with open(_pending_answers_cache_path(), "w", encoding="utf-8") as f:
            json.dump(store.pending_answers_cache, f, indent=2)
    except Exception as e:
        console.log(f"Warning: could not save pending answers cache: {e}", style="warning")


def _clear_pending_answers_cache():
    """Delete the pending answers cache on successful completion."""
    cache_path = _pending_answers_cache_path()
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            log("Cleared pending answers cache.", indent=0, style="info")
        except Exception as e:
            console.log(f"Warning: could not clear pending answers cache: {e}", style="warning")


def do_update():
    """
    Run an update for this subscriber:
    - Interactively query whether to subscribe new shows since the last update
    - Identify newly available episodes of subscribed tv shows
    - Interactively query whether to copy new movies since the last update
    - Finally, do the actual copying (if not in pretend mode!)
    """

    console.rule(f'Media Library [green]Update[/green] for [blue]{store.name}')

    # We load this in here, rather than in e.g. cli.py->update, as if we're doing an agogo, it's only just been created...
    config.load_tv_and_movie_config()

    # Load any pending answers cache from a previous incomplete run
    _load_pending_answers_cache()

    # First work out the changes to make...
    tv_copy_queue = []
    movie_copy_queue = []

    if store.update_tv:
        console.rule(f'Processing TV Shows')
        tv_copy_queue = create_tv_copy_queue()
        if tv_copy_queue:
            tv_copy_queue = filter_copy_queue_by_already_copied_in_full(tv_copy_queue)
        # if agogo, we double-check with Kodi and filter out things that have been watched out of sequence
        if "agogo" in store.name:
            tv_copy_queue = filter_tv_queue_by_kodi_watched_status(tv_copy_queue)
        if tv_copy_queue:
            with open(f"{store.mediacopier_path}/results/tv.copy.queue.txt", "w", encoding='utf-8') as f:
                for tv_copy in tv_copy_queue:
                    f.write(f"{tv_copy}\n")
            console.log(f"Wrote '{store.mediacopier_path}/results/tv.copy.queue.txt'")

            check_disk_space(tv_copy_queue, None)
            console.rule("TV Space")
            console.log(f"TV - available space is: {store.tv_available_space_gb:.2f} GB")
            console.log(f"TV - needed space is:    {store.tv_needed_space_gb:.2f} GB")

    if store.update_movies:
        console.rule(f'Processing Movies')
        movie_copy_queue = create_movie_copy_queue()
        store.movies_were_selected = len(movie_copy_queue) > 0
        if movie_copy_queue:
            movie_copy_queue = filter_copy_queue_by_already_copied_in_full(movie_copy_queue)
        if movie_copy_queue:
            with open(f"{store.mediacopier_path}/results/movies.copy.queue.txt", "w", encoding='utf-8') as f:
                for movie_copy in movie_copy_queue:
                    f.write(f"{movie_copy}\n")
            console.log("Wrote 'results/movies.copy.queue.txt'")

            check_disk_space(None, movie_copy_queue)
            console.rule("Movie Space")
            console.log(f"Movies - available space is: {store.movies_available_space_gb:.2f} GB")
            console.log(f"Movies - needed space is:    {store.movies_needed_space_gb:.2f} GB")

    # ...now actually copy the calculated queues
    console.rule("Total Space")
    console.log(f"Total to copy: {store.total_needed_space_gb:.2f} GB")

    # Apply speed limit now that we know the full transfer size across both TV and movies
    store.active_speed_limit_mbps = None
    if store.copy_speed_limit_mbps and store.copy_speed_limit_threshold_gb:
        if store.total_needed_space_gb >= store.copy_speed_limit_threshold_gb:
            store.active_speed_limit_mbps = store.copy_speed_limit_mbps
            console.log(
                f"Transfer size ({store.total_needed_space_gb:.1f} GB) exceeds threshold "
                f"({store.copy_speed_limit_threshold_gb} GB) — speed limit of "
                f"{store.copy_speed_limit_mbps} MB/s will be applied to protect SLC cache.",
                style="warning"
            )
        else:
            console.log(
                f"Transfer size ({store.total_needed_space_gb:.1f} GB) is under threshold "
                f"({store.copy_speed_limit_threshold_gb} GB) — copying at full speed.",
                style="info"
            )

    copy(tv_copy_queue, movie_copy_queue)

    # ...and write out the updated subscription tracker files
    if store.update_tv and "agogo" not in store.name:
        config.save_tv_config()
    if store.update_movies:
        config.save_movie_config()

    # ...and, finally, we're done!
    console.rule(f'Finished Media Library [green]Update[/green] for [dodger_blue1]{store.name}!')

    # Clear the pending answers cache now that we completed successfully
    _clear_pending_answers_cache()

    # Prompt to archive the old config, and swap in the new for future updates
    finish_update()
