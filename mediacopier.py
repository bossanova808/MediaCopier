import argparse
import logging
import os
import pprint
import re
import shutil
import sys
import yaml

from xbmcjson import XBMC
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
    parser.add_argument('mode',
                        choices=['init', 'update', 'agogo'],
                        help="init sets up configuration files for a new person, update updates from a configuration file, agogo updates based on an xbmc library instead of configuration files")
    parser.add_argument('update',
                        choices=['tv', 'movies', 'both'],
                        help="tv - just work on TV shows, movies - just work on movies, both updates both tv shows and movies")
    parser.add_argument('-p', '--pretend',
                        help="Run in pretend mode - will log what would have happened, but not actually copy anything",
                        action="store_true")
    parser.add_argument('-n', '--name',
                        help="Name of person to update - used with init & update mode only")
    parser.add_argument('-c', '--clean',
                        help="Remove (i.e. DELETE) watched material from the destination during an update or agogo")

    args = parser.parse_args()


def load_master_config():
    """ Loads the yaml config file from config/MediaCopier/config.yaml"""

    global config
    global show_to_folder_mappings

    logging.info("Loading configuration from config/MediaCopier/config.yaml")
    try:
        config = yaml.full_load(open("config/MediaCopier/config.yaml"))
        logging.info("\nRead in configuration:\n" + pprint.pformat(config))
    except Exception:
        logging.exception("Exception raised while reading MediaCopier configuration file")
        sys.exit()

    # logging.info( "Loading show to folder mappings from config/MediaCopier/show_to_folder_mappings.yaml" )    
    # try:
    #     show_to_folder_mappings = yaml.full_load(open("config/MediaCopier/show_to_folder_mappings.yaml"))
    #     logging.info("\nRead in mappings:\n" + pprint.pformat(show_to_folder_mappings))
    # except Exception as inst:
    #     logging.error("Exception raised while reading Show to Folder Mappings file: " + format_exc(inst))


def load_config_for_agogo():
    """
    Read in config/Subscribers/config.agogo.yaml into user_config
    """

    config_filename = "config/Subscribers/config.agogo.yaml"
    config_file = open(config_filename)
    logging.info("Loading config " + config_filename)

    try:
        # read it in
        user_config.update(yaml.safe_load(config_file))
        config_file.close()
    except Exception:
        logging.exception("Exception raised while reading agogo configuration file: " + config_filename)
        sys.exit()


def load_config_for_name(name):
    """
    Loads the config files for the user into user_config
    Special case is user 'agogo' supplied
    """

    global user_config
    global args

    if args.update == "tv" or args.update == "both":
        config_filename = "config/Subscribers/config." + name + ".tv.txt"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)

        try:
            # read it in
            user_config['tv_wanted_list'] = config_file.read().splitlines()
            user_config['basic_show_list'] = [wanted.split('|')[0] for wanted in user_config['tv_wanted_list']]
            config_file.close()
        except Exception:
            logging.exception("Exception raised while reading tv configuration file: " + config_filename)
            sys.exit()

    if args.update == "movies" or args.update == "both":
        config_filename = "config/Subscribers/config." + name + ".movies.txt"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)

        try:
            user_config['movies_to_ignore'] = config_file.read().splitlines()
            config_file.close()
        except Exception:
            logging.exception("Exception raised while reading movie configuration file: " + config_filename)
            sys.exit()

    # if init or update, load the output paths (with agogo this has already been loaded from yaml config file)
    if args.mode != "agogo":
        config_filename = "config/Subscribers/config." + name + ".paths.yaml"
        config_file = open(config_filename)
        logging.info("Loading config " + config_filename)

        try:
            # read it in
            user_config.update(yaml.safe_load(config_file))
            # create output folders if they don't exist
            if not os.path.exists(user_config['paths']['tv_output_path']):
                os.makedirs(user_config['paths']['tv_output_path'])
            if not os.path.exists(user_config['paths']['movie_output_path']):
                os.makedirs(user_config['paths']['movie_output_path'])
            config_file.close()
        except Exception:
            logging.exception("Exception raised while reading paths configuration file: " + config_filename)
            sys.exit()

    # dump all the user_config info for debugging purposes
    logging.info("Config all loaded as:\n" + pprint.pformat(user_config))


def set_up_new_person(name, latest_episodes=None, watched_movies=None):
    """ 
    Sets up a new subscriber to the library by creating the tv.name.txt and movies.names.txt config files
    Can be in two ways  - just initialisation, in which case the config files created are all movies seen/tvshow|0|0 - i.e. don't want this show
                        - with a list of latestEpisodes which should have in it the names of the latest watched episodes for all shows with unwatched episodes remaining

    """

    global user_config
    global config

    if args.update == "tv" or args.update == "both":
        # create the 3 config files - one for tv, paths, and optionally one for movies if we're not
        out_config_tv_filename = "config/Subscribers/config." + name + ".tv.txt"

        answer = ""
        create_file = True

        # don't clobber existing files by accident
        if os.path.isfile(out_config_tv_filename):
            logging.error("TV config file already exists: " + out_config_tv_filename)
            create_file = False
            answer = input("Overwrite existing config file [x] or use the existing file [enter]? ")

        if create_file or answer.lower() == "x" or args.mode == "init":

            out_config_tv_file = open(out_config_tv_filename, 'w')

            # DO TV SHOW ZERO LIST
            tv_show_list = []

            for d in config['tv_paths']:
                temp = utils.listdirPaths(d)
                for a in temp:
                    tv_show_list.append(os.path.basename(a))

            logging.debug("\nTV show list is: \n" + pprint.pformat(sorted(tv_show_list)))

            logging.debug("\nMatching latest_episodes to show paths")

            # First we must make sure we can map all our latest episodes from Kodi back to a show folder.
            # If not, stop here, so the corrections can be made.

            mapping_errors = False
            lowered_folders = list(map(str.lower, tv_show_list))

            logging.debug("Lowered folder names:")
            logging.debug(lowered_folders)

            for index, show in enumerate(sorted(latest_episodes)):
                # Must be reversed below, see line approx 231
                # So any change here has to be added there...
                show = show.replace(':', ' -')
                show = show.replace('’', "'")
                show = show.replace('!', "")
                show = show.lower()

                if show in lowered_folders:
                    logging.debug(f"Matched {show}")
                else:
                    mapping_errors = True
                    logging.error(f"NO MATCHING FOLDER FOUND FOR {show}")

            if mapping_errors:
                exit()

            if latest_episodes is None:
                logging.warning("NO LATEST EPISODES - Setting ALL TV shows to unwanted in created config file")
                for show in sorted(tv_show_list):
                    out_config_tv_file.write(show + "|0|0\n")
                    # out_config_tv_file.write( show + "|0|0|" + str(latest_episodes[show]["showId"]) + "\n")

            else:
                logging.info("Processing latest episodes list (creating on-the-fly a-go-go config)")
                for show in sorted(tv_show_list):

                    # show_
                    show_title_on_disk = show
                    # (Depends on scraper it seems, so we if there is a date, we need to check both the show with date and without).
                    # Kodi (sometimes) no longer stores dupes as New Amsterdam (2018), just New Amsterdam...so cut off the last six chars here if we have a date on the end
                    # Might mean we recognise a show as something we shouldn't but overall no huge drama if we copy too much
                    if show[-1] == ')' and show[-2].isdigit():
                        show = show[:-7]
                        logging.debug("Cut year off end of show name")

                    # Kodi store's Mighty Ducks: Game Changers but on disk this is Mighty Ducks - Game changers, so change these to the Kodi form
                    # for the lookup
                    # this is the reverse of code at line 190, so keep these mirroring each other!
                    show = show.replace(' -', ':')
                    show = show.replace("'", '’')
                    show = show.lower()

                    logging.debug(f'Processing: [{show}]')
                    # check if there is a latest watched episode for this how
                    if show not in latest_episodes and show_title_on_disk.lower() not in latest_episodes:
                        logging.debug(
                            f"{show}, {show_title_on_disk} was not found to have a latest watched episode - set to unwanted")
                        user_config[show_title_on_disk] = {'season': 0, 'episode': 0}
                        out_config_tv_file.write(show_title_on_disk + "|0|0|0\n")

                    else:
                        # we got here, so one of show or show (year) is in latest episodes...
                        if show not in latest_episodes:
                            show = show_title_on_disk.lower()

                        logging.debug(show_title_on_disk + " has a latest watched episode of " + str(
                            latest_episodes[show]["season"]) + "|" + str(latest_episodes[show]["episode"]))
                        # we're creating an output file for aGoGo machine so get the latest watched episode and record the previous episode
                        # in the config file as the last one copied
                        out_ep_num = int(latest_episodes[show.lower()]["episode"])
                        # the config file stores the latest watched episode - so we have to take one off the unwatched episode number
                        if out_ep_num > 0:
                            out_ep_num = out_ep_num - 1

                        out_config_tv_file.write(show_title_on_disk + "|" + latest_episodes[show]["season"] + "|" + str(
                            out_ep_num) + "|" + str(latest_episodes[show]["showId"]) + "\n")

            out_config_tv_file.close()

            logging.info("\nKodi's latest episodes mapped to agogo config for tv:\n")

            # Now we do a quick visual check of Kodi's latest episodes, and the generated copy list...

            with open(out_config_tv_filename, 'r') as f:
                lines = f.readlines()

            shows_to_copy = []
            for line in lines:
                if not line.endswith('|0|0|0\n'):
                    shows_to_copy.append(line)

            for index, show in enumerate(sorted(latest_episodes)):
                logging.info(show)
                logging.info(shows_to_copy[index])

            answer = input("Do the lists match (n/enter)? ")
            if answer:
                exit()

    # DO MOVIE LIST & BATCH FILE IF WE'RE NOT UPDATING AN aGoGO Machine

    if args.update == "movies" or args.update == "both":

        out_config_movies_filename = "config/Subscribers/config." + name + ".movies.txt"

        answer = ""
        # don't clobber existing files by accident
        if os.path.isfile(out_config_movies_filename):
            logging.error("Movie config file already exists " + out_config_movies_filename)
            answer = input("Overwrite existing config file [x] or use the existing file [enter]? ")

        if answer.lower() == "x" or args.mode == "init":
            out_config_movies_file = open(out_config_movies_filename, 'w')
            # not doing agogo, so build watched_movies now
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
    # create empty paths in all cases

    if args.mode != "agogo":
        out_config_paths_filename = "config/Subscribers/config." + name + ".paths.yaml"
        if os.path.isfile(out_config_paths_filename):
            logging.error("Config file already exists: " + out_config_paths_filename)
        else:
            out_config_paths_file = open(out_config_paths_filename, 'w')
            user_config['paths'] = {'tv_output_path': "", 'movie_output_path': ""}
            yaml.dump(user_config, out_config_paths_file, default_flow_style=False, allow_unicode=True)
            out_config_paths_file.close()


def xbmc_agogo():
    """ 
    Create the on-the-fly config files for an agogo update
    """

    global config
    global user_config
    global args
    global xbmc

    # load the agogo config
    load_config_for_agogo()

    # Login with custom credentials
    xbmc = XBMC(user_config["xbmc_source"]["url"], user_config["xbmc_source"]["user"],
                user_config["xbmc_source"]["pass"])
    print(xbmc.JSONRPC.Ping())

    seen_movies = None
    latest_episodes = None

    if args.update == "tv" or args.update == "both":

        latest_episodes = {}
        result = xbmc.VideoLibrary.GetTVShows({"filter": {"field": "playcount", "operator": "is", "value": "0"}})
        shows_with_unwatched = result["result"]["tvshows"]
        for show in shows_with_unwatched:
            # print "******" + show["label"]
            result = xbmc.VideoLibrary.GetEpisodes(
                {"tvshowid": show["tvshowid"], "sort": {"order": "ascending", "method": "episode"},
                 "filter": {"field": "playcount", "operator": "lessthan", "value": "1"}})
            unwatched_episodes = result["result"]["episodes"]
            # for episode in unwatched_episodes:
            #    print episode["label"]
            # 3x07. MagicHour (2)
            cut = unwatched_episodes[0]["label"].split(".", 1)
            episode_string = cut[0]
            parts = episode_string.split("x")
            try:
                season_number = parts[0]
                episode_number = parts[1]
            # Deal with specials returned as S09
            except Exception:
                season_number = "0"
                episode_number = (parts[0])[1:]
            # xbmc returns nice full show names but windows doesn't like special characters in paths
            # so remove the problem chars here to match the folder names
            cleaned_episode_name = show["label"].replace(":", "")
            cleaned_episode_name = cleaned_episode_name.replace("?", "")
            latest_episodes[cleaned_episode_name.lower()] = ({"showId": show["tvshowid"], "season": season_number, "episode": episode_number})

    # latest_episodes is a list of dicts with the above keys containing the latest unwatched episodes
    # seen_movies is a list of all movies that have been watched
    # call set up new person with these lists
    if latest_episodes is not None:
        logging.debug("Latest watched episodes list is:\n" + pprint.pformat(latest_episodes))
    if seen_movies is not None:
        logging.debug("Seen Movies list is:\n" + pprint.pformat(seen_movies))

    set_up_new_person("agogo", latest_episodes, seen_movies)


def build_show_lists():
    global user_config

    # will store our list of shows found in the TV paths
    show_list = []
    # and a list to hold new shows found
    new_show_list = []

    for d in config['tv_paths']:
        shows_in_this_path = os.listdir(d)
        logging.info(d + " contains:\n" + str(shows_in_this_path))
        for show_in_this_path in shows_in_this_path:
            show_path = d + "\\" + show_in_this_path
            if os.path.isdir(show_path):
                show_list.append(show_path)
                if show_in_this_path not in user_config['basic_show_list']:
                    new_show_list.append(show_path)
            else:
                logging.warning(show_in_this_path + " - not a directory.")

    return show_list, new_show_list


def update_subscriber_tv():
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
    logging.info("\n\n" + str(len(user_config['basic_show_list'])) + " AVAILABLE SHOWS" + "\n")
    for show in sorted(user_config['basic_show_list'], key=str.lower):
        logging.debug(os.path.basename(show))

    if len(new_show_list) > 0:
        logging.debug("\n\n" + str(len(new_show_list)) + " NEW SHOWS FOUND:" + "\n")
        for show in new_show_list:
            logging.debug(os.path.basename(show))

    logging.info("\n\nADD ANY NEW SHOWS INTERACTIVELY\n")

    # add new shows?
    for show in new_show_list:
        print("")
        answer = input("Add new TV show " + show + " to copy list (return = no, y = yes)")
        if (not answer) or answer == "n" or answer == "N":
            print(show + " - Not Added, set to 0|0 in output_show_list")
            logging.debug(show + " - Not Added, set to 0|0 in output_show_list")
            output_show_list[os.path.basename(show)] = [0, 0]
        else:
            print(show + " - Added ")
            logging.info(show + " - Added")
            user_config['tv_wanted_list'].append(os.path.basename(show) + "|1|0\n")

    ################################################################################

    logging.info("NOW PROCESSING EACH WANTED SHOW")

    # ok for each wanted show...
    for wanted in user_config['tv_wanted_list']:

        # Parse config file
        try:
            values = wanted.split('|')
            wanted_show = values[0]
            wanted_season_int = int(values[1])
            wanted_season = format(wanted_season_int, "02d")
            wanted_episode = int(values[2])
            show_id = int(values[3])
        except IndexError:
            show_id = 0

        # record where we started
        original_show_list[wanted_show] = [wanted_season_int, wanted_episode]



        #######################
        # otherwise start processing
        logging.info("Show: Wanted name: " + wanted_show + " - Wanted Series: " + str(
            wanted_season) + " - Wanted Episode: " + str(wanted_episode))

        found_show = False
        output_folder = ""
        origin_folder = ""

        ############
        # do we recognise this show?
        for possible_show in show_list:
            # logging.info("Matching " + wanted_show + " to " + os.path.basename(possible_show))
            if wanted_show == os.path.basename(possible_show):
                logging.info("Matched " + wanted_show + " to " + possible_show)
                output_folder = os.path.join(user_config['paths']['tv_output_path'], wanted_show)
                origin_folder = possible_show
                found_show = True
                break

        # show is not in the available list
        if not found_show:
            logging.error("WARNING: SHOW NOT FOUND - so added to unfound list, and won't be re-written to tracker file")
            unfound_shows.append(wanted_show)
            continue

        #######################
        # skip if set to 0,0
        if wanted_season_int == 0 and wanted_episode == 0:
            logging.info("Show: " + wanted_show + " set to 0|0 -> skip it")
            original_show_list[wanted_show] = [0, 0]
            output_show_list[wanted_show] = [0, 0]
            # print(outputShowList)
            # go back to the top of the loop for the next show
            continue

        # we found it, so let's maybe copy some stuff
        logging.info("Show: From: " + origin_folder)
        logging.info("Show: To:   " + output_folder)

        # OK, so the show is available, and we want some of it.  Let's find out if there are new episodes?
        start_season_int = int(wanted_season)
        start_season_folder = origin_folder + "\\Season " + wanted_season
        start_season_folder_output = output_folder + "\\Season " + wanted_season

        # set up for loop
        current_season_folder = start_season_folder
        current_season_folder_output = start_season_folder_output
        current_season_int = start_season_int
        episode_considering = 0

        season_folder_exists = True
        missed_one_already = False
        found_new_episode = False

        # we loop through each season until we can't find another season
        while season_folder_exists:
            if os.path.exists(current_season_folder):
                # the season folder exists
                logging.info("Show: Handling " + os.path.basename(current_season_folder))

                # make a list of files in the current season
                current_season_files = utils.listdirPaths(current_season_folder)

                # ok so now we want to match only the wanted episode and above and add them to the copy queue
                # keep track of them for logging
                episodes_added = []
                # and a queue to store files like folder.jpg that we will only copy if we found at least 1 new ep.
                possible_queue = []

                for current_season_file in current_season_files:
                    # match the SXXEXX part of the filename
                    p = re.compile('S[0-9]*E[0-9]*')
                    match = p.search(current_season_file)
                    if match:
                        episode_string = match.group()
                        episode_string = episode_string.split('E')[1]
                        # logging.info( f"episode_string is {episode_string}" )
                        episode_considering = int(episode_string)
                        # logging.info( f"episode_considering is {episode_considering}" )
                        if episode_considering > wanted_episode:
                            found_new_episode = True
                            if episode_string not in episodes_added:
                                episodes_added.append(episode_string)
                            # logging.info("Show: Episode " + str(episodeConsidering) + " file is newer than " + str(wantedEpisode) +", adding to queue")
                            tv_copy_queue.append(
                                [current_season_file, current_season_folder_output, wanted_show, show_id,
                                 int(current_season_int), int(episode_considering)])
                        # else:
                        # logging.info("Show: Episode " + str(episodeConsidering) + " file is older/same than " + str(wantedEpisode) +", not adding")

                    else:
                        logging.info("Show: Did not match - copy just to be safe? " + current_season_file)
                        possible_queue.append([current_season_file, current_season_folder_output])

                # copy unmatched files if we're adding new things to this season (e.g. folder.jpg)
                if found_new_episode and len(possible_queue) > 0:
                    logging.info(
                        "Show: Adding unmatched files to queue as we found a new episode - " + str(possible_queue))
                    tv_copy_queue.extend(possible_queue)

                # get set up for the next season
                current_season_int += 1
                current_season_folder = origin_folder + "\\Season " + '%0*d' % (2, current_season_int)
                current_season_folder_output = output_folder + "\\Season " + '%0*d' % (2, current_season_int)
                # if we're moving up a season we want all episodes from the new season
                wanted_episode = 0
                if len(episodes_added) > 0:
                    logging.info("Show: Added: " + str(episodes_added))
                else:
                    logging.info("Show: No episodes to add from this season.")

            else:
                logging.info("Show: There is no: " + current_season_folder)
                # Because of some stupid shows/people, Location, Location, Location has seasons 31,33,34,35...so we skip
                # over one folder and check again just to be sure we should be stopping...
                if not missed_one_already:
                    logging.info(
                        f"Setting missed_one_already and incrementing current season from {current_season_int} to {current_season_int + 1}")
                    missed_one_already = True
                    current_season_int += 1
                    current_season_folder = origin_folder + "\\Season " + '%0*d' % (2, current_season_int)
                    current_season_folder_output = output_folder + "\\Season " + '%0*d' % (2, current_season_int)
                    wanted_episode = 0
                    continue
                # If we missed_one_already, then we've added one to the current_season_int so take that back off again so that
                # when we write the tracker file we're not one season forward...
                else:
                    current_season_int -= 1
                    logging.info(
                        f"Two season folders don't exist, stop looking for more - reset current_season_int to {current_season_int}")
                    break

        # if we copied anything from this season, record the last thing we copied
        logging.info(
            f"At this point, current_season_int ({current_season_int}) should be 1 more than what we want to record, so set output_show_int to {current_season_int - 1}")
        output_show_int = current_season_int - 1
        # don't decrement if we didn't copy a new season
        if output_show_int < wanted_season_int:
            logging.info(
                f"But we didn't copy a new season, so in fact set output_show_int to wanted_season_int ({wanted_season_int})")
            output_show_int = wanted_season_int
        output_show_list[wanted_show] = [output_show_int, episode_considering]
        logging.info("Show: Updated " + wanted_show + " to " + str(output_show_list[wanted_show]))

        # If here are any new episodes, add the base files to the queue as well (e.g. folder.jpg)
        if found_new_episode:
            base_dir_files = utils.listfiles(origin_folder)
            short_list = []
            for base_dir_file in base_dir_files:
                tv_copy_queue.append([base_dir_file, output_folder])
                short_list.append(os.path.basename(base_dir_file))
            logging.info("Show: Base files found and added to queue: " + str(short_list))

            # And if new episodes, always attempt to copy the Season 00 folders if there are any
            if os.path.exists(origin_folder + "\\Season 00"):
                season00_files = utils.listfiles(origin_folder + "\\Season 00")
                for season00File in season00_files:
                    p = re.compile('S[0-9]*E[0-9]*')
                    match = p.search(season00File)
                    if match:
                        se_string = match.group()
                        season_string = "00"
                        episode_string = se_string[4:6]
                        logging.info("Show: Season00 file found and added to queue: " + season00File)
                        tv_copy_queue.append(
                            [season00File, output_folder + "\\Season 00", wanted_show, show_id, int(season_string),
                             int(episode_string)])
                    else:
                        logging.warning(
                            "Could not match season/episode of special so adding to queue anyway to be safe")
                        logging.info("Show: Season00 file found and added to queue: " + season00File)
                        tv_copy_queue.append([season00File, output_folder + "\\Season 00"])


def update_subscriber_movies():
    ################################################################################
    ################################################################################
    # MOVIES - this is much easier - just check for any new movies and prompt for
    # copy or not

    # stores the folder names of movies to copy:
    global movie_copy_queue

    for folder in config['movie_paths']:
        files_in_path = utils.listdirPaths(folder)
        for file in files_in_path:
            if file != ".deletedByTMM":
                movies_available.append(file)

    logging.info("MOVIES AVAILABLE:")
    for file in movies_available:
        logging.debug(file)

    logging.info("CHANGES: ")
    # what is the difference
    for movie in movies_available:
        movie_name = os.path.basename(movie)
        # pprint.pprint(user_config['movies_to_ignore'][0:10])
        # print(movie_name)
        # in agogo mode we add all unwatched movies to the queue
        # if args.mode=="agogo":
        #    logging.info(movie_name + " - Added")
        #    movie_copy_queue.append(movie)
        # elif movie_name not in user_config['movies_to_ignore']:

        if movie_name not in user_config['movies_to_ignore'] and movie_name != ".deletedByTMM":
            print("")
            answer = input("Add new movie " + repr(movie_name) + " to copy list (return = no, y = yes)")
            if (not answer) or answer == "n" or answer == "N":
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
    global video_file_extensions

    if not len(tv_copy_queue) > 0:
        logging.info("NO TV FOUND TO COPY")
    else:
        logging.info("TV COPY QUEUE IS:")
        for copy in tv_copy_queue:
            logging.info(str(copy))

    # First, need to strip files out that have been watched in an ad hoc order...
    playcount_cache = {}
    new_copy_queue = []

    for copy in tv_copy_queue:

        # logging.info(str(copy))

        # Only video files have the id stuff at the end, not base files etc...which we always want to copy really...
        try:
            tv_show_name = copy[2]
            tv_show_id = int(copy[3])
            tv_show_season = int(copy[4])
            tv_show_episode = int(copy[5])
        except Exception:
            continue

        # Deal with shows being watched in random order...
        if tv_show_id > 0:
            # logging.info("Checking playcount of %s id: %s season: %s episode: %s" % (tv_show_name, str(tv_show_id), str(tv_show_season), str(tv_show_episode)))

            kodi_playcount = 0
            filename, file_extension = os.path.splitext(copy[0])

            # Grab the playcount from our cache if it is in there...
            try:
                kodi_playcount = playcount_cache[
                    str(tv_show_id) + "-" + str(tv_show_season) + "-" + str(tv_show_episode)]
                # logging.info("Using playcount_cache: " + str(kodi_playcount))

            # Otherwise, check this particular episode is _actually_ unwatched in Kodi's library... 
            #  (if we're dealing with shows being watched in an adhoc order...)
            except KeyError:
                result = xbmc.VideoLibrary.GetEpisodes({"tvshowid": tv_show_id,
                                                        "season": tv_show_season,
                                                        "properties": ['season', 'episode', 'playcount'],
                                                        "filter": {"field": "episode", "operator": "is",
                                                                   "value": str(tv_show_episode)}
                                                        })

                # logging.info(result)

                # Episode found in kodi...should be only one
                try:
                    for episode in result["result"]["episodes"]:
                        if episode['season'] == tv_show_season and episode['episode'] == tv_show_episode:
                            # logging.info("Matched: "+ str(episode))
                            playcount_cache[str(tv_show_id) + "-" + str(tv_show_season) + "-" + str(tv_show_episode)] = episode['playcount']
                            kodi_playcount = episode['playcount']
                            break

                # Episode not found in Kodi?  Don't skip it just to be safe...
                except KeyError:
                    if file_extension in video_file_extensions:
                        logging.info("%s Season %s episode %s not found in Kodi Library? Copying just to be safe..." % (tv_show_name, tv_show_season, tv_show_episode))

            # One way or another we should have a playcount now, or we've assumed zero...
            if int(kodi_playcount) > 0:
                if file_extension in video_file_extensions:
                    logging.info(
                        "Skipping: " + os.path.basename(copy[0]) + " (Kodi playcount is " + str(kodi_playcount) + ")")
                continue

        # add this file to the new copy queue if it hasn't been watched...
        new_copy_queue.append(copy)

    if args.pretend:
        logging.info("PRETEND MODE - NO ACTUAL COPYING DONE")

    else:

        # we're actually copying...
        logging.info("COPYING TV NOW")

        # work out if we have enough space
        needed_space = 0
        available_space = utils.get_free_space_gb(user_config['paths']['tv_output_path'])
        for copy in new_copy_queue:
            destin_file = copy[1] + "\\" + os.path.basename(copy[0])
            if not os.path.exists(destin_file):
                needed_space += os.path.getsize(copy[0])

        # convert to GB
        needed_space = needed_space / 1024 / 1024 / 1024

        logging.info("TV - available space is " + str(available_space) + " GB")
        logging.info("TV - needed space is    " + str(needed_space) + " GB")

        if needed_space > available_space:
            logging.error("Not enough space!!  Bailing out!")
            sys.exit()

        # make the root output folder if we need to
        if not os.path.exists(user_config['paths']['tv_output_path']):
            try:
                os.mkdir(user_config['paths']['tv_output_path'])
            except Exception:
                logging.exception("ERROR - Couldn't make output directory: " + user_config['paths']['tv_output_path'])
                sys.exit()

        # OK NOW FINALLY DO THE ACTUAL TV COPYING

        copied_amount = 0

        for copy in new_copy_queue:

            destin_file = copy[1] + "\\" + os.path.basename(copy[0])

            if not os.path.exists(destin_file):
                copied_amount += os.path.getsize(copy[0])

            # make the output folder if it doesn't exist
            if not os.path.exists(copy[1]):
                try:
                    os.makedirs(copy[1])
                except Exception:
                    logging.exception("ERROR - Couldn't make output directory: " + copy[1])
                    sys.exit()

            logging.info("Copying: " + copy[0])
            logging.info("To:      " + destin_file)
            # don't re-copy files if we're re-running the script!

            # TODO - ok we have a newer version maybe?  Might as well copy the better
            # quality version over & remove the lesser one

            if not os.path.exists(destin_file):
                utils.copyFile(copy[0], destin_file)
                logging.info("Copied:  " + destin_file)
            else:
                # check the sizes match in case of interrupted copy
                if not os.path.getsize(copy[0]) == os.path.getsize(destin_file):
                    utils.copyFile(copy[0], destin_file)
                    logging.info("ReCopy:  " + destin_file)
                else:
                    logging.info("Exists:  " + destin_file)

            logging.info("Copied " + "{:.2f}".format(copied_amount / 1024 / 1024 / 1024) + " GB of " + "{:.2f}".format(
                needed_space) + "\n")

    ################################################################################

    logging.info("ANY UNFOUND SHOWS?")

    if len(unfound_shows) > 0:
        for unfound_show in unfound_shows:
            logging.info("WARNING: I couldn't find this show: " + str(unfound_show))

    ################################################################################

    # write out a new tv tracker if we're not doing the nuc 
    if args.mode != "agogo":

        logging.info("WRITING UPDATED TV TRACKER FILE")

        out_name = "results/config." + args.name + ".tv.txt"

        f = open(out_name, 'w')
        for output_show in sorted(output_show_list, key=str.lower):
            try:
                old_line = output_show + "|" + str(original_show_list[output_show][0]) + "|" + str(
                    original_show_list[output_show][1])
            except Exception:
                old_line = "Show did not exist in old file"

            new_line = output_show + "|" + str(output_show_list[output_show][0]) + "|" + str(
                output_show_list[output_show][1])
            if old_line != new_line:
                logging.info("OLD: " + old_line)
                logging.info("NEW: " + new_line)
            f.write(new_line + "\n")
        f.close()


def copy_movies():
    """
    Do the actual movie file copying if not in pretend mode
    """

    global movie_copy_queue

    ################################################################################
    # The copyQueues contains all the files to be copied and the destination directories - let's copy them

    if not len(movie_copy_queue) > 0:

        logging.info("NO MOVIES FOUND TO COPY")
    else:

        logging.info("MOVIE COPY QUEUE IS:")
        for copy in movie_copy_queue:
            logging.info(copy)
    ################################################################################
    # and actually do the movie copying...

    if args.pretend:
        logging.info("PRETEND MODE - NO ACTUAL COPYING DONE")
    else:

        logging.info("NOW COPYING MOVIES")

        # work out if we have enough space
        needed_space = 0
        available_space = utils.get_free_space_gb(user_config['paths']['movie_output_path'])
        for movie in movie_copy_queue:
            output_path = os.path.join(user_config['paths']['movie_output_path'], os.path.basename(movie))
            if not os.path.exists(output_path):
                logging.info(movie)
                needed_space += utils.getSize(movie)

        # convert to GB
        needed_space = needed_space / 1024 / 1024 / 1024

        logging.info("Movies - available space is " + str(available_space) + " GB")
        logging.info("Movies - needed space is    " + str(needed_space) + " GB")

        if needed_space > available_space:
            logging.error("Not enough space!!  Bailing out!")
            sys.exit()

        for movie in movie_copy_queue:
            logging.info("Copying: " + movie)
            logging.info("To:    : " + user_config['paths']['movie_output_path'])
            output_path = os.path.join(user_config['paths']['movie_output_path'], os.path.basename(movie))
            # if the output path exists, we may have only copied to half way or something.
            # check the sizes
            need_to_copy = True
            if os.path.exists(output_path):
                output_path_size = utils.getSize(output_path)
                input_path_size = utils.getSize(movie)
                if output_path_size == input_path_size:
                    need_to_copy = False
                    logging.info("Exists : " + movie + "\n")
                else:
                    # get rid of the old folder and start again
                    logging.info("Deleted : " + output_path)
                    shutil.rmtree(output_path)
            if need_to_copy:
                utils.copyFolder(movie, output_path)
                logging.info("Copied : " + movie + "\n")

    ################################################################################
    # we've now considered all available movies, so write out that as the new list

    logging.info("WRITING NEW MOVIE TRACKER FILE")

    basename_list = []
    for movie in movies_available:
        basename_list.append(os.path.basename(movie))

    if args.mode != "agogo":
        f = open("results/config." + args.name + ".movies.txt", 'w')
    else:
        f = open("results/config.agogo.movies.txt", 'w')
    for movie in sorted(basename_list, key=str.lower):
        movie_name = os.path.basename(movie)
        f.write(movie_name + "\n")
    f.close()


def delete_files(files):
    """ Delete a list of files """

    for filename in files:
        if args.pretend:
            logging.warning("Would have deleted " + filename)
        else:
            pass


def delete_folders(folders):
    """ Delete a list of folders """

    for folder in folders:
        if args.pretend:
            logging.warning("Would have deleted " + folder)
        else:
            pass


def clean():
    """ Remove watched material from the destination.  
        
        If running agogo, read the master destination library and poll the source library for watched status.
        If the movie/episode is watched on the master library, remove it and related files
        Movies - delete the whole directory
        TV - delete all files with the same stem Show S01E02*.*

        If running an update, read the destination library and if watched, do as above.
    """

    global config
    global args

    movie_folders_to_delete = []
    tv_files_to_delete = []

    if args.mode == "agogo":
        logging.info("CLEAN - mode is agogo")
        # the library to read comes from config.agogo.yaml

    if args.mode == "update":
        logging.info("CLEAN - mode is update")

    # Now run through the library and see if each item has been watched, if so schedule its deletion
    # The whole folder for movies, stem + all matching files for TV

    # And do the deleting

    logging.info("About to delete TV files: " + str(tv_files_to_delete))
    delete_files(tv_files_to_delete)

    logging.info("About to delete Movie folders" + str(movie_folders_to_delete))
    delete_folders(movie_folders_to_delete)


def do_some_stuff():
    """
    Given a name, do the actual processing required as specified by the args
    """

    global args

    # Make some space if requested
    # if args.clean:
    #     clean()

    # Work out what we're going to copy    
    if args.update == "tv":
        logging.info("Unwatched TV only")
        update_subscriber_tv()
    if args.update == "movies":
        logging.info("Unwatched Movies only")
        update_subscriber_movies()
    if args.update == "both":
        logging.info("Unwatched Movies and TV")
        update_subscriber_tv()
        update_subscriber_movies()

    # & Copy!
    if args.update == "tv":
        logging.info("Copying TV only")
        copy_tv()
    if args.update == "movies":
        logging.info("Copying Movies only")
        copy_movies()
    if args.update == "both":
        logging.info("Copying Movies and TV")
        copy_tv()
        copy_movies()


def main():
    """ The main script """

    # Globals
    global config
    global show_to_folder_mappings  # not currently used
    global args
    global xbmc

    # Set Up
    set_up_logging()
    interpret_command_line_arguments()
    load_master_config()

    ################################################################################
    # Are we in pretend mode?
    if args.pretend:
        logging.info("PRETEND MODE -> log what would have been done, do nothing")
    else:
        logging.info("NOT PRETENDING -> let's make some changes")

    # set up paths
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

    elif args.mode == "agogo":
        logging.info("Doing: UPDATE XBMC-A-GO-GO MACHINE WITH UNWATCHED MATERIAL")
        xbmc_agogo()
        logging.info("Done creating xbmc-a-go-go config")
        load_config_for_name("agogo")
        do_some_stuff()

        # clean up the on-the-go config files
        if args.update == "tv" or args.update == "both":
            logging.info("Removing agogo on-the-fly tv config")
            try:
                os.remove("config/Subscribers/config.agogo.tv.txt")
            except Exception:
                logging.exception("Error deleting on-the-fly tv config file - please manually delete config/Subscribers/config.agogo.tv.txt\n")
                # DON'T REMOVE MOVIES FILE SO WITH EACH UPDATE WE CONSIDER RECENT MOVIES
        # if args.update=="movies" or args.update=="both":
        #     logging.info("Removing agogo on-the-fly movies config")
        #     try:
        #         os.remove("config/Subscribers/config.agogo.movies.txt")
        #     except Exception as inst:
        #         logging.error("Error deleting on-the-fly movie config file - please manually delete config/Subscribers/config.agogo.movies.txt\n" + format_exc(inst))

        # May 2020 - can't do this anymore as we're just using a separate hard drive now...will need to do a manual update...
        # logging.info("Done updating agogo - kick off a library update on agogo") 
        # xbmc = XBMC(user_config["xbmc_destination"]["url"], user_config["xbmc_destination"]["user"], user_config["xbmc_destination"]["pass"])
        # xbmc.VideoLibrary.Scan()

    elif args.mode == "update":
        # if we get here we're doing an update for a person
        logging.info("Doing: LIBRARY UPDATE FOR " + args.name)
        # where are we outputting to?
        load_config_for_name(args.name)
        do_some_stuff()
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

    # globals
    xbmc = None
    args = {}
    config = {}
    user_config = {}
    outputPaths = {}
    tv_copy_queue = []
    movie_copy_queue = []
    video_file_extensions = [".avi", ".mkv", ".mp4", ".divx", ".mov", ".flv", ".wmv"]
    # will store any shows we can't find at all
    unfound_shows = []
    # will store the list of where we got up to with each show for outputting the done file
    original_show_list = {}
    output_show_list = {}
    # list of wanted TV shows - filled up via the config file tv.name.txt
    wanted_list = []
    # wantedList but without the paths
    basic_show_list = []
    # what is available on the system?
    movies_available = []

    # Not currently used
    show_to_folder_mappings = []

    # kick this bad boy off
    main()
