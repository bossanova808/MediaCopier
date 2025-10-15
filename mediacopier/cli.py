import atexit
import click
import socket
from rich.traceback import install
from pathlib import Path

from . import config
from base.console import console
from .finish import finish_log
from models.store import store
from .agogo import do_agogo
from .clean import do_delete_watched, do_delete_lower_quality_duplicates
from .init import do_init
from .kodi import connect_to_kodi_or_die
from .update import do_update
from .bossanova808 import do_b808_stuff


@click.group()
@click.option('--pretend/--no-pretend', default=False, help="Pretend mode does nothing, but shows what would be done (AKA dry run)")
def cli(pretend):
    store.pretend = pretend


if socket.gethostname() == "jdcli":
    @cli.command(help="Run some other bossanova808 specific stuff - do NOT run if you're not bossanova808!")
    def b808():
        store.name = 'agogo'
        store.command = 'b808'
        config.load_media_library_paths()
        config.load_subscriber_paths()
        console.log(store)
        do_b808_stuff()


@cli.command(help="Remove watched tv episodes from an agogo drive")
def delete_watched():
    """Delete watched tv episodes from an agogo drive"""
    store.name = 'agogo'
    store.command = 'delete_watched'
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)
    connect_to_kodi_or_die()
    do_delete_watched()


@cli.command(help="Remove lower quality duplicates from a destination drive")
@click.argument('name', default='agogo')
def delete_dupes(name):
    """
    Remove any lower quality duplicates (S04E03 HDTV -> S04E03 WEB-DL Proper) that may exist on an agogo drive
    (Lower quality is determined by age, i.e. we let Sonarr make the replacement decisions in the source library and assume newer = better)
    """
    store.name = name
    store.command = 'delete_dupes'
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)
    do_delete_lower_quality_duplicates()


@cli.command(help="'Kodi Agogo' - Copy a media library of all unwatched media")
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
# @cli, not @click!
def agogo(limit_to):
    console.log(f'[green]Kodi Agogo[/green] - copying all unwatched media')
    store.name = 'agogo'
    store.command = 'agogo'
    store.set_media_limits(limit_to)
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)

    # Agogo & doing tv? Can we reach Kodi?
    # No point continuing with an agogo update if we can't...
    if store.update_tv:
        connect_to_kodi_or_die()
    do_agogo()


@cli.command(help="'Kodi Agogo (KIDS!)' - Copy a media library of all unwatched media")
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
# @cli, not @click!
def agogo_kids(limit_to):
    console.log(f'[green]Kodi Agogo (KIDS!)[/green] - copying all unwatched media')
    store.name = 'agogo_kids'
    store.command = 'agogo_kids'
    store.set_media_limits(limit_to)
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)

    # Agogo & doing tv? Can we reach Kodi?
    # No point continuing with an agogo update if we can't...
    if store.update_tv:
        connect_to_kodi_or_die()
    do_agogo(kids=True)


@cli.command(help="Initialise mediacopier configuration, for a given name")
@click.argument('name')
def init(name):
    """The name of the person to create configuration files for, e.g. laura or kathrex"""
    store.name = name
    store.command = 'init'
    config.load_media_library_paths()
    do_init()


@cli.command(help="Update a media library, for a given name")  # @cli, not @click!
@click.argument('name')
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
def update(name, limit_to):
    """The name of the person to run the update for, e.g. laura or kathrex"""
    console.log(f'[bold green]Update[/bold green] media library for: [yellow]{name}')
    store.name = name
    store.command = 'update'
    config.load_media_library_paths()
    config.load_subscriber_paths()
    store.set_media_limits(limit_to)
    do_update()


# @cli.command(hidden=True)
# def helper():
#     pass

# This is __main()__

# Rich exceptions...
# install(show_locals=True)
install()
# Preserve HTML logs for later debugging
atexit.register(finish_log)
# So we can use relative paths for results etc...
store.mediacopier_path = Path(__file__).parents[1]
# Let's get the party started...
console.print("\n\n")
console.rule("[bold red]Bossanova808 MediaCopier")
if socket.gethostname() == "HomeServer":
    console.log(f"Running on '{socket.gethostname()}'\n")
    store.bossanova808 = True
    console.log(">>> Bossanova808 mode engaged <<<\n", style="danger")
