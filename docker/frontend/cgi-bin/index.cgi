#!/bin/sh
# 
#

# --- GLOBAL Variabler --- #
CSS_IP="http://100.99.35.80/style/dikt.css"

LOGGED_IN=0
COOKIE_RESPONSE=""
QUERY_STRING=$(echo "$QUERY_STRING")
CURL_OUTPUT=""
SET_COOKIE=""


sanitize() {
    # Replace '+' with space
    local input=$(echo "$1" | sed 's/+/%20/g')
    # Decode only allowed characters
    local decoded=$(echo "$input" | sed 's/%20/ /g' | sed 's/%2C/,/g' | sed 's/%2E/./g' | sed 's/%21/!/g' | sed 's/%3F/?/g' | sed 's/%40/@/g')
    # Remove everything except letters, numbers, comma, period, exclamation mark, question mark, and space
    echo "$decoded" | sed 's/[^a-zA-Z0-9 ,.!?@]//g'
}

# -- Sjekker om bruker er logget inn -- #
if [ -z "$HTTP_COOKIE" ]; then
    LOGGED_IN=0
else 

    # Send xml forespørsel til backend for å sjekke om bruker er logget inn
    COOKIE_RESPONSE=$(curl -s -X PUT "http://172.20.0.2/Diktdatabase/Bruker" -H "accept: text/xml" -H "Cookie: $HTTP_COOKIE")

    # Sjekke XML respons fra backend 
    if echo "$COOKIE_RESPONSE" | grep -q "<message><text> Gyldig cookie! </text></message>"; then
        LOGGED_IN=1
    else
        LOGGED_IN=0
    fi    
fi


# --- Lese dikt (GET) --- #
if [ "$REQUEST_METHOD" = "GET" ]; then
    if echo "$QUERY_STRING" | grep -q "show_all="; then
        
        # Execute the curl command and capture its output
        CURL_OUTPUT=$(curl -s -X GET "http://172.20.0.2/Diktdatabase/Diktsamling" -H "accept: text/xml")

    elif echo "$QUERY_STRING" | grep -q "tittel="; then
        
        # Hent tittel fra URL og saniterer
        POEM_TITLE=$(echo "$QUERY_STRING" | sed 's/.*tittel=\([^&]*\).*/\1/' | sed 's/%20/ /g')
        
        CURL_OUTPUT=$(curl -s -X GET "http://172.20.0.2/Diktdatabase/Diktsamling/$POEM_TITLE" -H "accept: text/xml")
    fi

fi

# --- Logg inn (GET) --- #
if [ "$REQUEST_METHOD" = "POST" ] && [ "$LOGGED_IN" -eq 0 ]; then
    read BODY

    # Hent email og passord fra body og saniterer
    EMAIL=$(sanitize "$(echo "$BODY" | sed 's/.*epost=\([^&]*\).*/\1/')")
    PASSWORD=$(sanitize "$(echo "$BODY" | sed 's/.*password=\([^&]*\).*/\1/')")

    # XML Request i henhold til XML-schema
    xml_request="<Autorisering><Login><Epost>$EMAIL</Epost><Passord>$PASSWORD</Passord></Login></Autorisering>"

    # Send forespørsel til backend server
    CURL_OUTPUT=$(curl -v -X GET "http://172.20.0.2/Diktdatabase/Bruker" \
        -H "accept: text/xml" \
        -H "Content-Type: text/xml" \
        -d "$xml_request" 2>&1)

    # Hente "Set-Cookie" command fra backend svar
    SET_COOKIE=$(echo "$CURL_OUTPUT" | grep 'Set-Cookie' | sed -e 's/^< //')
    
fi


# --- LEGGE TIL (POST) OG OPPDATERE (PUT) DIKT --- #
if [ "$REQUEST_METHOD" = "POST" ] && [ "$LOGGED_IN" -eq 1 ]; then
    read BODY

    # Hvis gammel tittel ikke er spesifisert, legg til dikt
    if ! echo "$BODY" | grep -q "old_tittel="; then
        
        # Hent tittel og tekst fra body og saniterer
        TITTEL=$(sanitize "$(echo "$BODY" | sed 's/.*tittel=\([^&]*\).*/\1/')")
        TEKST=$(sanitize "$(echo "$BODY" | sed 's/.*tekst=\([^&]*\).*/\1/')")

        # XML Request i henhold til XML-schema
        xml_request="<Diktsamling><Dikt><Tittel>$TITTEL</Tittel><Tekst>$TEKST</Tekst></Dikt></Diktsamling>"

        # Send forespørsel til backend server
        CURL_OUTPUT=$(curl -s -X POST "http://172.20.0.2/Diktdatabase/Diktsamling/$TITTEL" \
            -H "Cookie: $HTTP_COOKIE" \
            -H "accept: text/xml" \
            -H "Content-Type: text/xml" \
            -d "$xml_request")
    fi

    # Hvis gammel tittel er spesifisert, oppdater dikts
    if echo "$BODY" | grep -q "old_tittel="; then
        
        # Hent gammel-tittel, ny-tittel og ny-tekst fra body og saniterer
        OLD_TITTEL=$(sanitize "$(echo "$BODY" | sed 's/.*old_tittel=\([^&]*\).*/\1/')")
        NEW_TITTEL=$(sanitize "$(echo "$BODY" | sed 's/.*new_tittel=\([^&]*\).*/\1/')")
        NEW_TEKST=$(sanitize "$(echo "$BODY" | sed 's/.*new_tekst=\([^&]*\).*/\1/')")
            
        # XML Request i henhold til XML-schema
        xml_request="<Diktsamling><Dikt><Tittel>$NEW_TITTEL</Tittel><Tekst>$NEW_TEKST</Tekst></Dikt></Diktsamling>"
        
        # Send forespørsel til backend server
        CURL_OUTPUT=$(curl -s -X PUT "http://172.20.0.2/Diktdatabase/Diktsamling/$OLD_TITTEL" \
            -H "Cookie: $HTTP_COOKIE" \
            -H "accept: text/xml" \
            -H "Content-Type: text/xml" \
            -d "$xml_request")
    fi

fi

# --- SLETTE DIKT (DELETE) --- #
if [ "$REQUEST_METHOD" = "GET" ] && [ "$LOGGED_IN" -eq 1 ] && echo "$QUERY_STRING" | grep -q "^del_"; then

    # Hvis spesifisert, slett dikt
    if echo "$QUERY_STRING" | grep -q "del_tittel="; then

        # Hent tittel fra URL og saniterer
        POEM_TITLE=$(echo "$QUERY_STRING" | sed 's/.*del_tittel=\([^&]*\).*/\1/' | sed 's/%20/ /g')
        
        # Send forespørsel til backend server
        CURL_OUTPUT=$(curl -s -X DELETE "http://172.20.0.2/Diktdatabase/Diktsamling/$POEM_TITLE" \
        -H "Cookie: $HTTP_COOKIE" \
        -H "accept: text/xml")
        
    fi

    # Hvis uspesifisert, slett alle dikt
    if echo "$QUERY_STRING" | grep -q "del_all="; then
        
        # Send forespørsel til backend server
        CURL_OUTPUT=$(curl -s -X DELETE "http://172.20.0.2/Diktdatabase/Diktsamling" \
        -H "Cookie: $HTTP_COOKIE" \
        -H "accept: text/xml")
    fi

fi

# --- HEADER --- #
# Hvis bruker har logget inn, gi cookie 
if [ ! -z "$SET_COOKIE" ]; then
    echo $SET_COOKIE
    LOGGED_IN=1
fi

echo "Content-type:text/html;charset=utf-8"
echo

# ------ Hvis bruker er logget inn ------ #
if [ "$LOGGED_IN" -eq 1 ]; then    
cat << EOF
<!DOCTYPE html>
<html>
    <head>
        <title>Diktsamling</title>
        <link rel="stylesheet" type="text/css" media="screen" href="$CSS_IP" />
    </head>

    <body>

        <!-- Left side of page -->
        <div class="left-side">
            <h1> Gruppe 5 sin diktsamling! </h1>
            <a href="http://localhost"> Gruppe 5 sin Hjemmeside </a>
            <br> Du er logget inn!
            <p>

            <!-- Søk Form -->
            <form action="" method="get">
                <label for="dikt_tittel">Dikt search:</label>
                <input type="text" id="dikt_tittel" name="tittel" placeholder="Tittel">
                <input type="submit" value="search" class="submit-btn">
            </form>

            <!-- Vis alle dikt knapp -->
            <form action="" method="get">
                <input type="submit" name="show_all" value="Vis alle dikt" class="submit-btn" >
            </form>

            <div class="centered-content">
-----------------------
  Dikt:
-----------------------
$CURL_OUTPUT
-----------------------
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
                    <input type="submit" value="Send inn dikt" class="submit-btn">
                </div>

            </form>

            <!-- Slette dikt Form -->
            <form action="" method="delete" class="dikt-form">
                 <div class="form-group">
                    <label for="del_tittel">Tittel på dikt som skal slettes:</label>
                    <input type="text" id="del_tittel" name="del_tittel" class="form-control">
                </div>
                <div class="form-group">
                    <input type="submit" value="Slett dikt" class="submit-btn">
                </div>
            </form>
            <form action="" method="get">
                <input type="submit" name="del_all" value="Slett alle dikt" class="submit-btn" >
            </form>


            <!-- Oppdatere dikt Form -->
            <form action="/" method="post" class="dikt-form">
                
                <div class="form-group">
                    <label for="old_tittel">Gammel Tittel:</label>
                    <input type="text" id="old_tittel" name="old_tittel" class="form-control">
                </div>
                <div class="form-group">
                    <label for="new_tittel">Ny Tittel:</label>
                    <input type="text" id="new_tittel" name="new_tittel" class="form-control">
                </div>
                <div class="form-group">
                    <label for="new_tekst">Ny Tekst:</label>
                    <textarea id="new_tekst" name="new_tekst" class="form-control" placeholder="Skriv inn ny tekst her!"></textarea> 
                </div>
                <div class="form-group">
                    <input type="submit" value="Oppdatere dikt" class="submit-btn">
                </div>

            </form>


        </div>

  </body>
</html>
EOF

else
# ------ Hvis bruker ikke er logget inn ------ #
cat << EOF
<!DOCTYPE html>
<html>
    <head>
        <title>Diktsamling</title>
        <link rel="stylesheet" type="text/css" media="screen" href="$CSS_IP" />
    </head>

    <body>

        <!-- Left side of page -->
        <div class="left-side">
            <h1> Gruppe 5 sin diktsamling! </h1>
            <a href="http://localhost"> Gruppe 5 sin Hjemmeside </a>
            <p>

            <!-- Søk Form -->
            <form action="" method="get">
                <label for="dikt_tittel">Dikt search:</label>
                <input type="text" id="dikt_tittel" name="tittel" placeholder="Tittel">
                <input type="submit" value="search" class="submit-btn">
            </form>

            <!-- Vis alle dikt knapp -->
            <form action="" method="get">
                <input type="submit" name="show_all" value="Vis alle dikt" class="submit-btn" >
            </form>

            <div class="centered-content">
-----------------------
  Dikt:
-----------------------
$CURL_OUTPUT
-----------------------
            </div>

        </div>
    
        <!-- Right side of page -->
        <div class="right-side">
        
            <!-- Logg in Form -->
            <form action="/" method="post" class="dikt-form">
                
                <div class="form-group">
                    <label for="epost">Epostadresse:</label>
                    <input type="email" id="epost" name="epost" class="form-control">
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" class="form-control">
                </div>
                <div class="form-group">
                    <input type="submit" value="Logg inn" class="submit-btn">
                </div>

            </form>
    
    
    </body>
</html>
EOF
fi
