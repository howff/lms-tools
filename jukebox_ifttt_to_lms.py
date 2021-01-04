#!/usr/bin/env python3
# Server to catch triggers from IFTTT and pass the spoken word
# onto the LMS Logitech Media Server as a playlist search.
# Listens on port 8123 which is the same as the Home-Assistant.io server.
# Although that's mapped in the home router from the external port 18123.
# HASS expects JSON but we only expect a search word.
# NB. In IFTTT use http not https otherwise you'll have to decode SSL.
# Also IFTTT issues a POST so the first line we get using sock.recv
# contains the POST headers and the search term is in the second line.
# However curl sends both together so we handle both types of input.
# Usage:
#  -d = debug to stdout, otherwise goes only to a log file.
# References:
#  https://github.com/elParaguayo/LMS-CLI-Documentation/blob/master/LMS-CLI.md

import socket
import json
import traceback
import logging
import logging.handlers
import re
import sys
import time
import xml.etree.ElementTree as XML

# Configuration:
default_player_name = "kitchen"
default_player_id = 'cc:cc:5c:56:cb:58'
lms_cli_ip_num = '192.168.1.30' # where the LMS server is running, probably localhost 127.0.0.1
lms_cli_ip_port = 9090          # which port LMS listens for telnet commands, normally 9090
ifttt_trigger_port_num = 8123   # the local port number, not the one exposed to the internet
log_file_name = 'jukebox_ifttt_to_lms.log'
castbridge_xml = '/var/lib/squeezeboxserver/prefs/castbridge.xml'
debug = False

# Initialisation
player_id = default_player_id
player_mac = {}


# Read the LMS Castbridge plugin to get the list of players and their ids (MAC addresses)
def read_castbridge_players():
    """ Fills in player_mac dict with the mac addresses of all the named players
    read from the castbridge_xml file """
    for elem in XML.parse(castbridge_xml).getroot().findall('device'):
        player_mac[elem.find('name').text] = elem.find('mac').text


def lms_response_to_dict(response):
    # The response is a string of words like name1:value1 name2:value2
    # except the colon is %3A. Luckily spaces in values are encoded as %20
    # which makes each tuple a distinct space-separated word.
    # XXX this doesn't work given a mac address of course.
    responsedict = {}
    for word in response.split():
        if '%3A' in word:
            (name,value) = word.replace('%20',' ').split('%3A', maxsplit=1)
            responsedict[name] = value
    return responsedict

def send_command_to_media_server(cmd):
    """ Opens a telnet connection to the Logitech Media Server
    and sends the given command which must have a trailing \n
    Returns the response as a string.
    """
    logging.info('connecting to media server at %s:%s' % (lms_cli_ip_num, lms_cli_ip_port))
    logging.debug('using player %s' % player_id)
    outsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    outsocket.connect((lms_cli_ip_num, lms_cli_ip_port))
    logging.debug('  connected, sending "%s"' % cmd.rstrip())
    outsocket.send(str.encode(cmd))
    reply = ''
    # wait until it has acknowleged all commands before closing
    try:
        logging.debug('wait for recv')
        reply=outsocket.recv(1024) # XXX need a timeout so it doesn't hang if LMS not responding
        logging.debug('  reply %s' % reply)
    except Exception as e:
        logging.error('exception while getting reply from LMS %s' % str(e))
        logging.error(traceback.format_exc())
    outsocket.close()
    logging.info('command sent')
    return reply.decode()


def jukebox_getNumTracks():
    """ Returns the number of tracks in the current playlist.
    This is used to detect if a 'clear' has worked, and to detect if a search has worked.
    """
    reply = send_command_to_media_server('%s status 0 19\n' % player_id)
    replydict = lms_response_to_dict(reply)
    return int(replydict.get('playlist_tracks', '-1'))


def jukebox_play(param):
    """ Clear the current playlist, search for the given term
    and add the results to the playlist, then start it playing.
    Currently there's no way to append but that's unlikely to be wanted anyway.
    The player_id global variable must already have been set.
    XXX ideally should search the name of a playlist first.
    Then searches track titles, album titles, and then artist name.
    """
    logging.debug('using player %s' % player_id)
    # Clear the current playlist and wait for it to empty
    send_command_to_media_server('%s playlist clear\n' % player_id)
    logging.debug('waiting for playlist to clear')
    while jukebox_getNumTracks() != 0:
        time.sleep(1)
    # Search tracks, albums and artists
    # encode spaces as %20
    param = re.sub(' ', '%20', param)
    send_command_to_media_server('%s playlist addtracks track.titlesearch%%3D%s\n' % (player_id, param))
    send_command_to_media_server('%s playlist addtracks album.titlesearch%%3D%s\n' % (player_id, param))
    send_command_to_media_server('%s playlist addtracks contributor.namesearch%%3D%s\n' % (player_id, param))
    # Wait for some search results
    logging.debug('waiting for playlist to fill with results')
    for i in range(0,19):
        if jukebox_getNumTracks() > 0: break
        time.sleep(1)
    send_command_to_media_server('%s play\n' % player_id)


def jukebox_next():
    """ Skips the rest of the current track and starts playing the next track in the playlist
    """
    send_command_to_media_server('%s playlist index +1\n' % player_id)


def jukebox_pause():
    """ Stops audio output by pausing the player
    """
    send_command_to_media_server('%s pause 1\n' % player_id)

def jukebox_resume():
    """ Continue audio output after pausing the player
    """
    send_command_to_media_server('%s pause 0\n' % player_id)


def decode_jukebox_verb(param):
    global player_id
    logging.debug('verb: %s' % param)
    words = param.split()
    # Remove the name of the player from the end of the command
    # if the user says 'in kitchen' or 'in the kitchen' or 'on chromecast'.
    # The last word must match the name of a player defined in the dict
    # player_mac as loaded form the castbridge.xml file.
    if len(words) > 3 and words[-1] in player_mac and \
        ((words[-2] == "in" or words[-2] == "on") or \
        ((words[-3] == "in" or words[-3] == "on") and words[-2] == "the")):
        player_id = player_mac[words[-1]]
        logging.debug('on: %s' % player_id)
        # remove the last two or three words
        if words[-2] == "the": words.pop()
        words.pop()
        words.pop()
    else:
        player_id = default_player_id
    # The first word should be the command: next/skip/pause/stop/continue/resume
    # otherwise it's assumed to be play. The rest of the words are the search term.
    if (words[0] == "next" or words[0] == "skip") and len(words) == 1:
        # Next
        logging.debug('verb: next')
        jukebox_next()
    elif (words[0] == "next" or words[0] == "skip") and len(words) > 1 and words[1] == "track":
        # Next track
        logging.debug('verb: next')
        jukebox_next()
    elif (words[0] == "pause" or words[0] == "stop") and len(words) == 1:
        # Pause
        logging.debug('verb: pause')
        jukebox_pause()
    elif (words[0] == "continue" or words[0] == "resume") and len(words) == 1:
        # Resume
        logging.debug('verb: resume')
        jukebox_resume()
    elif (words[0] == "play") and len(words)==1:
        # Nothing after play means resume
        logging.debug('verb: resume')
        jukebox_resume()
    elif (words[0] == "play") and len(words)>1:
        # The rest of the words after play become the search string
        # reconstructed by concatenating with a space separator.
        logging.debug('verb play on %s: %s' % (player_id, ' '.join(words[1:])))
        jukebox_play(' '.join(words[1:]))
    else:
        # No play command is assumed to be play
        logging.debug('verb play on %s: %s' % (player_id, ' '.join(words)))
        jukebox_play(' '.join(words))



# ---------------------------------------------------------------------
# MAIN
if len(sys.argv)>1 and sys.argv[1] == "-d":
    debug = True

# Configure logging debug messages to a file
# XXX should use a RotatingFileHandler
logging.basicConfig(filename=log_file_name, level=logging.DEBUG)
logging.getLogger().addHandler(logging.handlers.RotatingFileHandler(log_file_name, maxBytes=64*1024*1024, backupCount=9))
if debug:
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


# Read the list of players from the LMS server Castbridge plugin
read_castbridge_players()
if default_player_name in player_mac:
    player_id = player_mac[default_player_name]


# Create a network socket to listen for commands
socky = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socky.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socky.bind(('', ifttt_trigger_port_num))
socky.listen(5)
logging.info("listening for trigger from IFTTT on port %d" % ifttt_trigger_port_num)


while True:
    client, address = socky.accept()
    logging.info("client connected")
    client.settimeout(10)
    size = 2048
    rc=200
    try:
        logging.debug('  waiting for header from client')
        header_data = client.recv(size).decode()
        logging.debug('  client header: %s' % header_data)
        # Sometimes the body is in the same string (eg. from CURL) sometimes in a separate read call (eg. from IFTTT)
        if '\r\n\r\n' in header_data:
            body_data = header_data.split('\r\n\r\n')[1]
        else:
            logging.debug('  waiting for data from client')
            body_data = client.recv(size)
        logging.debug('  client body  : %s' % body_data)
        if body_data:
            query = body_data.rstrip() #.decode('utf-8')
            logging.debug('  query %s' % query)
            query_json = json.loads(query)
            logging.debug('  query_json %s' % query_json)
            if 'command' in query_json:
                # These commands are no longer recommended,
                # use only the 'jukebox' command so you only need one IFTTT trigger.
                if query_json['command'] == 'play':
                    term = query_json['parameter']
                    logging.info('  command: Play %s' % term)
                    jukebox_play(term)
                elif query_json['command'] == 'next':
                    logging.info('  command: Next' )
                    jukebox_next()
                elif query_json['command'] == 'stop':
                    logging.info('  command: Stop')
                    jukebox_stop()
                elif query_json['command'] == 'jukebox':
                    decode_jukebox_verb(query_json['parameter'])
                else:
                    logging.warning('unknown command %s' % query_json['command'])
        else:
            # if there's no body then raise an exception
            raise Exception('cannot handle request')
    except Exception as e:
        # any failures during client.recv, json.loads, outsocket.*
        # will be caught and end up here:
        logging.error('exception: closing connection (%s)' % str(e))
        logging.error(traceback.format_exc())
        rc=404
    client.send(b'HTTP/1.0 %d OK\r\n' % rc)
    client.close()
