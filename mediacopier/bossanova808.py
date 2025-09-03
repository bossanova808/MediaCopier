"""
Bossanova808 specific extra stuff that other folks should _not_ use...
"""

import os

from base.console import console
from models.store import store


def do_b808_stuff():

    console.rule("Doing bossanova808 specific extra stuff!", style="danger")
    console.log("\nIf you're not bossanova808, you really should not be running this!!\n", style="danger")

    console.log("[green]Update Kodi Agogo - Video Test Files")
    command = 'rsync -avh --delete --progress --stats "/mnt/hdd/mixed-shares/video/non-library-videos/Video Test Files" "/mnt/external/hdd/"'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(command)

    console.log("[green]Update Kodi Agogo - Photo Library")
    command = 'rsync -avh --delete --progress --stats --exclude "Thumbs.db" "/mnt/hdd/mixed-shares/Dropbox/Photos" "/mnt/external/hdd/"'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(command)

    console.log("[green]Update Kodi Agogo - Music Library")
    command = 'rsync -avh --delete --progress --stats --exclude "Thumbs.db" --exclude "lost+found"  "/mnt/nvme/music/" "/mnt/external/hdd/Music"'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(command)

    console.rule(f'Finished bossanova808 specific extra stuff!')


