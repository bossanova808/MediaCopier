### MediaCopier (for XBMC)

This tool is a gross python hack script to try & make two common processes easier:

- You have a large media library (movies and TV shows), and you want to share this library with your friends/family 
- You want to take the unwatched portion of your own library with you on holidays - 'xbmc-agogo' if you will.  
   
   (Paired with a little NUC machine running [Openelec](http://openelec.tv/) and using an internal 1.5TB drive, you can have a very full XBMC experience anywhere you go that has an HDMI friendly TV.  Using the [trakt.tv](https://trakt.tv/) add-on, this agogo process can even mark off all the stuff you watched on holiday when you get back!)


This system basically lets your friends and family subscribe to TV shows - they then just periodically bring/send their hard drive to you, and you run a fully automatic update which copies all new episodes and/or selected movies since the last update.  Alternatively it can inspect your current XBMC library and grab all the unwatched tv and/or movies from it and send them to your holiday machine.

Thus, there are three modes of operation available - the first two for subscriptions, and the 'agogo' mode for the special case of taking your own unwatched material on holiday:

- init : set up configuration files for a new subscriber
- update : actually copy the subscribed shows and/or new movies to that person's hard drive
- agogo : inspect your xbmc library and copy all unwatched stuff to a traveling machine/drive

Obviously, copying a LOT of media can take a LOT of time.  It's best to run things with the `--pretend` option to see what it would do before you launch into actual copying.  When using the agogo holiday mode, I usually leave it running overnight the night before we leave (and I just copy TV, and manually choose a few movies as my unwatched movie library is just too big!)


### WARNING

This is not really ready for prime time.  

It's a bug ridden, rather situation specific hack and probably the worst code I have ever put out in public.  But - it will never delete anything, be design, so worst case scenario is it doesn't immediately work for you.  It's designed to be taken by you and expanded upon/adapted for your own needs and *NO REAL SUPPORT OF ANY KIND IS OFFERED*.  You can post to the XBMC forums here: [http://forum.xbmc.org/showthread.php?tid=189144] - and I may try and help, but the general idea is that you'll get your hands dirty and make it work for you.  Or even better, get hacking and submit a pull request with improvements.

It's been tested only on Windows, only with my library, but I have been using it fairly comprehensively for about two years now without issues.


### PREREQUISITES

A well organised and named media library - basically what you'd get out of Sickbeard and Couchpotato with XBMC naming conventions of the SXXEXX type, and season folders.  It would be easy enough to add support for 1x06 type naming I think.

e.g.

TV
```
/TV Library 03/Carnivale/Season 01/Carnivale - S01E01 - Milfay.mkv
```

Movies
```
/Movie Library 02/Memento (2000)/Memento.mkv
```

Also you should:

- Install Python 2.7 and make sure it's in your path
- pip install xbmc-json
- probably other stuff I can't think of right now - run it and remind me!
- If you're doing an 'agogo' update where you need to copy only your unwatched TV and/or movies:
  XBMC running (with the correct profile selected if you use profiles) & details of your JSON interface to it


### SETUP

Ok, clone this repo.  Then cd into the directory and run:

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
It will set all shows to unsubscribed, and all movies to watched.  I.e. if you then run an update (see below) it won't copy anything at this point

First, edit the paths.yaml file and put in your output files.  On windows this looks something like:
```
paths:
  tv_output_path: U:/TV/
  movie_output_path: U:/Movies/
```
...where U: is drive letter for the take-away hard drive.

Then, subscribe your friends to some shows.  You'll see that `showname|0|0` is a special case that means 'don't subscribe'.

So, to subscribe them from the very beginning, edit the entry to be `showname|1|0`, or if they are already into the show, just use the last episode they watched `showname|3|2` for season 3, episiode 2 for example.  Just edit the list of shows, subscribing to any they want, from the point they want.

For movies - just delete any entries from the list you want to copy on this first run.  Later runs it will prompt you about all new movies one by one interactively when you do an update.

OK, now you should be ready to do your first update!


#### 2. UPDATE

*You can run update with `--pretend` to see what it would have done without it actually copying anything*

#####  Making room for updates by auto-deleting watched stuff

*If you're running 'update' you can do this just before you do the actual update to remove wathced stuff*

Install [XBMC File Cleaner](http://wiki.xbmc.org/index.php?title=Add-on:XBMC_File_Cleaner) and configure it to run on demand rather than as a service.  Set up your delete parameters as needed.  Add the icon to your home screen (in skin settings) so it is easy to acesss.  Then, just run as needed before you do the steps below, to make room if required (if you don't do this, repeated update sessions will eventually fill up your drive).

##### Running an actual update

OK, every time your friend wants an update, you do it like this:

`
python mediacopier.py update both --name james
`
(you can specify 'both', 'tv', or 'movies')

The config files are inspected and then you will be interactively prompted about any new shows and movies that have been added to the library since the last update run.  Just follow the prompts and add any new shows and movies you want to subscribe/copy since the last update.

Then, it will do it's thing and you should see a whole bunch of stuff flowing past and then files copying.  Fingers crossed, eh?

##### Finishing an update session

Check everything copied ok to the destination drive/folders.  If all looks as you expect, it's time to close off this session.  MediaCopier has outputted some new config files in the `/results` folder.  You need to manually copy these to the `/config` folder (replacing the old ones) - once you're happy all went well.  These new config files record, say, that you are now up to S04E07...meaning next time you run an update, it only looks at new stuff.  (NB You don't need to do this for an agogo session, see below).

This step is not automated as we don't want to clobber your config in the event of an error. Also, sometimes your frend might drop off a hard drive for pick up later in the week - you can run an update immediately to do the bulk of the copying, then when your friend actually picks up the drive you can quickly run another update to pick up any last remaining new things that have landed in your library in the interim.  In that case you'd move the new config files over after the last session of course.



#### USING IT AGOGO - Copy unwatched items to your holiday machine

*You can run agogo with `--pretend` to see what it would have done without it actually copying anything*

#####  Making room for updates by auto-deleting watched stuff

- If you're running 'agogo', you can do this just before an agogo update - first run a manual trakt sync on your agogo machine to mark off anything on that machine you've watched since your last holiday, then then run XBMC File Cleaner, and then run your agogo update.  This will delete all the things you have watched, and then copy the new stuff over much more quickly than if you copy your entire unwatched library

Install [XBMC File Cleaner](http://wiki.xbmc.org/index.php?title=Add-on:XBMC_File_Cleaner) and configure it to run on demand rather than as a service.  Set up your delete parameters as needed.  Add the icon to your home screen (in skin settings) so it is easy to acesss.  Then, just run as needed before you follow the steps below

##### Running an actual agogo update

The agogo system basically inspects your XBMC install via JSON to create on-the-fly config files for above - you get subscribed to all TV shows with unwatched epsiodes from the point you are up to, and/or it can copy all your unwatched movies.

To setup, make sure `/config/Subscribers/config.agogo.yaml` is filled out with your details. It should look like something like this:

```
paths:
    tv_output_path: Y:/TV/
    movie_output_path: Y:/Movies/
xbmc:
    url: http://192.168.1.62/jsonrpc
    user: xbmc
    pass: xbmc
```

(in my case those paths are just pointing to the SMB shares from my openelec NUC machine which has an internal 1.5TB drive, that auto mount on my server whenever I plug the NUC in).

Then, you run it like this:

```
python mediacopier.py agogo both
```
(again, you can specify 'both' or just 'tv' or 'movies')

This will call out to XBMC and get your unwatched stuffs, create on the fly config files for such (so a magic init), and then trigger an update as above...it then copies all that stuff and finally it will clean up the on-the-fly config files.  If you then run a library update on your take-away xbmc box, it should match the unwatched part of your libray on your home xbmc system precisely.  Does for me!


##### Auto Syncing your watched stuff when you get back

Assuming  you don't have internet where you're going, most likely when you get home you'll want to sync anything you have watched back you your master library to it's all marked off there automatically.

First, install trakt and sync your library to trakt.tv

Then, to auto mark off the watched stuff, simply plug in the NUC when you get home, and manually run the trakt add-on.  This will send all the newly watched stuff up to trakt.tv.  Then, manually run trakt on your XBMC home machine and it will mark all the stuff you watched on holidays as watched in your master library.  Done!

Once that is all done, it's best wipe your NUC so you can start clean next time.  MediaCopier doesn't delete stuff, so if you just keep updating your traveler machine it will overflow at some point.



### NOTES

If something goes wrong or whatever, or you decide you want to add another show/movies to the copy list, just run update again and it essentially will resume from where it left off (that is, it knows the previously copied stuff exists so it will skip it)

A very comprehensive log is written to `/results/mediacopier.log`


### KNOWN ISSUES

Many, but mainly:
- Does not deal with specials in a specials/season 0 folder (it used to, but needs work, not quite sure what to do here )
- Will choke if your naming is dodgy (and by dodgy I mean any different to the above really - so currently no 1x06 support for example)
- Do not use special characters in show folders, like 'Agents of S.H.I.E.L.D.' - just use a folder named Agents of SHIELD instead
- If you run an update, then another a few days later and some of your episodes have been replaced with higher quality copies, you'll end up with both qualities on the destination.  I have plans to fix this at some point.
- Really this may not work for anyone else, ever, except me without a bit of hacking for your setup/library - but once done it is a HUGE time-saver if you're the main media person in your circle!!
