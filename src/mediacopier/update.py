import os
import re

from console.console import console
from data.copy_item import CopyItem
from data.store import store
from mediacopier import config
from mediacopier.filter import filter_tv_queue_by_kodi_watched_status, filter_copy_queue_by_already_copied_in_full
from utils import utils
from utils.copy import copy


def build_show_lists():
    """
    Build two list:
     1. of all available TV shows in the th path
     2. of new tv shows since the last update of this subscriber
    """
    all_available_tv_shows_list = []
    new_tv_shows_list = []

    for d in store.tv_input_paths:
        shows_in_this_path = os.listdir(d)
        # console.log(d + " contains:\n" + str(shows_in_this_path))
        for show_in_this_path in shows_in_this_path:
            show_path = os.path.join(d, show_in_this_path)
            if os.path.isdir(show_path):
                all_available_tv_shows_list.append(show_path)
                if show_in_this_path not in store.tv_subscriptions_basic_show_list:
                    new_tv_shows_list.append(show_path)
            else:
                console.log(show_in_this_path + " - is not a directory.", style="danger")

    with open('results/tv.library.all.txt', 'w') as f:
        for show in all_available_tv_shows_list:
            f.write(f"{os.path.basename(show)}, at {show}\n")
    console.log("Wrote list of all tv shows to 'results/tv.library.all.txt'")
    if new_tv_shows_list:
        with open('results/tv.library.new.txt', 'w') as f:
            for show in new_tv_shows_list:
                f.write(f"{os.path.basename(show)}, at {show}\n")
        console.log("Wrote list of new-since-last-update tv shows to 'results/tv.library.new.txt'")

    return all_available_tv_shows_list, new_tv_shows_list


def create_movie_copy_queue():
    """
    Create & return the list of movies to copy
    (much easier than for tv, simply prompts interactively for all movies not in the unwanted_movies list)
    """

    movie_copy_queue = []
    movies_available = []

    for folder in store.movie_input_paths:
        files_in_path = utils.list_of_directory_paths_for(folder)
        for movie_file in files_in_path:
            if movie_file != ".deletedByTMM":
                movies_available.append(movie_file)

    # Save this to our store for later use when writing out the tracker file...
    # noinspection PyTypeChecker
    store.movies_available = sorted(map(os.path.basename, movies_available), key=str.lower)
    console.log(f"{len(movies_available)} Movies found in library")

    # Log these larger lists to separate files as it's too much/too slow for the console...
    movies_in_library_file = "results/movies.library.txt"
    new_movies_file = "results/movies.new.to.subscriber.txt"

    with open(movies_in_library_file, "w") as movie_file:
        for movie in movies_available:
            movie_file.write(f"{os.path.basename(movie)}, at '{movie}\n")
    console.log(f"Wrote '{movies_in_library_file}'")

    console.log("\nInteractively process New Movies since last update...")

    with open(new_movies_file, "w") as new_movie_file:
        for movie in movies_available:
            movie_name = os.path.basename(movie)
            if movie_name not in store.unwanted_movies and movie_name != ".deletedByTMM":
                console.print("")
                answer = console.input("Add new movie [blue]" + repr(movie_name) + "[/blue] to copy list ([green]enter=no[/green], [red]y=yes[/red]) ")
                if not answer or answer.lower() == "n":
                    console.log(f"{movie_name} - Not Selected")
                    new_movie_file.write(f"{movie_name} - Not Selected\n")
                else:
                    console.log(f"{movie_name} - Selected")
                    new_movie_file.write(f"{movie_name} - Selected\n")

                    # Add all the files from the movie folder - we don't bother with sub-dirs like '.actors' or 'extrafanart'
                    movie_files = [f for f in os.listdir(movie) if os.path.isfile(os.path.join(movie, f))]

                    for movie_file in movie_files:
                        movie_copy_queue.append(CopyItem(
                            file_name=movie_file,
                            file_size=os.path.getsize(os.path.join(movie,movie_file)),
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
    # store any shows we find in the subscriptions that we don't find in the library
    shows_not_matched_to_library = []

    # build lists of all available tv shows, and shows that are new for this subscriber
    all_available_tv_shows_list, new_tv_shows_list = build_show_lists()

    console.log(f"{len(store.tv_subscriptions_basic_show_list)} Shows found in the subscription file.")
    with open("results/tv.subscriptions.from.config.txt", "w") as f:
        # noinspection PyTypeChecker
        for show in sorted(store.tv_subscriptions_basic_show_list, key=str.lower):
            f.write(f"{show}\n")
    console.log(f"Wrote 'results/tv.subscriptions.from.config.txt'")

    if len(new_tv_shows_list) > 0:
        console.log(f"{len(new_tv_shows_list)} New (new since last update) shows found in library.")
        with open("results/tv.new.since.last.update.txt", "w") as f:
            # noinspection PyTypeChecker
            for show in new_tv_shows_list:
                f.write(f"{os.path.basename(show)}\n")
        console.log(f"Wrote 'results/tv.new.since.last.update.txt'")

    if store.name != 'agogo':
        console.log("\nInteractively decide about new TV shows.\n")
        for show in new_tv_shows_list:
            answer = console.input(f"Subscribe to new TV show '{os.path.basename(show)}' ([green]enter = no[/green], [red]y = yes[/red]) ")
            if (not answer) or answer.lower == "n":
                console.log(f"[green]{show} - Not Added[/green], set to 0|0 in output_show_list")
                output_show_list[os.path.basename(show)] = [0, 0]
            else:
                console.log(f"[red]{show} - Added")
                store.tv_subscriptions.append(os.path.basename(show) + "|1|0\n")

    console.log("\nNow, process each wanted show.\n")

    # For each wanted show...
    for subscription in store.tv_subscriptions:

        indent = "    "

        wanted_show = None
        wanted_season_int = None
        wanted_episode = None
        wanted_season = None
        show_id = None

        # parse config file
        try:
            values = subscription.split('|')
            wanted_show = values[0]
            wanted_season_int = int(values[1])
            wanted_season = format(wanted_season_int, "02d")
            wanted_episode = int(values[2])
            show_id = int(values[3])
        except IndexError:
            # is this needed, could be left at None?
            show_id = 0

        # record where we started e.g. original_show_list['Bosch'] = [5,1] (i.e. [season, episode])
        original_show_list[wanted_show] = [wanted_season_int, wanted_episode]

        output = f"[bold green]Wanted:[/bold green] {wanted_show}, from S{wanted_season_int:02d}E{wanted_episode:02d}"

        #######################
        # skip if set to 0,0
        if wanted_season_int == 0 and wanted_episode == 0:
            original_show_list[wanted_show] = [0, 0]
            output_show_list[wanted_show] = [0, 0]
            output += " -> Skipped as 0|0."
            console.log(output, style="info", highlight=None)
            # go back to the top of the loop for the next show
            continue

        #######################
        # otherwise start processing
        console.log(output, style="success", highlight=None)
        found_show = False
        origin_folder = ""
        output_folder = ""

        ############
        # do we recognise this show?
        for possible_show in all_available_tv_shows_list:
            # console.log("Matching " + wanted_show + " to " + os.path.basename(possible_show))
            if wanted_show == os.path.basename(possible_show):
                origin_folder = possible_show
                output_folder = os.path.join(store.tv_output_path, wanted_show)
                console.log(f"[bold green]Matched:[/bold green] '{wanted_show}' to: '{origin_folder}', copy to:'{output_folder}'")
                found_show = True
                # show has been found so no need to compare further
                break

        # show is not in the available list
        if not found_show:
            console.log("WARNING: SHOW NOT FOUND - so added to unfound list, and won't be re-written to tracker file",
                        style="danger")
            shows_not_matched_to_library.append(wanted_show)
            continue

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
        missed_one_already = False
        found_new_episode = False

        # we loop through each season until we can't find two seasons in a row
        while season_folder_exists:
            if os.path.exists(current_season_folder):
                # the season folder exists
                # console.log(f"{indent}Handling {os.path.basename(current_season_folder)}", style="info")
                # make a list of files in the current season
                current_season_files = utils.list_of_directory_paths_for(current_season_folder)
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
                    console.log(f"{indent}Added S{current_season_int:02d} - {episodes_added}", style="info")
                else:
                    console.log(f"{indent}No episodes to add from S{current_season_int:02d}", style="info")

                # get set up for the next season
                wanted_episode = 0
                current_season_int += 1
                current_season_folder = os.path.join(origin_folder, f"Season {current_season_int:02d}")
                current_season_folder_output = os.path.join(str(output_folder), f"Season {current_season_int:02d}")

            else:
                console.log(f"{indent}There is no '{current_season_folder}'", style="info")
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
        console.log(f"{indent}Updated {wanted_show} to {output_show_list[wanted_show]}", style="success")

        # If there are any new episodes, add the base files to the queue as well (e.g. folder.jpg)
        if found_new_episode:
            base_dir_files = utils.list_files(origin_folder)
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
            console.log(f"{indent}Base files (artwork etc) added to copy queue :white_check_mark:", style="info")

            # And if there are new episodes, always attempt to copy the Season 00 folders if there are any
            specials_path = os.path.join(origin_folder + "Season 00")
            output_specials_path = os.path.join(str(output_folder), "Season 00")
            if os.path.exists(specials_path):
                season00_files = utils.list_files(specials_path)
                for season00_file in season00_files:
                    p = re.compile('S[0-9]*E[0-9]*')
                    match = p.search(season00_file)
                    if match:
                        se_string = match.group()
                        season_string = "00"
                        episode_string = se_string[4:6]
                        console.log(f"{indent}Special (Season 00) file found and added to queue: '{season00_file}'", style="info")
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
                        console.log(f"{indent}Could not match season/episode of special so adding to queue anyway to be safe: '{season00_file}'", style="warning")
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

    # First work out the changes to make...
    tv_copy_queue = []
    movie_copy_queue = []

    if store.update_tv:
        console.rule(f'Processing TV Shows')
        tv_copy_queue = create_tv_copy_queue()
        if tv_copy_queue:
            tv_copy_queue = filter_copy_queue_by_already_copied_in_full(tv_copy_queue)
        # if agogo, we double-check with Kodi and filter out things that have been watched out of sequence
        if store.name == "agogo":
            tv_copy_queue = filter_tv_queue_by_kodi_watched_status(tv_copy_queue)
        if tv_copy_queue:
            with open("results/tv.copy.queue.txt", "w") as f:
                for tv_copy in tv_copy_queue:
                    f.write(f"{tv_copy}\n")
            console.log("Wrote 'results/tv.copy.queue.txt'")

    if store.update_movies:
        console.rule(f'Processing Movies')
        movie_copy_queue = create_movie_copy_queue()
        if movie_copy_queue:
            movie_copy_queue = filter_copy_queue_by_already_copied_in_full(movie_copy_queue)
        if movie_copy_queue:
            with open("results/movies.copy.queue.txt", "w") as f:
                for movie_copy in movie_copy_queue:
                    f.write(f"{movie_copy}\n")
            console.log("Wrote 'results/movies.copy.queue.txt'")

    # ...now actually copy the calculated queues
    copy(tv_copy_queue, movie_copy_queue)

    # ...and write out the updates subscription tracker files
    if store.update_tv and store.name != "agogo":
        config.save_tv_config()
    if store.update_movies:
        config.save_movie_config()
