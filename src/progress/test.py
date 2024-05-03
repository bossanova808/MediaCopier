import os
import random

import utils.utils
from copy_progress import CopyProgress
from rich.live import Live
from rich.text import Text
from console.console import console
from utils.copy_with_progress import copy_with_callback

MULTIPLIER = 0.01
progress: CopyProgress = CopyProgress()
live: Live

pretend_list = [
    "small",
    "medium",
    "large",
    "small",
    "medium",
    "large",
]


# Simulate a copy - do an actual file copy (with a progress callback), then delete that copy
def copy_current_file(name, size):
    out = f"{name}_out"
    progress.prep_current_file_progress(os.path.basename(name), size)
    copy_with_callback(name, out, progress.update_current_file_progress, 4*1024*1024)
    progress.complete_current_file()
    os.remove(out)


def copy_tv():

    random.shuffle(pretend_list)

    for tv_show in pretend_list:
        file_to_copy = f"test_copy/{tv_show}"
        size = os.stat(file_to_copy).st_size
        copy_current_file(file_to_copy, size)
        progress.update_overall_and_library_progress(size)

    progress.complete_current_library()


def copy_movies():

    random.shuffle(pretend_list)

    for movie in pretend_list:
        file_to_copy = f"test_copy/{movie}"
        size = os.stat(file_to_copy).st_size
        copy_current_file(file_to_copy, size)
        progress.update_overall_and_library_progress(size)

    progress.complete_current_library()


if __name__ == '__main__':

    total_to_copy = utils.utils.folder_size_in_bytes("test_copy")
    console.log(f"Total bytes to copy: {total_to_copy * 2}")
    progress.prep_overall_progress(total_to_copy * 2)
    live = Live(progress.layout)

    with live:
        progress.prep_library_progress("TV Shows", total_to_copy)
        copy_tv()
        progress.prep_library_progress("Movies", total_to_copy)
        copy_movies()

        progress.layout["upper"].size = 3
        progress.layout["lower"].update(Text("MediaCopier has finished!"))
