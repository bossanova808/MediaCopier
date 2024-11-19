import os
import sys
from datetime import datetime

from base.console import console
from models.store import store


# Save the recorded console output as a log file when exiting
# Optionally, archive the log as well
def finish_log():
    console.rule("Archive the log file")
    print(os.getcwd())
    console.save_html("results/mediacopier.log.html")
    answer = console.input(f"Archive the log for this session for {store.name}? ([green]enter=yes[/green], [red]n=no[/red]) ")
    if not answer:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not os.path.exists(store.session_archive_path):
            os.makedirs(store.session_archive_path)
        out_file = f"{store.session_archive_path}/{now}.mediacopier.log.{'.'.join(sys.argv[1:])}.html"
        os.rename(f"results/mediacopier.log.html", out_file)
        console.log(f"Archived to: {out_file}", highlight=False)


def finish_update():
    """
    Close off a mediacopier update by archiving the old config (just in case) and moving the new config, ready for the future
    """

    # With an agogo, the tv config file is deleted already...
    if store.name != 'agogo':
        answer = console.input(f"Close TV session for subscriber {store.name}? ([green]enter=yes[/green], [red]n=no[/red]) ")
        if not answer:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if not os.path.exists(store.session_archive_path):
                os.makedirs(store.session_archive_path)
            os.rename(f"config/Subscribers/config.{store.name}.tv.txt", f"{store.session_archive_path}/{now}.config.{store.name}.tv.txt")
            os.rename(f"results/config.{store.name}.tv.txt", f"config/Subscribers/config.{store.name}.tv.txt")
            console.log(f"Archived old tv config & swapped in new for {store.name}")

    # ...but movies is handled the same as with any other subscriber
    answer = console.input(f"Close Movies session for subscriber {store.name}? ([green]enter=yes[/green], [red]n=no[/red]) ")
    if not answer:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not os.path.exists(store.session_archive_path):
            os.makedirs(store.session_archive_path)
        os.rename(f"config/Subscribers/config.{store.name}.movies.txt", f"{store.session_archive_path}/{now}.config.{store.name}.movies.txt")
        os.rename(f"results/config.{store.name}.movies.txt", f"config/Subscribers/config.{store.name}.movies.txt")
        console.log(f"Archived old movie config & swapped in new for {store.name}")
