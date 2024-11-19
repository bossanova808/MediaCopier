import os
import sys

from rich.live import Live
from rich.text import Text
from .console import console
from models.copy_item import CopyItem
from models.store import store
from progress.copy_progress import CopyProgress
from .utils import free_space_in_gigabytes
from .copy_with_progress import copy_with_callback, SameFileError



progress: CopyProgress = CopyProgress()
BYTES_TO_GB_FACTOR = 1024 * 1024 * 1024
COPY_BUFFER = 4 * 1024 * 1024


def copy_current_file(copy_item: CopyItem):
    progress.prep_current_file_progress(copy_item.file_name, copy_item.file_size)
    os.makedirs(copy_item.destination_folder, exist_ok=True)
    try:
        copy_with_callback(copy_item.source_file, copy_item.destination_file, progress.update_current_file_progress, COPY_BUFFER)
    except SameFileError:
        console.log("SameFileError!")
        pass

    progress.complete_current_file()


def copy_queue(queue):
    """
    Copy movies, showing a nice progress bar and updating the overall progress
    """

    if len(queue) == 0:
        console.log("COPY QUEUE IS EMPTY - We're done.")
        return

    # If we get here, we should do some actual copying!
    for potential_copy in queue:
        if not os.path.exists(potential_copy.destination_file) or os.path.getsize(potential_copy.destination_file) != os.path.getsize(potential_copy.source_file):
            copy_current_file(potential_copy)

    progress.complete_current_library()


def check_disk_space(tv_copy_queue, movie_copy_queue):
    """
    Does a basic check that we have enough room to do the copying.
    Saves a bunch of useful info about needed and available space to the store
    """

    if tv_copy_queue and store.update_tv and len(tv_copy_queue) > 0:
        store.tv_available_space_gb = free_space_in_gigabytes(store.tv_output_path)
        for tv_to_copy in tv_copy_queue:
            if not os.path.exists(tv_to_copy.destination_file) or os.path.getsize(tv_to_copy.destination_file) != os.path.getsize(tv_to_copy.source_file):
                store.tv_needed_space_bytes += tv_to_copy.file_size
        # convert bytes to GB
        store.tv_needed_space_gb = store.tv_needed_space_bytes / BYTES_TO_GB_FACTOR

        if store.tv_needed_space_gb > store.tv_available_space_gb:
            console.log(f"Not enough space for TV!!  Bailing out!  (Needed {store.tv_needed_space_gb} GB, Available {store.tv_available_space_gb} GB)", style="danger")
            sys.exit(1)

    if movie_copy_queue and store.update_movies and len(movie_copy_queue) > 0:
        store.movies_available_space_gb = free_space_in_gigabytes(store.movie_output_path)
        for movie_to_copy in movie_copy_queue:
            if not os.path.exists(movie_to_copy.destination_file) or os.path.getsize(movie_to_copy.destination_file) != os.path.getsize(movie_to_copy.source_file):
                store.movies_needed_space_bytes += movie_to_copy.file_size
        # convert to GB
        store.movies_needed_space_gb = store.movies_needed_space_bytes / BYTES_TO_GB_FACTOR

        if store.movies_needed_space_gb > store.movies_available_space_gb:
            console.log(f"Not enough space for Movies!!  Bailing out!  (Needed {store.movies_needed_space_gb} GB, Available {store.movies_available_space_gb} GB)", style="danger")
            sys.exit(1)

    store.total_needed_space_bytes = store.tv_needed_space_bytes + store.movies_needed_space_bytes
    store.total_needed_space_gb = store.total_needed_space_bytes / BYTES_TO_GB_FACTOR


def copy(tv_copy_queue, movie_copy_queue):

    console.rule("Now Copying Media")

    if store.pretend:
        console.log("PRETEND MODE - NO ACTUAL COPYING DONE", style="warning")
        return

    if len(tv_copy_queue) == 0 and len (movie_copy_queue) == 0:
        console.log("Nothing found in the queue to copy.", style="warning")
        return

    console.log("\n\n")

    progress.prep_overall_progress(store.total_needed_space_bytes)
    live = Live(progress.layout)

    with live:
        if store.update_tv:
            progress.prep_library_progress("TV Shows", store.tv_needed_space_bytes)
            copy_queue(tv_copy_queue)
        if store.update_movies:
            progress.prep_library_progress("Movies", store.movies_available_space_bytes)
            copy_queue(movie_copy_queue)

        # And, finally, we're done...
        progress.layout["upper"].size = 3
        progress.layout["lower"].update(Text("Copying has finished!"))
