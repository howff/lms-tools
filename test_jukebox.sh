#!/bin/bash

url="http://localhost:8123"

echo "dua lipa in kitchen..."
curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"play dua lipa in kitchen"}' "$url"
sleep 5
echo "queen in office..."
curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"play queen in office"}' "$url"
sleep 5
echo "pause..."
curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"pause in kitchen"}' "$url"
curl -X POST -H 'Content-type: application/json' -d '{"command":"jukebox","parameter":"pause in office"}' "$url"
