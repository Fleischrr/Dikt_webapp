#!/bin/sh
# 
#

# --- GLOBAL Variabler --- #
LOGGED_IN=0
COOKIE_RESPONSE=""
QUERY_STRING=$(echo "$QUERY_STRING")
CURL_OUTPUT=""

sanitize() {
    # Replace '+' with space
    local input=$(echo "$1" | sed 's/+/%20/g')
    # Decode only allowed characters
    local decoded=$(echo "$input" | sed 's/%20/ /g' | sed 's/%2C/,/g' | sed 's/%2E/./g' | sed 's/%21/!/g' | sed 's/%3F/?/g')
    # Remove everything except letters, numbers, comma, period, exclamation mark, question mark, and space
    echo "$decoded" | sed 's/[^a-zA-Z0-9 ,.!?]//g'
}

# -- Sjekker om bruker er logget inn -- #
if [ -z "$HTTP_COOKIE" ]; then
    LOGGED_IN=0
else 

    # Send xml forespørsel til backend for å sjekke om bruker er logget inn
    COOKIE_RESPONSE=$(curl -s -X PUT "http://192.168.1.120:8180/Diktdatabase/Bruker" -H "accept: text/xml" -H "Cookie: $HTTP_COOKIE")

    # Sjekke XML respons fra backend 
    if echo "$COOKIE_RESPONSE" | grep -q "<message><text> Gyldig cookie! </text></message>"; then
        LOGGED_IN=1
    else
        LOGGED_IN=0
    fi    
fi


# --- GET --- #
if [ "$REQUEST_METHOD" = "GET" ]; then
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
fi

TITTEL=""
TEKST=""
BODY=""
xml_request=""
# --- POST --- #
if [ "$REQUEST_METHOD" = "POST" ] && [ "$LOGGED_IN" -eq 1 ]; then
    read BODY

    TITTEL=$(sanitize "$(echo "$BODY" | sed 's/.*tittel=\([^&]*\).*/\1/')")
    TEKST=$(sanitize "$(echo "$BODY" | sed 's/.*tekst=\([^&]*\).*/\1/')")

    # Build the XML body
    xml_request="<Diktsamling><Dikt><Tittel>$TITTEL</Tittel><Tekst>$TEKST</Tekst></Dikt></Diktsamling>"

    # Send the XML to the backend server
    curl_output=$(curl -s -X POST "http://192.168.1.120:8180/Diktdatabase/Diktsamling/$TITTEL" -H "Cookie: $HTTP_COOKIE" -H "accept: text/xml" -H "Content-Type: text/xml" -d "$xml_request")
fi

echo "Content-type:text/html;charset=utf-8"
echo



cat << EOF
<!DOCTYPE html>
<html>
    <head>
        <title>Dikt Search</title>
        <link rel="stylesheet" type="text/css" media="screen" href="/css/style.css" />
    </head>

    <body>
        
        <!-- Left side of page -->
        <div class="left-side">
            
            <!-- Søk Form -->
            <form action="" method="get">
                <label for="dikt_tittel">Dikt search:</label>
                <input type="text" id="dikt_tittel" name="tittel" placeholder="Tittel">
                <input type="submit" value="search" class="submit-btn">
            </form>

            <!-- Vis alle dikt knapp -->
            <form action="" method="get">
                <input type="submit" name="show_all" value="vis-alle-dikt" class="submit-btn" >
            </form>

            <div class="centered-content">
  DEBUG INFO:
  $QUERY_STRING
  $REQUEST_METHOD
  $HTTP_COOKIE
  $COOKIE_RESPONSE
  $LOGGED_IN
  $BODY
tittl=        $TITTEL
tekst=        $TEKST
-----------------------
  Dikt:
-----------------------
$CURL_OUTPUT
            </div>

        </div>

        <!-- Right side of page -->
        <div class="right-side">
        
            <!-- Sende inn dikt Form -->
            <form action="" method="post" class="dikt-form">
                
                <div class="form-group">
                    <label for="tittel">Tittel:</label>
                    <input type="text" id="tittel" name="tittel" class="form-control">
                </div>
                <div class="form-group">
                    <label for="tekst">Tekst:</label>
                    <textarea id="tekst" name="tekst" class="form-control"></textarea> <!-- Changed to textarea -->
                </div>
                <div class="form-group">
                    <input type="submit" value="send-inn-dikt" class="submit-btn">
                </div>

            </form>

        </div>

  </body>
</html>
EOF

