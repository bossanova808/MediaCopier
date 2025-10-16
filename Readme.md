# MediaCopier (for Kodi)

This tool is V2 of a **hacked together** Python script to try & make two common processes much easier:

- You have a large media library of movies and TV shows, and you would like to share this library (as files on a hard drive) - with your less technical friends/family on a regular basis ('subscriber updates').  (Yes, you could of course use various media serving programs to do the same thing more easily, but not all of us have wonderful internet or want to run a public/semi-public server)

- You want to take the unwatched portion of your own library with you on holidays - 'xbmc-agogo', if you will.  Paired with a small portable Kodi machine like, for example, an Odroid N2/+ running CoreElec, and using an external hard dive, you can have a very full Kodi experience anywhere you go that has an HDMI friendly TV.  Using the [trakt.tv](https://trakt.tv/) add-on, this 'agogo' process can even mark off all the stuff you watched on holiday so everything is hunky-dory with your library when you get home!)

**In early 2024** I re-factored MediaCopier pretty comprehensively, and added much better console output and logging (using the excellent Python library,  [Rich](https://github.com/Textualize/rich)).  There's even progress bars and ETA info when the actual copying is taking place - very useful, as of course copying large media libraries to external drives can take a while!

### :warning: Warning

> Whilst I have cleaned this up considerably in 2024, it is _still_ really a bit of a hack - just a starting point really, and is _not_ really ready for prime time general public release like a proper open source project would/should be.
> 
> It's a rather situation specific hack that works well for me (and has done so for over a decade now). Importantly - **it will never delete anything from your source library**, by design, so worst case scenario is it just doesn't immediately work for you or quite do what you want.
> 
> It's designed to be taken by you and expanded upon/adapted for your own needs.  You can post to the Kodi forums [here](https://forum.kodi.tv/showthread.php?tid=189144)...and I may try and help, but the general idea is that you'll get your hands dirty and make it work for yourself.  (Or even better, get hacking and submit a pull request with improvements!)
> 
> It's been tested thoroughly in actual use, but only on Windows, only with my own media library.  I have myself been using it fairly comprehensively...for over a decade now, so for my personal needs, it's pretty battle-tested at this point.

## Two Major Modes of Operation

### 1. Subscriber Updates

This system basically lets your friends and family 'subscribe' to TV shows in your collection - they then just periodically bring/send their hard drive to you, and you can run a fully automatic update which copies just the new episodes and/or selected new movies, that have entered your library since the last update.  

### 2. Kodi Agogo - Copy All Unwatched Material

Alternatively it can inspect your current Kodi library, and grab all the as yet unwatched tv and/or movies from it, and send them to your holiday machine.




## Prerequisites

A well-organised and well-named media library - basically what you'd get out of a typical Sonarr/Radarr setup, using Kodi naming conventions of the `SXXEXX` type, and using separate season folders.  

It would be easy enough to add support for 1x06 type naming I think....but I haven't as yet, since I don't use that.

e.g. here are some example paths/files:

TV
```
/TV Library 03/Carnivale/Season 01/Carnivale - S01E01 - Milfay.mkv
```

Movies
```
/Movie Library 02/Memento (2000)/Memento.mkv
```

- If you're doing an `agogo` update, i.e. where you want to copy only your unwatched TV and/or movies:
  Kodi must be running locally or somewhere reachable on your network (and with the correct Kodi profile selected & open, if you use profiles). 
- Details of your Kodi JSON interface to this machine (so it can query your live Kodi for what is watched/not watched).


## Using MediaCopier - Modes of Operation

There are actually three modes of operation available - the first two for friends and family subscriptions, and the 'agogo' mode for the special case of taking your own unwatched material on holiday:

- `init` : set up configuration files for a new subscriber
- `update` : actually copy the subscribed shows and/or new movies to that person's hard drive
- `agogo` : inspect your xbmc library and copy all unwatched stuff to a traveling machine/drive

Obviously, copying a LOT of media can take a significant amount of time, and you'll want to check everything is working as you expect.  Thus it's recommended to first run things with the `--pretend` option to see what it _would_ do before you launch into the _actual_ copying.  

When using the `agogo` holiday mode, I typically leave it running overnight the night before we leave (and I just copy TV, and manually choose a few movies as my unwatched movie library is just too big!)

## 'Installation'

You should have Python 3 (tested with 3.12) and pip installed.

Clone/download this repo.

The easiest way to get going is to use `uv` to install the project in editable form, as this takes care of dealing with the requirements/virtual environments etc. and you can explicitly set the Python version.

`uv tool install --python 3.12 -e  mediacopier`

...where `mediacopier` is a directory containg the repo's contents.

You may need to re-run this after adding/changing any CLI commands.

Or (this has not been tested in a while...) - if you prefer to use traditional Python virtual environments, then `cd` into the project's root folder and create a new virtual environment, then install the MediaCopier project in editable form, like so:

```bash
python -m venv .venv
.venv/bin/activate 
(or Windows: .\venv\Scripts\Activate)
pip install -e .
```

This should automatically install all dependencies to your virtual environment for you (click, rich, PyYaml, KodiPydent-alt etc).

Within that venv (or just everywhere, if you installed with `uv`) the `mediacopier` command should now be available.  

(If you're modifying things locally for your own needs, you can now go ahead and edit the MediaCopier source as much as you like - you'd only need to re-run this 'install' if you add new dependencies to the `pyproject.toml` file).

Next, configure your system by editing `config/MediaCopier/config.yaml` - follow the existing format but replace the paths with all your actual paths for Movies and TV shows.

### Updating Dependencies

`uv lock --upgrade` will update the dependcies mentioned in `pyproject.toml`

## Using MediaCopier

## Sharing media with your friends & family

### Initialise for a new person

```bash
mediacopier init james  
```

...or you can use the shorter command name:

```bash
mc init james  
```

This will create config files for a user named james, and write them to `config/Subscribers/` as
```
config.james.tv.txt
config.james.movies.txt
config.james.paths.yaml
```
It will set all shows to unsubscribed, and all movies to watched.  I.e. if you then run an update (see below) it won't actually copy anything at all at this point.

Now, edit the paths.yaml file and put in your output paths.  
On windows this might look something like:
```yaml
paths:
  tv_output_path: U:/TV/
  movie_output_path: U:/Movies/
```
...where `U:` is drive letter for the destination hard drive.

Then, subscribe your friend to some shows by editing `config.name.tv.txt` in any text editor.

You'll see in there that `showname|0|0` is a special case that means 'don't subscribe' to this show.

To subscribe them to a show from the very beginning, edit the entry to be `showname|1|0`, or if they are already watching the show, just use the last episode they have watched `showname|3|2` for season 3, episode 2 for example.  Just edit the list of shows, subscribing to any they want, from the episode they want.

For movies - simply delete any entries from the list you want to copy on this first run.  Later runs it will prompt you about all new movies that have been added to your library (since the last update) one by one interactively, when you later come to do an update.

OK, now you should be ready to do your first update!


### Copy Media

*I suggest you start with `--pretend` to see what it would have done without it actually copying anything!!*

Every time you want to run an update (i.e. copy new shows/episodes etc) - for your friend, you do it like this:

```bash
mc update james
```

By default, MediaCopier will consider both tv and moves.  But you can instead specify `--limit-to`, for just `tv`, or just `movies`:

```bash
 mc update --limit-to tv james
```


The config files are inspected, and then you will be interactively prompted about any new shows and movies that have been added to the library since the last update run.  Just follow the prompts and add any new shows and movies you want to subscribe/copy since the last update.

Then, it will do its thing, and you should see a bunch of stuff flowing past and then files copying.  Fingers crossed, eh?



### Finishing Up

Check everything copied ok to the destination drive/folders.  If all looks as you expect, it's time to close off this session.  MediaCopier has outputted some new config files in the `/results` folder.  You need to manually copy these to the `/config` folder (replacing the old ones) - once you're happy all went well (or write a little script to automate this).  

These new config files record, say, that you are now up to S04E07...meaning next time you run an update, it only looks at new stuff.  (NB You don't need to do this for an agogo session, see below).

This step is not automated as we don't want to clobber your config in the event of an error. Also, sometimes your friend might drop off a hard drive for pick-up later in the week - you can run an update immediately to do the bulk of the copying, then when your friend actually picks up the drive you can quickly run another update to pick up any last remaining new things that have landed in your library in the interim.  In that case you'd move the new config files over after the last session of course.



## MediaCopier Agogo (automatically copy unwatched media, for holiday use)

*You can also run agogo with `--pretend` to see what it would have done without it actually copying anything*

### Running an actual `agogo` update

The agogo system basically inspects your Kodi install via JSON to create on-the-fly config files for above - you get subscribed to all TV shows with unwatched episodes from the point you are up to, and/or it can copy all your unwatched movies.

To set up, make sure `/config/Subscribers/config.agogo.yaml` is filled out with your details. It should look like something like this:

```yaml
paths:
    tv_output_path: Y:/TV/
    movie_output_path: Y:/Movies/
xbmc:
    url: http://192.168.1.62/jsonrpc
    user: xbmc
    pass: xbmc
```

Then, you run it like this:

```bash
mc agogo
```

(again, you can specify `--limit-to` for just `tv` or `movies`)

This will call out to Kodi for a list of your unwatched media, create on the fly config files for such (so a magic `init` if you will), and then trigger an update as above...it then copies all that stuff, and finally it will clean up the on-the-fly config files.  If you then run a library update on your take-away xbmc box, it should match the unwatched part of your library on your home Kodi system precisely.  Well, it does for me!

Note - A full `agogo` update will in fact look more like this (see [Utilities](#utilities) below for details).

```bash
mc delete-watched
mc agogo
mc delete-dupes
```

## Utilities

MediaCopier has two useful utility commands (both can be run with `--pretend` to pre-flight their behaviour).

#### Deleting watched TV episodes  (for `agogo` scenario)

To remove watched TV episodes (e.g. to make space) - from an agogo drive, run:

`mc --delete-watched` 

This will query your Kodi install about the episodes on your agogo drive - any that Kodi has recorded as watched will be deleted.

#### Removing lower quality duplicates (for any subscriber, including `agogo`)

For any subscriber, including the `agogo` scenario, if you run regular agogo updates, it's possible that your downloader (e.g. Sonarr) has, in the meantime, found higher quality files for a show - so you might end up with e.g. both HDTV-1080p and Web-DL-1080p versions, or an original and a later proper, on the output drive.

This utility will find these duplicates and delete the older files (i.e. assuming that your downloader has made the right decision in obtaining the newer file...)

To remove lower quality duplicate videos, run:

`mc --delete-dupes`



### Auto Syncing your watched stuff when you get back

Assuming  you don't have internet available where you're going, most likely when you get home you'll want to sync anything you have watched back you your master library to it's all marked off there automatically.

First, install trakt and sync your library to trakt.tv

Then, to auto mark off the watched stuff, simply plug in the agogo machine when you get home, and manually run the trakt add-on.  This will send all the newly watched stuff up to trakt.tv.  Then, manually run Trakt on your Kodi home machine, and it will mark all the stuff you watched on holidays as watched in your master library.  Done!

Once that is all done, it's cleanest to wipe your agogo hard drive, so you can start clean next time. MediaCopier never deletes anything, by design, so if you just keep updating your traveler machine it will overflow at some point.  Or, use the new `delete-watched` command described above in [Utilities](#utilities).

## Notes & Known Issues

- A bunch of log files are written to `/results/xxx.log`
- If something goes wrong or whatever, or you decide you want to add another show/movie to the copy list, just run update again, and it essentially will resume from where it left off (that is, it knows the previously copied stuff exists, so it will just skip it)
- If there any episodes for a series to copy, it also always copies the **whole** Season 00/Specials folder, just in case there's a special that should be played within the timeline of the unwatched material
- Mediacopier will choke if your library file naming is dodgy (and by dodgy I mean any different to the above really - so currently no 1x06 support for example)


## Reminder...

Again, the real intention here is that you use this as a starting point, and hack in to this a bit yourself to make it work for you...it's just provided as an 'as is' thing that might be useful for others. 

I hope it proves useful for you!
