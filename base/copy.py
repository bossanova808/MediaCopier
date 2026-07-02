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
COPY_BUFFER = 16 * 1024 * 1024


def copy_current_file(copy_item: CopyItem):
    progress.prep_current_file_progress(copy_item.file_name, copy_item.file_size)
    os.makedirs(copy_item.destination_folder, exist_ok=True)
    try:
        copy_with_callback(copy_item.source_file, copy_item.destination_file, progress.update_current_file_progress, COPY_BUFFER,
                           speed_limit_mbps=store.active_speed_limit_mbps)
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
    # _needs_copy is set by check_disk_space to avoid re-stating destination files.
    # Fall back to a fresh stat check if check_disk_space wasn't called (e.g. pretend mode).
    for potential_copy in queue:
        needs_copy = getattr(potential_copy, '_needs_copy', None)
        if needs_copy is None:
            dest_size = os.path.getsize(potential_copy.destination_file) if os.path.exists(potential_copy.destination_file) else -1
            needs_copy = dest_size != potential_copy.file_size
        if needs_copy:
            copy_current_file(potential_copy)

    progress.complete_current_library()


def check_disk_space(tv_copy_queue, movie_copy_queue):
    """
    Does a basic check that we have enough room to do the copying.
    Saves a bunch of useful info about needed and available space to the store
    """

    if tv_copy_queue and store.update_tv and len(tv_copy_queue) > 0:
        store.tv_available_space_gb = free_space_in_gigabytes(store.tv_output_path)
        for item in tv_copy_queue:
            # Use the file_size already stored on the CopyItem (set when the queue was built)
            # rather than re-stating the source file. Only count files not already fully copied.
            dest_size = os.path.getsize(item.destination_file) if os.path.exists(item.destination_file) else -1
            if dest_size != item.file_size:
                store.tv_needed_space_bytes += item.file_size
                item._needs_copy = True
            else:
                item._needs_copy = False
        store.tv_needed_space_gb = store.tv_needed_space_bytes / BYTES_TO_GB_FACTOR

        if store.tv_needed_space_gb > store.tv_available_space_gb:
            console.log(f"Not enough space for TV! (Needed {store.tv_needed_space_gb:.2f} GB, Available {store.tv_available_space_gb:.2f} GB)", style="danger")
            sys.exit(1)

    if movie_copy_queue and store.update_movies and len(movie_copy_queue) > 0:
        store.movies_available_space_gb = free_space_in_gigabytes(store.movie_output_path)
        for item in movie_copy_queue:
            dest_size = os.path.getsize(item.destination_file) if os.path.exists(item.destination_file) else -1
            if dest_size != item.file_size:
                store.movies_needed_space_bytes += item.file_size
                item._needs_copy = True
            else:
                item._needs_copy = False
        store.movies_needed_space_gb = store.movies_needed_space_bytes / BYTES_TO_GB_FACTOR

        if store.movies_needed_space_gb > store.movies_available_space_gb:
            console.log(f"Not enough space for Movies! (Needed {store.movies_needed_space_gb:.2f} GB, Available {store.movies_available_space_gb:.2f} GB)", style="danger")
            sys.exit(1)

    store.total_needed_space_bytes = store.tv_needed_space_bytes + store.movies_needed_space_bytes
    store.total_needed_space_gb = store.total_needed_space_bytes / BYTES_TO_GB_FACTOR


def copy(tv_copy_queue, movie_copy_queue):
    console.rule("Now Copying Media")

    if store.pretend:
        console.log("PRETEND MODE - NO ACTUAL COPYING DONE", style="warning")
        return

    if len(tv_copy_queue) == 0 and len(movie_copy_queue) == 0:
        console.log("Nothing found in the queue to copy.", style="warning")
        return

    console.log("\n\n")

    progress.prep_overall_progress(store.total_needed_space_bytes)
    live = Live(progress.layout, refresh_per_second=1)

    with live:
        if store.update_tv:
            progress.prep_library_progress("TV Shows", store.tv_needed_space_bytes)
            copy_queue(tv_copy_queue)
        if store.update_movies:
            progress.prep_library_progress("Movies", store.movies_needed_space_bytes)
            copy_queue(movie_copy_queue)

        # And, finally, we're done...
        progress.layout["upper"].size = 3
        progress.layout["lower"].update(Text("Copying has finished!"))
