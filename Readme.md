# MediaCopier (for Kodi)

This tool is a **hacked together** Python script to try & make two common processes easier:

- You have a large media library (movies and TV shows), and you want to share this library (as files on a hard drive) - with your less technical friends/family on a regular basis ('subscriber updates')

- You want to take the unwatched portion of your own library with you on holidays - 'xbmc-agogo' if you will.  Paired with a small portable Kodi machine like, for example, an Odroid N2/+ running CoreElec, and using an external hard dive, you can have a very full Kodi experience anywhere you go that has an HDMI friendly TV.  Using the [trakt.tv](https://trakt.tv/) add-on, this 'agogo' process can even mark off all the stuff you watched on holiday so everything is hunky-dory with your library when you get home!)

### WARNING

This is _not_ really ready for prime time general public release.  

It's a rather situation specific hack and probably the worst code I have ever put out in public.  But - it will never delete anything, by design, so worst case scenario is it doesn't immediately work for you.  

It's designed to be taken by you and expanded upon/adapted for your own needs and *NO REAL SUPPORT OF ANY KIND IS OFFERED*.  You can post to the Kodi forums here: [https://forum.kodi.tv/showthread.php?tid=189144] - and I may try and help, but the general idea is that you'll get your hands dirty and make it work for you.  Or even better, get hacking and submit a pull request with improvements.

It's been tested only on Windows, only with my library, but I have myself been using it fairly comprehensively for about a decade.


## Subscriber Updates

This system basically lets your friends and family 'subscribe' to TV shows in your collection - they then just periodically bring/send their hard drive to you, and you run a fully automatic update which copies just the new episodes and/or selected new movies, that have entered your library since the last update.  

## Kodi Agogo - Copy All Unwatched Material

Alternatively it can inspect your current Kodi library, and grab all the as yet unwatched tv and/or movies from it, and send them to your holiday machine.

## Modes of Operation

There are three modes of operation available - the first two for subscriptions, and the 'agogo' mode for the special case of taking your own unwatched material on holiday:

- `init` : set up configuration files for a new subscriber
- `update` : actually copy the subscribed shows and/or new movies to that person's hard drive
- `agogo` : inspect your xbmc library and copy all unwatched stuff to a traveling machine/drive

Obviously, copying a LOT of media can take a significant amount of time.  It's best to first run things with the `--pretend` option to see what it _would_ do before you launch into the _actual_ copying.  

When using the `agogo` holiday mode, I typically leave it running overnight the night before we leave (and I just copy TV, and manually choose a few movies as my unwatched movie library is just too big!)


## Pre Requisites

A well organised and named media library - basically what you'd get out of a typical Sonarr/Radarr setup, using Kodi naming conventions of the `SXXEXX` type, and using season folders.  

It would be easy enough to add support for 1x06 type naming I think....but I haven't since I don't use that.

e.g.

TV
```
/TV Library 03/Carnivale/Season 01/Carnivale - S01E01 - Milfay.mkv
```

Movies
```
/Movie Library 02/Memento (2000)/Memento.mkv
```

Also, you should:

- Install Python3 (currently tested using Python 3.12)
- probably some python libs will need a `pip install` - stuff I can't think of right now - run it and remind me!
- If you're doing an `agogo` update where you need to copy only your unwatched TV and/or movies:
  Kodi running somewhere on your network (and with the correct profile selected & open, if you use profiles).  Also details of your Kodi JSON interface to this machine (so it can query your live Kodi for what is watched/not watched).


## SETUP

Clone this repo.  Then cd into the directory and run:

```
python mediacopier -h
```

...which gives you the command line help.

Next, configure the system by editing config/MediaCopier/config.yaml - follow the existing format but replace the paths with all your paths for Movies and TV shows.


### USING IT - For sharing with your friends

#### 1. INIT - initialise for a new person

```
python mediacopier init --name james
```

This will create config files for a user named james, and write them to config/Subscribers/ as
```
config.james.tv.txt
config.james.movies.txt
config.james.paths.yaml
```
It will set all shows to unsubscribed, and all movies to watched.  I.e. if you then run an update (see below) it won't actually copy anything at all at this point.

Now, edit the paths.yaml file and put in your output paths.  
On windows this looks something like:
```
paths:
  tv_output_path: U:/TV/
  movie_output_path: U:/Movies/
```
...where U: is drive letter for the destination hard drive.

Then, subscribe your friend to some shows by editing `config.name.tv.txt`.

You'll see in there that `showname|0|0` is a special case that means 'don't subscribe' to this show.

To subscribe them to a show from the very beginning, edit the entry to be `showname|1|0`, or if they are already watching the show, just use the last episode they have watched `showname|3|2` for season 3, episode 2 for example.  Just edit the list of shows, subscribing to any they want, from the episode they want.

For movies - simply delete any entries from the list you want to copy on this first run.  Later runs it will prompt you about all new movies one by one interactively when you do an update.

OK, now you should be ready to do your first update!


## 2. UPDATE

*I suggest you start with `--pretend` to see what it would have done without it actually copying anything!!*

Every time your friend wants an update, you do it like this:

```
python mediacopier.py update both --name james
```

(you can specify `both`, or just `tv`, or just `movies`)

The config files are inspected, and then you will be interactively prompted about any new shows and movies that have been added to the library since the last update run.  Just follow the prompts and add any new shows and movies you want to subscribe/copy since the last update.

Then, it will do its thing, and you should see a bunch of stuff flowing past and then files copying.  Fingers crossed, eh?

### Finishing an update session

Check everything copied ok to the destination drive/folders.  If all looks as you expect, it's time to close off this session.  MediaCopier has outputted some new config files in the `/results` folder.  You need to manually copy these to the `/config` folder (replacing the old ones) - once you're happy all went well.  These new config files record, say, that you are now up to S04E07...meaning next time you run an update, it only looks at new stuff.  (NB You don't need to do this for an agogo session, see below).

This step is not automated as we don't want to clobber your config in the event of an error. Also, sometimes your friend might drop off a hard drive for pick-up later in the week - you can run an update immediately to do the bulk of the copying, then when your friend actually picks up the drive you can quickly run another update to pick up any last remaining new things that have landed in your library in the interim.  In that case you'd move the new config files over after the last session of course.



### USING IT AGOGO - Copy unwatched items to your holiday machine

*You can also run agogo with `--pretend` to see what it would have done without it actually copying anything*

#### Running an actual `agogo` update

The agogo system basically inspects your Kodi install via JSON to create on-the-fly config files for above - you get subscribed to all TV shows with unwatched episodes from the point you are up to, and/or it can copy all your unwatched movies.

To set up, make sure `/config/Subscribers/config.agogo.yaml` is filled out with your details. It should look like something like this:

```
paths:
    tv_output_path: Y:/TV/
    movie_output_path: Y:/Movies/
xbmc:
    url: http://192.168.1.62/jsonrpc
    user: xbmc
    pass: xbmc
```

Then, you run it like this:

```
python mediacopier.py agogo both
```

(again, you can specify `both` or just `tv` or `movies`)

This will call out to Kodi for a list of your unwatched media, create on the fly config files for such (so a magic `init` if you will), and then trigger an update as above...it then copies all that stuff, and finally it will clean up the on-the-fly config files.  If you then run a library update on your take-away xbmc box, it should match the unwatched part of your library on your home Kodi system precisely.  Well, it does for me!


##### Auto Syncing your watched stuff when you get back

Assuming  you don't have internet where you're going, most likely when you get home you'll want to sync anything you have watched back you your master library to it's all marked off there automatically.

First, install trakt and sync your library to trakt.tv

Then, to auto mark off the watched stuff, simply plug in the agogo when you get home, and manually run the trakt add-on.  This will send all the newly watched stuff up to trakt.tv.  Then, manually run Trakt on your Kodi home machine, and it will mark all the stuff you watched on holidays as watched in your master library.  Done!

Once that is all done, it's best to wipe your hard drive, so you can start clean next time. MediaCopier never deletes anything, by design, so if you just keep updating your traveler machine it will overflow at some point.



### NOTES

If something goes wrong or whatever, or you decide you want to add another show/movies to the copy list, just run update again, and it essentially will resume from where it left off (that is, it knows the previously copied stuff exists, so it will skip it)

A _very_ comprehensive log is written to `/results/mediacopier.log`


### NOTES & KNOWN ISSUES

- If there is stuff for a series to copy, it also always copies the whole Season 00/Specials folder, just in case
- Will choke if your naming is dodgy (and by dodgy I mean any different to the above really - so currently no 1x06 support for example)
- If you run an update, then another a few days later and some of your episodes have been replaced with higher quality copies, you'll end up with both qualities on the destination.  I have plans to fix this at some point.
- Again - the real intention here is that you hack in to this yourself to make it work for you...it's just provided as an 'as is' thing that might be useful for others. 
