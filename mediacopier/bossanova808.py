"""
Bossanova808 specific extra stuff that other folks should _not_ use...
"""

import os

from base.console import console
from models.store import store


def do_b808_stuff():

    console.rule("Doing bossanova808 specific extra stuff!", style="danger")
    console.log("\nIf you're not bossanova808, you really should not be running this!!\n", style="danger")

    base = store.tv_output_path.split("\\")[0]
    pre_command = "chcp 65001 & "

    console.log("[green]Update Kodi Agogo - Smart Playlists (Amy vs Jem shows etc.)")
    command = f'robocopy "F:\\Dropbox\\Computer-Stuff\\Kodi\\Shared-Config\\Adults\\playlists" "{base}\\Smart Playlists" /XF Thumbs.db /NDL /MIR'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(pre_command + command)

    console.log("[green]Update Kodi Agogo - Video Test Files")
    command = f'robocopy "F:\\Non Library Videos\\Video Test Files" "{base}\\Video Test Files" /XF Thumbs.db /NDL /MIR'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(pre_command + command)

    console.log("[green]Update Kodi Agogo - Photo Library")
    command = f'robocopy "F:\\Dropbox\\Photos" "{base}\\Photos" /XF Thumbs.db /NDL /MIR'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(pre_command + command)

    console.log("[green]Update Kodi Agogo - Music Library")
    command = f'robocopy "Z:\\Music" "{base}\\Music" /XF Thumbs.db /XD Playlists-Traveller /NDL /MIR'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(pre_command + command)

    console.rule(f'Finished bossanova808 specific extra stuff!')


