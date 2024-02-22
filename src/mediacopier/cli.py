import click
import atexit

from kodipydent import Kodi
from console.console import console
from data.store import store
from rich.traceback import install

from mediacopier import config
from mediacopier.agogo import do_agogo
from mediacopier.init import do_init
from mediacopier.update import do_update


# This is our tidy up function
# and save the recorded console output as a log file...
def at_exit():
    console.save_html("results/mediacopier.log.html")


def set_media_limits(limit_to):
    match limit_to:
        case 'tv':
            console.log("[red]Only TV will be updated[/red]")
            store.update_movies = False
        case 'movies':
            console.log("[red]Only Movies will be updated[/red]")
            store.update_tv = False
        case _:
            console.log("[green]Both TV & Movies will be updated[/green]")


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


@cli.command(help="'Kodi Agogo' - Copy a media library of all unwatched media, e.g. for a holiday")
@click.option('--limit-to', 'limit_to',
              help="Limit the library update to just tv or just movies",
              type=click.Choice(['movies', 'tv'], case_sensitive=False))
# @cli, not @click!
def agogo(limit_to):
    console.log(f'[green]Kodi Agogo[/green] - copying all unwatched media')
    store.name = 'agogo'
    set_media_limits(limit_to)
    config.load_media_library_paths()
    config.load_subscriber_paths()

    console.log(store)

    # Agogo & doing tv? Can we reach Kodi?
    # No point continuing with an agogo update if we can't...
    if store.update_tv:
        try:
            store.kodi = Kodi(hostname=store.kodi_ip,
                              port=store.kodi_jsonrpc_port,
                              username=store.kodi_username,
                              password=store.kodi_password)

        except Exception as e:
            console.log("Couldn't reach Kodi, exiting here", style="danger")
            console.print_exception(e)
            exit(1)

        json_result = store.kodi.JSONRPC.Ping()
        if json_result:
            console.log("Kodi json response:", style="info")
            console.log(json_result)
        if json_result and 'pong' in json_result['result']:
            console.log(":ping_pong: Successfully reached Kodi -> ping <> pong :ping_pong:", style='success')
        else:
            console.log("Couldn't reach Kodi, exiting here", style="danger")
            exit(1)

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

    set_media_limits(limit_to)
    do_update()


# Tidy-ups and save the console output to html
atexit.register(at_exit)

# Rich exceptions...
# install(show_locals=True)
install()

# & let's get the part started...
console.rule("[bold red]Bossanova808 MediaCopier")
