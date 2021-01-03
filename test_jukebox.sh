#!/bin/bash

url="http://localhost:8123"

curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"play dua lipa in kitchen"}' "$url"
sleep 5
curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"pause"}' "$url"
