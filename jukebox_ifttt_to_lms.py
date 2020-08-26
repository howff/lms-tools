#!/usr/bin/env python3
# Server to catch triggers from IFTTT and pass the spoken word
# onto the LMS Logitech Media Server as a playlist search.
# Listens on port 8127 which is almost the same as the Home-Assistant.io server.
# Although that's mapped in the home router from the external port 18127.
# HASS expects JSON but we only expect a search word.
# NB. In IFTTT use http not https otherwise you'll have to decode SSL.
# Also IFTTT issues a POST so the first line we get using sock.recv
# contains the POST headers and the search term is in the second line.

import socket
import json
import traceback
import logging
import logging.handlers
import sys

player_id = 'cd:cd:5d:57:cc:54' # Beauroom Speaker
lms_cli_ip_num = '192.168.1.25' # where the LMS server is running
lms_cli_ip_port = 9090          # which port LMS listens for telnet commands
ifttt_trigger_port_num = 8127   # the local port number not the one exposed to the internet
log_file_name = 'jukebox_ifttt_to_lms.log'

def send_command_to_media_server(cmd):
    logging.info('connecting to media server at %s:%s' % (lms_cli_ip_num, lms_cli_ip_port))
    outsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    outsocket.connect((lms_cli_ip_num, lms_cli_ip_port))
    logging.debug('  connected, sending "%s"' % cmd.rstrip())
    outsocket.send(str.encode(cmd))
    # wait until it has acknowleged all commands before closing
    try:
        r=outsocket.recv(128) # XXX need a timeout so it doesn't hang if LMS not responding
        logging.debug('  reply %s' % r)
    except Exception as e:
        logging.error('exception while getting reply from LMS %s' % str(e))
        logging.error(traceback.format_exc())
    outsocket.close()
    logging.info('command sent')

def jukebox_play(cmd):
    send_command_to_media_server('%s playlist clear\n' % player_id)
    send_command_to_media_server('%s playlist addtracks track.titlesearch%%3D%s\n' % (player_id, cmd))
    send_command_to_media_server('%s playlist addtracks album.titlesearch%%3D%s\n' % (player_id, cmd))
    send_command_to_media_server('%s playlist addtracks contributor.namesearch%%3D%s\n' % (player_id, cmd))
    send_command_to_media_server('%s play\n' % player_id)

def jukebox_next():
    send_command_to_media_server('%s playlist index +1\n' % player_id)

def jukebox_stop():
    send_command_to_media_server('%s pause\n' % player_id)


logging.basicConfig(filename=log_file_name, level=logging.DEBUG)
logging.getLogger().addHandler(logging.handlers.WatchedFileHandler(log_file_name))
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


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
        logging.debug('  waiting for data from client')
        header_data = client.recv(size)
        body_data = client.recv(size)
        logging.debug('  client header: %s' % header_data)
        logging.debug('  client body  : %s' % body_data)
        if body_data:
            query = body_data.rstrip() #.decode('utf-8')
            logging.debug('  query %s' % query)
            query_json = json.loads(query)
            logging.debug('  query_json %s' % query_json)
            if 'command' in query_json:
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
