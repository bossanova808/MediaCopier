import atexit
import click
from rich.traceback import install

from console.console import console
from data.store import store
from mediacopier import config
from mediacopier.agogo import do_agogo
from mediacopier.clean import do_delete_watched, do_delete_lower_quality_duplicates
from mediacopier.init import do_init
from mediacopier.kodi import connect_to_kodi_or_die
from mediacopier.update import do_update


# Save the recorded console output as a log file when exiting
def at_exit():
    console.save_html("results/mediacopier.log.html")


@click.group()
@click.option('--pretend/--no-pretend', default=False)
def cli(pretend):
    store.pretend = pretend


@cli.command(help="Initialise mediacopier configuration for a given name")
@click.argument('name')
def init(name):
    """The name of the person to create configuration files for, e.g. laura or kathrex"""
    store.name = name
    config.load_media_library_paths()
    do_init()


@cli.command(help="Remove watched tv episodes from an agogo drive")
def delete_watched():
    """Delete watched tv episodes from an agogo drive"""
    store.name = 'agogo'
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)
    connect_to_kodi_or_die()
    do_delete_watched()


@cli.command(help="Remove lower quality duplicates from an agogo drive (S04E03 HDTV -> S04E03 WEB-DL Proper etc)")
def delete_dupes():
    """
    Remove any lower quality duplicates (S04E03 HDTV -> S04E03 WEB-DL Proper) that may exist on an agogo drive
    (Lower quality is determined by age, i.e. we let Sonarr make the replacement decisions in the source library and assume newer = better)
    """
    store.name = 'agogo'
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)
    do_delete_lower_quality_duplicates()


@cli.command(help="'Kodi Agogo' - Copy a media library of all unwatched media, e.g. for a holiday")
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
# @cli, not @click!
def agogo(limit_to):
    console.log(f'[green]Kodi Agogo[/green] - copying all unwatched media')
    store.name = 'agogo'
    store.set_media_limits(limit_to)
    config.load_media_library_paths()
    config.load_subscriber_paths()
    console.log(store)

    # Agogo & doing tv? Can we reach Kodi?
    # No point continuing with an agogo update if we can't...
    if store.update_tv:
        connect_to_kodi_or_die()
    do_agogo()


@cli.command(help="Update a media library for a given name")  # @cli, not @click!
@click.argument('name')
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
def update(name, limit_to):
    """The name of the person to run the update for, e.g. laura or kathrex"""
    console.log(f'[bold green]Update[/bold green] media library for: [yellow]{name}')
    store.name = name
    config.load_media_library_paths()
    config.load_subscriber_paths()
    store.set_media_limits(limit_to)
    do_update()


# This is __main()__
# Tidy-ups and save the console output to html
atexit.register(at_exit)
# Rich exceptions...
# install(show_locals=True)
install()
# Let's get the party started...
console.print("\n\n")
console.rule("[bold red]Bossanova808 MediaCopier")
