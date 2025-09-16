import os
import yaml
from base.console import console
from datetime import datetime
from models.store import store


def load_media_library_paths():
    """
    Load in the main MediaCopier config file that contains the list of paths for tv and movies:
    config/MediaCopier/config.library.paths.yaml
    Also set up the archive path for logging the results of a session
    """
    mediacopier_config = yaml.full_load(open(f"{store.mediacopier_path}/config/MediaCopier/config.library.paths.yaml"))
    store.tv_input_paths = mediacopier_config["tv_paths"]
    store.movie_input_paths = mediacopier_config["movie_paths"]
    store.session_archive_path = f'{store.mediacopier_path}/results/archive/{store.name}/{datetime.now().strftime("%Y-%m-%d")}'


def load_subscriber_paths():
    """
    Load in the subscriber config file containing the output paths &, if agogo, the Kodi details
    Create the output paths if they don't exist yet
    {store.mediacopier_path}/config/Subscribers/config.{store.name}.paths.yaml
    """
    subscriber_config_file = f"{store.mediacopier_path}/config/Subscribers/config.{store.name}.paths.yaml"
    loaded_config = yaml.full_load(open(subscriber_config_file))
    store.tv_output_path = loaded_config["paths"]["tv_output_path"]
    store.movie_output_path = loaded_config["paths"]["movie_output_path"]

    # Extra config for agogo
    if store.name == "agogo":
        store.kodi_ip = loaded_config["kodi"]["ip"]
        store.kodi_jsonrpc_port = loaded_config["kodi"]["jsonrpc_port"]
        store.kodi_username = loaded_config["kodi"]["username"]
        store.kodi_password = loaded_config["kodi"]["password"]

    # create the output folders if they don't already exist
    if not store.pretend:
        if not os.path.exists(store.tv_output_path):
            os.makedirs(store.tv_output_path)
        if not os.path.exists(store.movie_output_path):
            os.makedirs(store.movie_output_path)


def load_tv_and_movie_config():
    """
    Load in the tv subscription file, and seen movie list file, for this subscriber
    {store.mediacopier_path}/config/Subscribers/config.{store.name}.tv.txt
    {store.mediacopier_path}/config/Subscribers/config.{store.name}.movies.txt
    """
    if store.update_tv:
        config_filename = f"{store.mediacopier_path}/config/Subscribers/config.{store.name}.tv.txt"
        with open(config_filename, "r", encoding="utf-8") as config_file:
            store.tv_subscriptions = config_file.read().splitlines()
            store.tv_subscriptions_basic_show_list = [wanted.split('|')[0] for wanted in store.tv_subscriptions]
    if store.update_movies:
        config_filename = f"{store.mediacopier_path}/config/Subscribers/config.{store.name}.movies.txt"
        with open(config_filename, "r", encoding="utf-8") as config_file:
            store.unwanted_movies = config_file.read().splitlines()


def save_movie_config():
    """
    Save the updated movie subscription file
    {store.mediacopier_path}/config/results/config.{store.name}.movies.txt
    """
    console.rule("Writing updated movie subscription file")

    with open(f"{store.mediacopier_path}/results/config.{store.name}.movies.txt", "w", encoding='utf-8') as f:
        # noinspection PyTypeChecker
        for movie in sorted(store.movies_available, key=str.lower):
            movie_name = os.path.basename(movie)
            f.write(movie_name + "\n")

    console.log("Done.")


def save_tv_config():
    """
    Save the updated tv subscription file
    {store.mediacopier_path}/config/results/config.{store.name}.tv.txt
    """
    console.rule("Writing updated tv subscription file")

    with open(f"{store.mediacopier_path}/results/config.{store.name}.tv.txt", "w", encoding='utf-8') as f:

        # noinspection PyTypeChecker
        for output_show in sorted(store.output_show_list, key=str.lower):
            try:
                old_line = output_show + "|" + str(store.original_show_list[output_show][0]) + "|" + str(
                    store.original_show_list[output_show][1])
            except Exception:
                old_line = "[yellow]Show did not exist in old file"

            new_line = output_show + "|" + str(store.output_show_list[output_show][0]) + "|" + str(
                store.output_show_list[output_show][1])
            if old_line != new_line:
                console.log(f"[green]OLD: {old_line}")
                console.log(f"[cyan]NEW: {new_line}")
            f.write(new_line + "\n")

        # And log those shows removed from tracking
        if store.shows_not_matched_to_library:
            console.log("\n\nWARNING: These shows are no longer being tracked:", style="danger")
            for removed_show in store.shows_not_matched_to_library:
                console.log(removed_show)
            console.log("")

    console.log("Done.")
