import os
import yaml

from base.console import console
from models.store import store
from base import utils


def do_init(first_unwatched_episodes=None):
    """
    Sets up a new subscriber to the library by creating the tv.name.txt and movies.name.txt config files

    By default, it creates configuration files specifying:
    - 1 - all tv shows are unwanted
      (i.e. show_name|0|0 - then manually change any desired show subscriptions to show_name|1|0)
    - 2 - all movies marked as seen
      (so you'd then dimply delete any from the list, if you wish to copy them on the first run)
    - 3 - A config file for the user, specifying output paths for the to-be-copied media

    Alternatively, supply a list of first_unwatched_episodes from a Kodi installation, and it will create configuration files
    that will then trigger a copy of all unwatched tv episodes (unwatched movies are handled by prompting).
    """

    console.rule(f'[green]Init[/green] mediacopier for new name: [dodger_blue1]{store.name}')

    # 1. TV SHOWS
    if store.update_tv:
        # create the 3 config files - one for tv, paths, and optionally one for movies if we're not
        out_config_tv_filename = f"{store.mediacopier_path}/config/Subscribers/config." + store.name + ".tv.txt"
        create_file = True

        # don't clobber existing files by accident
        if os.path.isfile(out_config_tv_filename):
            console.log("\n:warning: Initialising, but TV config file already exists??", style="danger")
            console.log("Exists: " + out_config_tv_filename + "\n")
            answer = console.input("Overwrite existing config file ([red]x[/red]) or use the existing file ([green]enter[/green])? \n\n")
            if answer.lower() == "x":
                console.log("\n[red]Overwriting[/red] existing config file")
            else:
                console.log("\n[green]Using[/green] existing config file")
                create_file = False

        if create_file:
            with open(out_config_tv_filename, 'w', encoding="utf-8") as out_config_tv_file:

                tv_show_list = []

                for tv_path in store.tv_input_paths:
                    list_of_directories = utils.list_of_folder_contents_as_paths(tv_path)
                    list_of_directories = filter(os.path.isdir, list_of_directories)
                    for tv_show in map(os.path.basename, list_of_directories):
                        if tv_show != "lost+found":
                            tv_show_list.append(tv_show)

                # Remove any duplicates we might have like 'The Block'
                tv_show_list = set(tv_show_list)

                console.log(f"{len(tv_show_list)} TV shows in library on disk")
                # We don't write the show list out to a log file here as we do that in update
                # (we don't always run an init of course)
                # console.log(sorted(tv_show_list))

                if first_unwatched_episodes is None:
                    console.log("No latest episodes supplied (not agogo) -> setting all TV shows to unwanted.")
                    for tv_show in sorted(tv_show_list):
                        out_config_tv_file.write(tv_show + "|0|0\n")

                else:
                    console.log("Processing latest episodes list from Kodi (i.e. creating on-the-fly 'agogo' config)\n")

                    for tv_show in sorted(tv_show_list):
                        found = list(filter(lambda first_unwatched_episode:first_unwatched_episode['folder'] == tv_show, first_unwatched_episodes))

                        if not found:
                            # console.log(f"{tv_show} was not found to have a latest watched episode - set to unwanted")
                            out_config_tv_file.write(tv_show + "|0|0|0\n")
                        else:
                            console.log(f"Found {found}")
                            # we got here, so one of show or show (year) is in latest episodes...
                            # console.log(f"{tv_show} has a latest watched episode of {first_unwatched_episodes[tv_show]["season"]}|{first_unwatched_episodes[tv_show]["episode"]}||{first_unwatched_episodes[tv_show]["showId"]}", highlight=False)
                            # we're creating an output file for aGoGo machine so get the latest watched episode and record the previous episode
                            # in the config file as the last one copied
                            out_ep_num = int(found[0]["episode"])
                            # the config file stores the latest watched episode - so we have to take one off the unwatched episode number
                            if out_ep_num > 0:
                                out_ep_num -= 1

                            out_config_tv_file.write(
                                    f'{tv_show}|{found[0]["season"]}|{out_ep_num}|{found[0]["showId"]}\n'
                            )

                console.log(f"\nCreated '{out_config_tv_filename}'")

        # Sanity check for agogo
        if "agogo" in store.name:

            # Now we do a quick visual check of Kodi's latest episodes, and the generated on the fly copy list...
            console.log(f"Sanity check - comparing Kodi latest episodes with generated '{out_config_tv_filename}'\n")
            with open(out_config_tv_filename, 'r', encoding="utf-8") as f:
                lines = f.readlines()
                # console.log(f"Lines is {len(lines)}")

            shows_to_copy = []
            for line in lines:
                if not line.endswith('|0|0|0\n'):
                    shows_to_copy.append(line)

            for index, tv_show in enumerate(first_unwatched_episodes):
                console.log(f'Kodi: {tv_show["kodi"]}|{int(tv_show["season"])}|{int(tv_show["episode"])}|{tv_show["showId"]}', style="dodger_blue1", highlight=False)
                console.log(f"Copy: {shows_to_copy[index]}", style="light_goldenrod2", highlight=False)

            answer = console.input("Do the lists of " + str(len(first_unwatched_episodes)) + " shows match ([red]n[/red]/[green]enter[/green])? \n\n")
            if answer:
                exit()

            # and the tv stage is done...
            console.log(f"Created & confirmed '{out_config_tv_filename}'")

    # 2. MOVIES
    # For agogo updates, we always use the existing file
    # (EXCEPT on very first run - remove the name = 'agogo' test here if running agogo for the very first time to generate a new movies config file)
    # @TODO - ?make this a CLI switch?
    if store.update_movies and "agogo" not in store.name:

        out_config_movies_filename = f"{store.mediacopier_path}/config/Subscribers/config.{store.name}.movies.txt"

        # don't clobber existing files by accident
        create_file = True
        if os.path.isfile(out_config_movies_filename):
            console.log("\n:warning: Initialising, but Movies config file already exists??", style="danger")
            console.log("Exists: " + out_config_movies_filename + "\n")
            create_file = False
            answer = console.input("Overwrite existing config file ([red]x[/red]) or use the existing file ([green]enter[/green])? ")
            if answer.lower() == "x":
                create_file = True

        if create_file:

            with open(out_config_movies_filename, 'w', encoding='utf-8') as out_config_movies_file:

                watched_movies = []

                for movie_path in store.movie_input_paths:
                    list_of_directories = utils.list_of_folder_contents_as_paths(movie_path)
                    for movie in map(os.path.basename, list_of_directories):
                        watched_movies.append(movie)

                console.log(f"{len(watched_movies)} movies in library -> setting all movies to unwanted.")
                # console.log(watched_movies)

                for movie in sorted(watched_movies):
                    out_config_movies_file.write(movie + "\n")

            # and the movies stage is done...
            console.log(f"Created '{out_config_movies_filename}'")

    # 3. Subscriber Configuration File (= media output paths, plus Kodi config in the case of agogo)
    if "agogo" not in store.name:
        out_config_paths_filename = f"{store.mediacopier_path}/config/Subscribers/config." + store.name + ".paths.yaml"
        if os.path.isfile(out_config_paths_filename):
            console.log("Config file already exists: " + out_config_paths_filename, style="warning")
        else:
            with open(out_config_paths_filename, 'w', encoding='utf-8') as out_config_paths_file:
                yaml.dump({'paths': {'tv_output_path': "", 'movie_output_path': ""}},
                          out_config_paths_file,
                          default_flow_style=False,
                          allow_unicode=True)

            console.log(f"Created '{out_config_paths_filename}'")

    console.log(f"Finished init for '{store.name}'.")
