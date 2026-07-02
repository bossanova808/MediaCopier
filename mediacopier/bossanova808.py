"""
Bossanova808 specific extra stuff that other folks should _not_ use...
"""

import subprocess

from base.console import console, log


def _rsync(label: str, src: str, dest: str, extra_args: list[str] | None = None):
    """Run an rsync command, logging the result. Warns on non-zero exit code."""
    args = ["rsync", "-avh", "--delete", "--progress", "--stats"] + (extra_args or []) + [src, dest]
    log(f"[green]{label}[/green]", indent=0)
    log(f"rsync {src} -> {dest}", indent=1)
    result = subprocess.run(args)
    if result.returncode != 0:
        log(f"rsync exited with code {result.returncode} — check output above", indent=1, style="danger")
    else:
        log(f"Done.", indent=1, style="info")


def do_b808_stuff():
    console.rule("Doing bossanova808 specific extra stuff!", style="danger")
    console.log("\nIf you're not bossanova808, you really should not be running this!!\n", style="danger")

    _rsync(
        "Update Kodi Agogo — Video Test Files",
        src="/mnt/hdd/mixed-shares/video/non-library-videos/Video Test Files",
        dest="/mnt/external/hdd/",
    )
    _rsync(
        "Update Kodi Agogo — Photo Library",
        src="/mnt/hdd/mixed-shares/Dropbox/Photos",
        dest="/mnt/external/hdd/",
        extra_args=["--exclude", "Thumbs.db"],
    )
    _rsync(
        "Update Kodi Agogo — Music Library",
        src="/mnt/nvme/music/",
        dest="/mnt/external/hdd/Music",
        extra_args=["--exclude", "Thumbs.db", "--exclude", "lost+found"],
    )

    console.rule('Finished bossanova808 specific extra stuff!')