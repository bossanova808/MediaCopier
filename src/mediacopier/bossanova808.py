"""
Bossanova808 specific extra stuff that other folks should _not_ use...
"""

import os
from datetime import datetime

from console.console import console
from models.store import store


def do_b808_stuff():

    console.rule("Doing bossanova808 specific extra stuff!", style="danger")
    console.log("\nIf you're not bossanova808, you really should not be running this!!\n", style="danger")

    base = "D:"
    pre_command = "chcp 65001 & "

    console.log("[green]Update Kodi Agogo - Smart Playlists (Amy vs Jem shows etc.)")
    command = f'robocopy "F:\\Dropbox\\Computer-Stuff\\Kodi\\Shared-Config\\Adults\\playlists" "{base}\\Smart Playlists" /XF Thumbs.db /NDL /MIR'
    console.log(f"Executing: {command}\n", highlight=False)
    os.system(pre_command + command)

    console.log("[green]Update Kodi Agogo - Video Test Files")
    command = f'robocopy "O:\\Other Videos\\Video Test Files" "{base}\\Video Test Files" /XF Thumbs.db /NDL /MIR'
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


def finish_update():
    """
    Close off a mediacopier update by archiving the old config (just in case) and moving the new config, ready for the future
    """

    # With an agogo, the tv config file is deleted already...
    if store.name != 'agogo':
        answer = console.input(f"Close TV session for subscriber {store.name}? ([green]enter=yes[/green], [red]n=no[/red]) ")
        if not answer:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            os.rename(f"config/Subscribers/config.{store.name}.tv.txt", f"results/archive/{store.name}/config.{store.name}.tv.{now}.txt")
            os.rename(f"results/config.{store.name}.tv.txt", f"config/Subscribers/config.{store.name}.tv.txt")
            console.log(f"Archived old tv config & swapped in new for {store.name}")

    # ...but movies is handled the same as with any other subscriber
    answer = console.input(f"Close Movies session for subscriber {store.name}? ([green]enter=yes[/green], [red]n=no[/red]) ")
    if not answer:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.rename(f"config/Subscribers/config.{store.name}.movies.txt", f"results/archive/{store.name}/config.{store.name}.movies.{now}.txt")
        os.rename(f"results/config.{store.name}.movies.txt", f"config/Subscribers/config.{store.name}.movies.txt")
        console.log(f"Archived old movie config & swapped in new for {store.name}")

