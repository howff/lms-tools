# lms-tools
Tools for home automation with squeezebox/Logitech media server

# Introduction

You want to be able to stream your own personal music (mp3) files to devices in your home
(such as a Hi-Fi, Chromecast, Chromecast audio, etc) and you want to be able to choose
which music by speaking into your home assistant (such as a Google Home assistant).

e.g. voice control of music streamed from your local NAS to your Chromecast.

You could use a different device instead of a Chromecast (such as your Hi-Fi or a SqueezeBox) in which case you don't use the CastBridge plugin.

# Diagram

You -> Google Home Assistant -> IFTTT -> This jukebox server -> LMS -> local MP3 collection -> CastBridge plugin -> Chromecast

* You say "OK Google, jukebox play Dua Lipa"
* The Google Home Assistant sends the words to IFTTT which recognises the trigger word "jukebox"
* The rest "play Dua Lipa" is forwarded to a server (this jukebox script) running on your computer
* The server converts the words into a "search" command for the Logitech Music Server
* LMS searches for "Dua Lipa" and adds all the songs to the playlist
* The server then sends a "play" command to the Logitech Music Server
* LMS starts to play the playlist
* LMS then uses the CastBridge plugin to stream the music to your Chromecast

# Requirements

* Logitech Music Server software running on your computer
* Configure your router to forward a port to your computer
* CastBridge plugin if streaming to a Chromecast or Chromecast Audio
* Account on IFTTT website

# Installation

1. Install Logitech Media Server, index your collection of music files
2. Install the CastBridge plugin and configure it to stream to your Chromecast
3. Test all of the above works before proceeding
4. Create an applet on IFTTT:
 * When you say "jukebox $"
 * Respond with "righty-ho"
 * Make a web request with method POST
 * Content-type: application/json
 * Body: { "command": "jukebox", "parameter": "{{TextField}}" }
 * http://IPADDR:18123/api/services/media_player
 * use your own IP address instead of IPADDR, or use a name if you've configured Dynamic DNS service
 * actually the /api/... stuff isn't needed in this version because the command is in the body
 * make sure it's http and not https
5. Configure your router to pass external internet-facing port 18123 to local port 8123 (for example) to your computer so that when IFTTT tries to connect to IPADDR port 18127 your router passes the request to your local computer and port 8127. You could make them the same number if you wish but this slightly obscures the purpose for hackers.
6. Edit the file jukebox_ifttt_to_lms.py if necessary
7. then make it executable with `chmod +x jukebox_ifttt_to_lms.py`
8. Run the jukebox_ifttt_to_lms.py script to start the local server. Run it in the background using `./jukebox_ifttt_to_lms.py &`
9. The log file will contain the requests and commands, or use the `-d` option to see that in the terminal.

To install as a service: edit `jukebox_ifttt_to_lms.service` with the full path to the script, then
`sudo cp jukebox_ifttt_to_lms.service /etc/systemd/system/` and then `systemctl enable jukebox_ifttt_to_lms.service`

# Configuration

Edit the script to change the port numbers, IP address of your LMS server, etc.

You will need to find the castbridge plugin config to get the MAC address, see the file such as `/var/lib/squeezeboxserver/prefs/castbridge.xml` (maybe you can also see this in the plugin configuration page of LMS) and find the `<mac>` line - use the value between the `<mac>` and `</mac>` inside the jukebox script.

You will need to change the castbridge plugin so it doesn't remove devices after a timeout - in the plugin configuration page set the remove timeout to -1 or by editing the castbridge.xml file add `<remove_timeout>-1</remove_timeout>` in the `common` section.

You can only command a single device so if you have multiple players you will need extra changes, but log a github issue if you want that feature.

You can create a castbridge.xml file at the command line using something like: `/var/lib/squeezeboxserver/cache/InstalledPlugins/Plugins/CastBridge/Bin/squeeze2cast-x86-64-static -i /tmp/castbridge.xml`

# References

LMS http://wiki.slimdevices.com/index.php/Main_Page

LMS downloads http://downloads.slimdevices.com/LogitechMediaServer_v7.9.2/

LMS CastBridge plugin https://github.com/philippe44/LMS-to-Cast

IFTTT https://ifttt.com/

CLI docs https://github.com/elParaguayo/LMS-CLI-Documentation/blob/master/LMS-CLI.md#0.1_PC
(more up to date in LMS docs though)
