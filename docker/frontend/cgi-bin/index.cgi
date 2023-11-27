#!/bin/sh
# 
#

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

# Read the query string from the environment variable
QUERY_STRING=$(echo "$QUERY_STRING")
CURL_OUTPUT=""


if echo "$QUERY_STRING" | grep -q "show_all="; then
    # Execute the curl command and capture its output
    CURL_OUTPUT=$(curl -s -X GET "http://192.168.1.120:8180/Diktdatabase/Diktsamling" -H "accept: text/xml")
elif echo "$QUERY_STRING" | grep -q "tittel="; then
    # Extract the poem title from the query string
    POEM_TITLE=$(echo "$QUERY_STRING" | sed 's/.*tittel=\([^&]*\).*/\1/' | sed 's/%20/ /g')
    if [ ! -z "$POEM_TITLE" ]; then
        # Execute the curl command with the poem title and capture its output
        # Replace this URL with the appropriate one that uses the poem title in the request
        CURL_OUTPUT=$(curl -s -X GET "http://192.168.1.120:8180/Diktdatabase/Diktsamling/$POEM_TITLE" -H "accept: text/xml")
    fi
fi

echo "Content-type:text/html;charset=utf-8"
echo


cat << EOF
<!DOCTYPE html>
<html>
    <head>
        <title>Dikt Search</title>
        <link rel="stylesheet" href="styles.css">
    </head>

    <body>

        <!-- Søk Form -->
        <form action="" method="get">
            <label for="poem-title">Dikt search:</label>
            <input type="text" id="dikt_tittel" name="tittel" placeholder="Tittel">
            <input type="submit" value="Search">
        </form>

        <!-- Vis alle dikt knapp -->
        <form action="" method="get">
            <input type="submit" name="show_all" value="Vis alle dikt">
        </form>

        <pre>
                Dikt:
                -----------------------
                $QUERY_STRING
                $CURL_OUTPUT
        </pre>



  </body>
</html>
EOF

