#!/bin/sh
# 
# ---- ---- ---- ---- ---- ---- ---- #

# GLOBAL Variabler
LOGGED_IN=0

# -- Sjekker om bruker er logget inn -- #
if [ -z "$HTTP_COOKIE" ]; then
    LOGGED_IN=0
else 
    # Henter session-cookie 
    session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=\([^;]*\).*/\1/')
    
    # Send xml forespørsel til backend for å sjekke om bruker er logget inn
    curl -s -X PUT "http://localhost:8080/Diktdatabase/Bruker" -H "accept: text/xml" -H "Cookie: session=$session_cookie" > /dev/null

    # TODO: Sjekke XML respons fra backend 
    if [ true ]; then
         LOGGED_IN=1
    fi    
fi

# -- Serverer riktig html fil -- #
if [ $LOGGED_IN = 0 ]; then
    cat html/login.html
else
    cat html/index.html
fi
