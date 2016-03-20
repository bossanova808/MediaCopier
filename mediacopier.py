import os, sys, re, shutil, datetime, argparse, logging, json, yaml, pprint
from xbmcjson import XBMC
from traceback import format_exc
from utils import utils

def set_up_logging():
    """ Sets up logging - all messages go to the log file, and info and higher to the console """

    logging.basicConfig(level=logging.DEBUG,
                        filename='results/mediacopier.log',
                        format='[%(asctime)s] %(name)-12s: %(levelname)-8s %(message)s', 
                        datefmt='%Y-%m-%d %I:%M:%S %p')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

def interpret_command_line_arguments():
    """ Parse and return a dictionary of the command line arguments (also sets up the argument documentation) """

    global args

    logging.debug("Parsing Command Line Args")

    parser = argparse.ArgumentParser(description='A subscription interface for video libraries')
    parser.add_argument('mode', choices=['init', 'update', 'agogo'], help="init sets up configuration files for a new person, update updates from a configuration file, agogo updates based on an xbmc library intead of configuration files")
    parser.add_argument('update', choices=['tv', 'movies', 'both'], help="tv - just work on TV shows, movies - just work on movies, both updates both tv shows and movies")
    parser.add_argument('-p', '--pretend', help="Run in pretend mode - will log what would have happened, but not actually copy anything", action="store_true")
    parser.add_argument('-n', '--name', help="Name of person to update - used with init & update mode only")
    parser.add_argument('-c', '--clean', help="Remove (i.e. DELETE) watched material from the destination during an update or agogo")

    args = parser.parse_args()

def load_master_config():
    """ Loads the yaml config file from config/MediaCopier/config.yaml"""

    global config

    logging.info( "Loading configuration from config/MediaCopier/config.yaml" )
    try:
        config = yaml.load(open("config/MediaCopier/config.yaml"))
        logging.info("\nRead in configuration:\n" + pprint.pformat(config))
    except Exception as inst:
        logging.error("Exception raised while reading MediaCopier configuration file: " + format_exc(inst))

def load_config_for_agogo():
    """
    Read in config/Subscribers/config.agogo.yaml into user_config
    """

    config_filename = "config/Subscribers/config.agogo.yaml"
    config_file = open(config_filename)
    logging.info("Loading config " + config_filename)

    try:
        #read it in            
        user_config.update(yaml.load(config_file))
        config_file.close()
    except Exception as inst:
        logging.error("Exception raised while reading agogo configuration file: " + config_filename + "\n" + format_exc(inst))
        sys.exit()



def load_config_for_name(name):
    """
    Loads the config files for the user into user_config
    Special case is user 'agogo' supplied
    """

    global user_config
    global args


    if args.update=="tv" or args.update=="both":
        config_filename = "config/Subscribers/config." + name + ".tv.txt"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)

        try:
            #read it in
            user_config['tv_wanted_list'] = config_file.read().splitlines()
            user_config['basic_show_list'] = [wanted.split('|')[0] for wanted in user_config['tv_wanted_list']]
            config_file.close()
        except Exception as inst:
            logging.error("Exception raised while reading tv configuration file: " + config_filename + "\n" + format_exc(inst))
            sys.exit()



    if args.update=="movies" or args.update=="both":
        config_filename = "config/Subscribers/config." + name + ".movies.txt"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)

        try:
            user_config['movies_to_ignore'] = config_file.read().splitlines()
            config_file.close()
        except Exception as inst:
            logging.error("Exception raised while reading movie configuration file: " + config_filename + "\n" + format_exc(inst))
            sys.exit()

    # if init or update, load the output paths (with agogo this has already been loaded from yaml config file)
    if args.mode!="agogo":
        config_filename = "config/Subscribers/config." + name + ".paths.yaml"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)
 
        try:
            #read it in            
            user_config.update(yaml.load(config_file))
            #create output folders if they don't exist
            if not os.path.exists(user_config['paths']['tv_output_path']):
                os.makedirs(user_config['paths']['tv_output_path'])
            if not os.path.exists(user_config['paths']['movie_output_path']):
                os.makedirs(user_config['paths']['movie_output_path'])
            config_file.close()
        except Exception as inst:
            logging.error("Exception raised while reading paths configuration file: " + config_filename + "\n" + format_exc(inst))
            sys.exit()
    

    #dump all the user_config info for debugging purposes
    logging.info("Config all loaded as:\n" + pprint.pformat(user_config))



def set_up_new_person(name, latest_episodes=None, watched_movies=None):
    """ 
    Sets up a new subscriber to the library by creating the tv.name.txt and movies.names.txt config files
    Can be in two ways  - just initialisation, in which case the config files created are all movies seen/tvshow|0|0 - i.e. don't want this show
                        - with a list of latestEpisodes which should have in it the names of the latest watched episodes for all shows with unwatched episodes remaining

    """

    global user_config
    global config

    if args.update =="tv" or args.update =="both":
        #create the 3 config files - one for tv, paths, and optionally one for movies if we're not
        out_config_tv_filename = "config/Subscribers/config." + name + ".tv.txt"
  
        answer = ""
        create_file = True

        #don't clobber existing files by accident
        if os.path.isfile(out_config_tv_filename):
            logging.error("TV config file already exists: " + out_config_tv_filename)
            create_file = False
            answer = raw_input("Over write existing config file [x] or use the existing file [enter]?")

        if create_file or answer.lower()=="x" or args.mode=="init":

            out_config_tv_file = open(out_config_tv_filename, 'w')

            # DO TV SHOW ZERO LIST
            tv_show_list = []

            for d in config['tv_paths']:
                temp = utils.listdirPaths(d)
                for a in temp:
                    tv_show_list.append(os.path.basename(a))

            logging.debug("\nTV show list is: \n" + pprint.pformat(tv_show_list))


            if latest_episodes is None:
                logging.info("Setting all TV shows to unwanted in created config file")
                for show in sorted(tv_show_list):
                   out_config_tv_file.write( show + "|0|0\n")

            else:            
                logging.info("Processing latest episodes list (creating on-the-fly a-go-go config)")
                for show in sorted(tv_show_list):
                    logging.debug("Processing: " + show)
                    #check if there is a latest watched episode for this how
                    if show not in latest_episodes:
                        logging.debug(show + " was not found to have a latest watched epsiode - set to unwanted")
                        user_config[show] = {'season':0,'episode':0}
                        out_config_tv_file.write( show + "|0|0\n")
                    else:
                        logging.debug( show + " has a latest watched episode of " + str(latest_episodes[show]["season"]) + "|" + str(latest_episodes[show]["episode"]))
                        #we're creating an output file for aGoGo machine so get the latest wathched episode and record the previous episode 
                        #in the config file as the last one copied
                        outEpNum = int(latest_episodes[show]["episode"])
                        #the config file stores the latest watched episode - so we have to take one off the unwatched episode number
                        if outEpNum > 0:
                            outEpNum = outEpNum - 1
                        
                        out_config_tv_file.write( show + "|" + latest_episodes[show]["season"] + "|" + str(outEpNum) + "\n")
             
            out_config_tv_file.close()      

    # DO MOVIE LIST & BATCH FILE IF WE'RE NOT UPDATING AN aGoGO Machine
    # i.e. with aGoGo machines we don't currenly do anything with movies, we manually copy those

    if args.update =="movies" or args.update =="both":

        out_config_movies_filename = "config/Subscribers/config." + name + ".movies.txt"

        answer=""
        #don't clobber existing files by accident
        if os.path.isfile(out_config_movies_filename):
            logging.error("Movie config file already exists " + out_config_movies_filename)
            answer = raw_input("Over write existing config file [x] or use the existing file [enter]?")
            
        if answer.lower()=="x" or args.mode=="init":
            out_config_movies_file = open(out_config_movies_filename, 'w')
            #not doing agogo, so build watched_movies now
            if watched_movies is None:
                logging.info("Setting all movies to seen in created config file")
                watched_movies = []

                for d in config['movie_paths']:
                    temp = utils.listdirPaths(d)
                    for a in temp:
                        watched_movies.append(os.path.basename(a))

            logging.debug("\nSeen Movies is: \n" + pprint.pformat(watched_movies))

            for movie in sorted(watched_movies):
                out_config_movies_file.write(movie + "\n")

            out_config_movies_file.close()


    # DO PATHS
    #create empty paths in all cases

    if args.mode!="agogo":
        out_config_paths_filename = "config/Subscribers/config." + name + ".paths.yaml"
        if os.path.isfile(out_config_paths_filename):
            logging.error("Config file already exists: " + out_config_paths_filename)
        else:
            out_config_paths_file = open(out_config_paths_filename, 'w')
            user_config['paths'] = {'tv_output_path': "", 'movie_output_path': ""}
            yaml.dump(user_config, out_config_paths_file, default_flow_style=False,allow_unicode=True)
            out_config_paths_file.close()



def xbmc_agogo():
    """ 
    Create the on-the-fly config files for an agogo update
    """

    global config
    global user_config
    global args

    #load the agogo config
    load_config_for_agogo()

    #Login with custom credentials
    xbmc = XBMC(user_config["xbmc_source"]["url"], user_config["xbmc_source"]["user"], user_config["xbmc_source"]["pass"])
    print xbmc.JSONRPC.Ping()

    seen_movies = None
    latest_episodes = None

    if args.update=="tv" or args.update=="both":

        latest_episodes={}
        result = xbmc.VideoLibrary.GetTVShows( {"filter": {"field": "playcount", "operator": "is", "value": "0"}})
        showsWithUnwatched = result["result"]["tvshows"]
        for show in showsWithUnwatched:
            #print "******" + show["label"]
            result = xbmc.VideoLibrary.GetEpisodes({"tvshowid": show["tvshowid"], "sort": {"order": "ascending", "method": "episode"}, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}})
            unwatchedEpisodes = result["result"]["episodes"]
            #for episode in unwatchedEpisodes:
            #    print episode["label"]
            #3x07. MagicHour (2)
            cut = unwatchedEpisodes[0]["label"].split(".",1)
            episodeString = cut[0]
            parts = episodeString.split("x")
            try:
                seasonNumber = parts[0]
                episodeNumber = parts[1]
            #Deal with specials returned as S09
            except:
                seasonNumber = "0";
                episodeNumber = (parts[0])[1:]
            #xbmc returns nice full show names but windows doesn't like special characters in paths
            #so remove the problem chars here to match the folder names
            cleanedEpisodeName = show["label"].replace(":","")
            cleanedEpisodeName = cleanedEpisodeName.replace(".","")
            latest_episodes[cleanedEpisodeName]=({"season":seasonNumber,"episode":episodeNumber})


    # if args.update=="movies" or args.update=="both":
    #     seen_movies = []
    #     # @TODO ADD GET XBMC WATCHED MOVIES HERE!!! Can we get actual path for better folder matching??
    #     result = xbmc.VideoLibrary.GetMovies( {"filter": {"field": "playcount", "operator": "greaterthan", "value": "0"}})
    #     movies_unwatched = result["result"]["movies"]
    #     #pprint.pprint(movies_unwatched)
    #     for movie in sorted(movies_unwatched):
    #         #print("******* WATCHED: " + str(movie) + str(movie['movieid']))
    #         result = xbmc.VideoLibrary.GetMovieDetails( {"movieid": int(movie['movieid']), "properties": ['file']})
    #         #pprint.pprint(result)
    #         uri = result['result']['moviedetails']['file']
    #         parts = uri.split('/')
    #         folder = parts[-2]
    #         #DVDs have folders in them....
    #         if folder.lower()=="video_ts":
    #             folder = parts[-3]
    #         seen_movies.append(folder.encode("utf-8"))
            


    #latest_episodes is a list of dicts with the above keys conatining the latest unwatched episodes
    #seen_movies is a list of all movies that have been watched
    #call set up new person with these lists
    if latest_episodes is not None:
        logging.debug("Latest watched episodes list is:\n" + pprint.pformat(latest_episodes))
    if seen_movies is not None:
        logging.debug("Seen Movies list is:\n" + pprint.pformat(seen_movies))

    set_up_new_person("agogo", latest_episodes, seen_movies)



def build_show_lists():
 
    global user_config

    #will store our list of shows found in the TV paths
    show_list = []
    #and a list to hold new shows found
    new_show_list = []

    for d in config['tv_paths']:
        shows_in_this_path = os.listdir(d)
        logging.info( d + " contains:\n" + str(shows_in_this_path) )
        for show_in_this_path in shows_in_this_path:
            show_path = d + "\\" + show_in_this_path
            if os.path.isdir(show_path):
                show_list.append(show_path)
                if show_in_this_path not in user_config['basic_show_list']:
                    new_show_list.append(show_path)
            else:
                logging.warning(show_in_this_path + " - not a directory.")
       
    return show_list, new_show_list


def update_subscriber_tv(name):
    """ Do a library update for a subscriber """

    global config
    global user_config
    global args
    global outputPaths
    global tv_copy_queue
    global unfound_shows
    global original_show_list


    ##############################################################################
    # build a list of all available tv shows, and 

    show_list, new_show_list = build_show_lists()
 
    ################################################################################
    logging.info( str(len(user_config['basic_show_list'])) + " AVAILABLE SHOWS" )
    for show in sorted(user_config['basic_show_list'], key=str.lower):
        logging.debug( os.path.basename(show) )

    if len(new_show_list)>0:
        logging.debug( str(len(new_show_list)) + " NEW SHOWS FOUND:" )
        for show in new_show_list:
            logging.debug( os.path.basename(show) )

    logging.info( "ADD ANY NEW SHOWS INTERACTIVELY" )

    #add new shows?
    for show in new_show_list:
        print ""
        answer = raw_input("Add new TV show " + show + " to copy list (return = no, y = yes)")
        if (not answer) or answer=="n" or answer=="N":
            print (show + " - Not Added, set to 0|0 in output_show_list")
            logging.debug  (show + " - Not Added, set to 0|0 in output_show_list")
            output_show_list[os.path.basename(show)] = [0,0]
        else:
            print show + " - Added "
            logging.info  (show + " - Added")
            user_config['tv_wanted_list'].append(os.path.basename(show) + "|1|0\n")

    ################################################################################


    logging.info( "NOW PROCESSING EACH WANTED SHOW" )

    #ok for each wanted show...
    for wanted in user_config['tv_wanted_list']:

        # Parse config file
        try:
            wanted_show, wanted_season, wanted_episode = wanted.split('|')
            wanted_season_int = int(wanted_season)
            wanted_season = format(wanted_season_int, "02d")
            wanted_episode = int(wanted_episode)
        except Exception as inst:
            logging.error("Problem in config: " + wanted + " " + format_exc(inst))
            sys.exit()

        #record where we started
        original_show_list[wanted_show] = [wanted_season_int,wanted_episode]

        #######################
        #skip if set to 0,0
        if wanted_season_int == 0 and wanted_episode == 0:
            logging.info( "Show: " + wanted_show + " set to 0|0 -> skip it")
            original_show_list[wanted_show] = [0,0]
            output_show_list[wanted_show] = [0,0]
            #print outputShowList
            #go back to the top of the loop for the next show
            continue

        #######################
        #otherwise start processing
        logging.info( "Show: Wanted name: " + wanted_show + " - Wanted Series: " + str(wanted_season) + " - Wanted Epsiode: " + str(wanted_episode) )

        found_show = False
        output_folder = ""
        origin_folder = ""

        ############
        #do we recognise this show?
        for possible_show in show_list:
            if wanted_show in possible_show:
                output_folder = os.path.join(user_config['paths']['tv_output_path'], wanted_show)
                origin_folder = possible_show
                found_show = True
                break;

        #show is not in the available list
        if not found_show:
            logging.error ( "WARNING: SHOW NOT FOUND - so added to unfound list" )
            unfound_shows.append(wanted_show)
        # we found it, so let's maybe copy some stuff
        else:
            logging.info( "Show: From: " + origin_folder )
            logging.info( "Show: To:   " + output_folder )

            #ok so the show is available and we want some of it.  Let's find out if there are new episodes?
            start_season_int =  int(wanted_season)
            start_season_folder = origin_folder +"\\Season " + wanted_season
            start_season_folder_output = output_folder +"\\Season " + wanted_season

            #set up for loop
            current_season_folder = start_season_folder
            current_season_folder_output = start_season_folder_output
            current_season_int = start_season_int
            episode_considering = 0

            season_folder_exists = True
            found_new_episode = False

            #we loop through each season until we can't find another season
            while season_folder_exists:
                if os.path.exists(current_season_folder):
                    #the season folder exists
                    logging.info( "Show: Handling " + os.path.basename(current_season_folder) )

                    #make a list of files in the current season
                    current_season_files = utils.listdirPaths(current_season_folder)

                    #ok so now we want to match only the wanted episode and above and add them to the copy queue
                    #keep track of them for logginh
                    episodes_added = []
                    #and a queue to store files like folder.jpg that we will only copy if we found at least 1 new ep.
                    possible_queue = []

                    for current_season_file in current_season_files:
                        #match the SXXEXX part of the filename
                        p = re.compile('S[0-9]*E[0-9]*')
                        match = p.search(current_season_file)
                        if match:
                            episode_string = match.group()
                            #logging.info( "episodeString is " + episodeString
                            episode_considering = int(episode_string[4:6])
                            if episode_considering > wanted_episode:
                                found_new_episode = True
                                if episode_string not in episodes_added:
                                    episodes_added.append(episode_string)
                                #logging.info("Show: Episode " + str(episodeConsidering) + " file is newer than " + str(wantedEpisode) +", adding to queue")
                                tv_copy_queue.append([current_season_file, current_season_folder_output])
                            #else:
                                #logging.info("Show: Episode " + str(episodeConsidering) + " file is older/same than " + str(wantedEpisode) +", not adding")

                        else:
                            logging.info( "Show: Did not match - copy just to be safe? " + current_season_file)
                            possible_queue.append([current_season_file, current_season_folder_output])

                    #copy unmatched files if we're adding new things to this season (e.g. folder.jpg)
                    if found_new_episode and len(possible_queue) > 0:
                        logging.info( "Show: Adding unmatched files to queue as we found a new episode - " + str(possible_queue) )
                        tv_copy_queue.extend(possible_queue)

                    #get set up for the next season
                    current_season_int += 1
                    current_season_folder = origin_folder + "\\Season " + '%0*d' % (2, current_season_int)
                    current_season_folder_output = output_folder + "\\Season " + '%0*d' % (2, current_season_int)
                    #if we're moving up a season we want all episodes from the new season
                    wanted_episode = 0
                    if len(episodes_added)>0:
                        logging.info("Show: Added: " + str(episodes_added))
                    else:
                        logging.info("Show: No episodes to add from this season.")

                else:
                    logging.info( "Show: There is no: " + current_season_folder)
                    break

            #if we copied anything from this season, record the last thing we copied
            output_show_int = current_season_int - 1
            #don't decrement if we didn't copy a new season
            if output_show_int < wanted_season_int:
                output_show_int = wanted_season_int
            output_show_list[wanted_show] = [output_show_int,episode_considering]
            logging.info( "Show: Updated " + wanted_show + " to " + str(output_show_list[wanted_show]) )

            # If here are any new epsiodes, add the base files to the queue as well (e.g. folder.jpg)
            if found_new_episode:
                base_dir_files = utils.listfiles(origin_folder)
                short_list = []
                for base_dir_file in base_dir_files:
                    tv_copy_queue.append([base_dir_file, output_folder])
                    short_list.append(os.path.basename(base_dir_file))
                logging.info( "Show: Base files found and added to queue: " + str(short_list) )

                #And if new episodes, then always attempt to copy copy the Season 00/Specials folders if there are any
                # if os.path.exists(originFolder+ "\\Season 00"):
                #     season00Files = listfiles(originFolder+ "\\Season 00")
                #     for season00File in season00Files:
                #         logging.info( "Show: Season00 file found and added to queue: " + season00File )
                #         copyQueue.append([season00File, outputFolder + "\\Season 00"])
                # if os.path.exists(originFolder+ "\\Specials"):
                #     specialsFiles = utils.listfiles(originFolder+ "\\Specials")
                #     for specialsFile in specialsFiles:
                #         logging.info( "Show: Specials file found and added to queue: " + specialsFile )
                #         copyQueue.append([specialsFile, outputFolder + "\\Specials"])


def update_subscriber_movies(name):

    ################################################################################
    ################################################################################
    # MOVIES - this is much easier - just check for any new movies and prompt for
    # copy or not

    #stores the folder names of movies to copy:
    global movie_copy_queue
    
    for dir in config['movie_paths']:
        files_in_path = utils.listdirPaths(dir)
        for file in files_in_path:
            movies_available.append(file)

    logging.info( "MOVIES AVAILABLE:" )
    for file in movies_available:
        logging.debug( file )

    logging.info( "CHANGES: " )
    #what is the difference
    for movie in movies_available:
        movie_name = os.path.basename(movie)
        #pprint.pprint(user_config['movies_to_ignore'][0:10])
        #print(movie_name)
        #in agogo mode we add all unwatched movies to the queue
        #if args.mode=="agogo":
        #    logging.info(movie_name + " - Added")
        #    movie_copy_queue.append(movie)
        #elif movie_name not in user_config['movies_to_ignore']:

        if movie_name not in user_config['movies_to_ignore']:
            print ""
            answer = raw_input("Add new movie " + repr(movie_name) + " to copy list (return = no, y = yes)")
            if (not answer) or answer =="n" or answer=="N":
                logging.info(movie_name + " - Not Added")
            else:
                logging.info(movie_name + " - Added")
                movie_copy_queue.append(movie)


def copy_tv():
    """
    Do the actual TV file copying if not in pretend mode
    """

    global tv_copy_queue
    global args
    global unfound_shows

    if not len(tv_copy_queue) > 0:
        logging.info( "NO TV FOUND TO COPY" )
    else:
        logging.info( "TV COPY QUEUE IS:" )
        for copy in tv_copy_queue:
            logging.info( str(copy) )

    # OK DO THE ACTUAL TV COPYING

    if args.pretend:
        logging.info( "PRETEND MODE - NO ACTUAL COPYING DONE" )
    else:
        #we're actually copying...
        logging.info( "COPYING TV NOW" )


        #work out if we have enough space
        needed_space = 0
        available_space = utils.get_free_space_gb(user_config['paths']['tv_output_path'])
        for copy in tv_copy_queue:
            destin_file = copy[1] + "\\" + os.path.basename(copy[0])
            if not os.path.exists(destin_file):
                needed_space += os.path.getsize(copy[0])

        #convert to GB
        needed_space = needed_space/1024/1024/1024

        logging.info( "TV - available space is " + str(available_space) + " GB")
        logging.info( "TV - needed space is    " + str(needed_space) + " GB")
 
        if needed_space > available_space:
            logging.error("Not enough space!!  Bailing out!")
            sys.exit()

        #make the root output folder if we need to
        if not os.path.exists(user_config['paths']['tv_output_path']):
            try:
                os.mkdir(user_config['paths']['tv_output_path'])
            except Exception as inst:
                logging.error("ERROR - Couldn't make output directory: " + user_config['paths']['tv_output_path'] + format_exc(inst))
                sys.exit()

        for copy in tv_copy_queue:

            destin_file = copy[1] + "\\" + os.path.basename(copy[0])

            #make the output folder if it doesn't exist
            if not os.path.exists(copy[1]):
                try:
                    os.makedirs(copy[1])
                except Exception as inst:
                    sys.exit("ERROR - Couldn't make output directory: " + copy[1] + format_exc(inst))


            logging.info( "Copying: " + copy[0] )
            logging.info( "To:      " + destin_file )
            #don't re-copy files if we're re-running the script!

            #TODO - ok we have a newer version maybe?  Might as well copy the better
            #quality version over & remove the lesser one

            if not os.path.exists(destin_file):
                utils.copyFile(copy[0],destin_file)
                logging.info( "Copied:  " + destin_file + "\n" )
            else:
                #check the sizes match in case of interrupted copy
                if not os.path.getsize(copy[0])==os.path.getsize(destin_file):
                    utils.copyFile(copy[0],destin_file)
                    logging.info( "ReCopy:  " + destin_file + "\n" )
                else:
                    logging.info( "Exists:  " + destin_file + "\n" )
 


    ################################################################################

    logging.info( "ANY UNFOUND SHOWS?" )

    if len(unfound_shows) > 0:
        for unfound_show in unfound_shows:
            logging.info("WARNING: I couldn't find this show: " + str(unfound_show) )

    ################################################################################

    # write out a new tv tracker if we're not doing the nuc 
    if args.mode != "agogo":

        logging.info( "WRITING UPDATED TV TRACKER FILE" )

        outname = "results/config." + args.name + ".tv.txt"

        f = open(outname , 'w')
        for output_show in sorted(output_show_list, key=str.lower):
            try:
                oldline = output_show + "|" + str(original_show_list[output_show][0]) + "|" + str(original_show_list[output_show][1])
            except:
                oldline = "Show did not exist in old file"

            newline = output_show + "|" + str(output_show_list[output_show][0]) + "|" + str(output_show_list[output_show][1])
            if oldline!=newline:
                logging.info( "OLD: " + oldline )
                logging.info( "NEW: " + newline )
            f.write(newline + "\n")
        f.close()


def copy_movies():
    """
    Do the actual movie file copying if not in pretend mode
    """

    global movie_copy_queue                

    ################################################################################
    #The copyQueues contains all the files to be copied and the destination directories - let's copy them


    if not len(movie_copy_queue) > 0:

        logging.info( "NO MOVIES FOUND TO COPY" )
    else:

        logging.info( "MOVIE COPY QUEUE IS:" )
        for copy in movie_copy_queue:
            logging.info( copy )
    ################################################################################
    #and actually do the movie copying...

    if args.pretend:
        logging.info( "PRETEND MODE - NO ACTUAL COPYING DONE" )
    else:

        logging.info( "NOW COPYING MOVIES" )

        #work out if we have enough space
        needed_space = 0
        available_space = utils.get_free_space_gb(user_config['paths']['movie_output_path'])
        for movie in movie_copy_queue:
            output_path = os.path.join(user_config['paths']['movie_output_path'],os.path.basename(movie))
            if not os.path.exists(output_path):
                logging.info(movie)
                needed_space += utils.getSize(movie)

        #convert to GB
        needed_space = needed_space/1024/1024/1024

        logging.info( "Movies - available space is " + str(available_space) + " GB")
        logging.info( "Movies - needed space is    " + str(needed_space) + " GB")

        if needed_space > available_space:
            logging.error("Not enough space!!  Bailing out!")
            sys.exit()

        for movie in movie_copy_queue:
            logging.info( "Copying: " + movie )
            logging.info( "To:    : " + user_config['paths']['movie_output_path'] )
            output_path = os.path.join(user_config['paths']['movie_output_path'],os.path.basename(movie))
            #if the output path exists, we may have only copied to half way or something.
            #check the sizes
            need_to_copy = True
            if os.path.exists(output_path):
                output_path_size = utils.getSize(output_path)
                input_path_size = utils.getSize(movie)
                if output_path_size == input_path_size:
                    need_to_copy = False
                    logging.info( "Exists : " + movie + "\n" )
                else:
                    #get rid of the old folder and start again
                    logging.info( "Deleted : " + output_path)
                    shutil.rmtree(output_path)
            if need_to_copy:
                utils.copyFolder(movie,output_path)
                logging.info( "Copied : " + movie + "\n" )

    ################################################################################
    #we've now considdered all available movies, so write out that as the new list

    logging.info( "WRITING NEW MOVIE TRACKER FILE")

    basename_list = []
    for movie in movies_available:
        basename_list.append(os.path.basename(movie))

    if args.mode!="agogo":
        f = open("results/config." + args.name + ".movies.txt" , 'w')
    else: 
        f = open("results/config.agogo.movies.txt" , 'w')       
    for movie in sorted(basename_list, key=str.lower):
        movie_name = os.path.basename(movie)
        f.write(movie_name + "\n" )
    f.close()


def delete_files(files):
    """ Delete a list of files """

    for filename in files:
        if args.pretend:
            log("Would have deleted " + filename)
        else:
            pass

def delete_folders(folders):
    """ Delete a list of folders """

    for folder in folders:
        if args.pretend:
            log("Would have deleted " + folder)
        else:
            pass


def clean():
    """ Remove watched material from the destination.  
        
        If running agogo, read the master destination library and poll the source library for watched status.
        If the movie/epsidoe is watched on the master library, remove it and related files
        Movies - delete the whole directory
        TV - delete all files with the same stem Show S01E02*.*

        If running an update, read the destination library and if watched, do as above.
    """

    global config
    global args

    movie_folders_to_delete = []
    tv_files_to_delete = []

    if args.mode=="agogo":
        log("CLEAN - mode is agogo")
        #the library to read comes from config.agogo.yaml
        watched_library_url = ""
        watched_library_pass = ""
        watched_library_user = ""

    if args.mode=="update":
        log("CLEAN - mode is update")

    #Now run through the library and see if each item has been watched, if so schedule it's delettion
    #The whole folder for movies, stem + all matching files for TV

    # And do the deleting

    log("About to delete TV files: " + str(tv_files_to_delete))
    delete_files(tv_files_to_delete)
    
    log("About to delete Movie folders" + str(movie_folders_to_delete))
    delete_folders(movie_folders_to_delete)    


def do_stuff_for(name):
    """
    Given a name, do the actual processing required as specified by the args
    """

    global args

    # Make some space if requested
    # if args.clean:
    #     clean()

    # Work out what we're going to copy    
    if args.update=="tv":
        logging.info("Unwatched TV only")
        update_subscriber_tv(name)
    if args.update=="movies":
        logging.info("Unwatched Movies only")
        update_subscriber_movies(name)            
    if args.update=="both":
        logging.info("Unwatched Movies and TV")
        update_subscriber_tv(name)
        update_subscriber_movies(name)            

    # & Copy!
    if args.update=="tv":
        logging.info("Copying TV only")
        copy_tv()
    if args.update=="movies":
        logging.info("Copying Movies only")
        copy_movies()            
    if args.update=="both":
        logging.info("Copying Movies and TV")
        copy_tv()
        copy_movies()


def main():
    """ The main script """

    # Globals
    global config
    global args

    # Set Up
    set_up_logging()
    interpret_command_line_arguments()
    load_master_config()


    ################################################################################
    # Are we in pretend mode?
    if args.pretend:
        logging.info( "PRETEND MODE -> log what would have been done, do nothing" )
    else:
        logging.info( "NOT PRETENDING -> let's make some changes" )

    #set up paths
    if not os.path.exists("results"):
        os.makedirs("results")
    if not os.path.exists("config/Subscribers"):
        os.makedirs("config/Subscribers")

    # what are we doing?
    # 3 options - set up for new person, update an xbmc-a-go-go machine with unwatched material, or do a library update for an existing person

    if args.mode == "init":
        logging.info("Doing: INITIALISE LIBRARY UPDATER FOR NEW NAME: " + args.name)
        set_up_new_person(args.name)
        logging.info("Done - all set up for " + args.name)
        logging.info("Next steps:\n\
                       Edit the config files - add your output paths,\n\
                       Subscribe to TV shows by setting them to 1|0 &\n\
                       Delete any movies from the list you want to copy.\n")

    elif args.mode =="agogo":
        logging.info("Doing: UPDATE XBMC-A-GO-GO MACHINE WITH UNWATCHED MATERIAL")
        xbmc_agogo()
        logging.info("Done creating xbmc-a-go-go config")
        load_config_for_name("agogo")
        do_stuff_for("agogo")

        #clean up the on-the-go config files
        if args.update=="tv" or args.update=="both":
            logging.info("Removing agogo on-the-fly tv config")
            try:
                os.remove("config/Subscribers/config.agogo.tv.txt")
            except Exception as inst:
                logging.error("Error deleting on-the-fly tv config file - please manually delete config/Subscribers/congig.agogo.tv.txt\n" + format_exc(inst)) 
        #DON'T REMOVE MOVIES FILE SO WITH EACH UPDATE WE CONSIDER RECENT MOVIES
        # if args.update=="movies" or args.update=="both":
        #     logging.info("Removing agogo on-the-fly movies config")
        #     try:
        #         os.remove("config/Subscribers/config.agogo.movies.txt")
        #     except Exception as inst:
        #         logging.error("Error deleting on-the-fly movie config file - please manually delete config/Subscribers/congig.agogo.movies.txt\n" + format_exc(inst))         

        logging.info("Done updating agogo - kick off a library update on agogo") 
        xbmc = XBMC(user_config["xbmc_destination"]["url"], user_config["xbmc_destination"]["user"], user_config["xbmc_destination"]["pass"])
        xbmc.VideoLibrary.Scan()

    elif args.mode =="update":
        #if we get here we're doing an update for a person
        logging.info("Doing: LIBRARY UPDATE FOR " + args.name)
        #where are we outputting to?
        load_config_for_name(args.name)
        do_stuff_for(args.name)
        logging.info("Done update for " + args.name)

    else:
        logging.error("Something went wrong with mode argument!")
        sys.exit()




# this just prevents main() being run if imported as a module
if __name__ == "__main__":

    try:
        os.remove("results/mediacopier.log")
    except Exception as inst:
        logging.info("No old results file to delete?  " + str(inst))

    #globals
    args = {}
    config = {}
    user_config = {}
    outputPaths = {}
    tv_copy_queue = []
    movie_copy_queue = []

    # will store any shows we can't find at all
    unfound_shows = []
    output_show_list = []

    ################################################################################
    # Holders for all our lists....

    #will store the list of where we got up to with each show for outputting the done file
    original_show_list = {}
    output_show_list = {}
    #list of wanted TV shows - filled up via the config file tv.name.txt
    wanted_list = []
    #wantedList but without the paths
    basic_show_list = []
    #what is available on the system?
    movies_available = []
 

    #kick this bad boy off
    main()
