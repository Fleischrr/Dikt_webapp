#!/bin/sh
# Restfull API for SQLite-databaser
# Dato: 13.10.2023
# Updated: 27.10.2023
# ---- ---- ---- ---- ---- ---- ---- #

# GLOBAL Variabler
LOGGED_IN=0
XSD_ROOT="/usr/local/apache2/cgi-bin/schemas/"


# Funksjon for å skrive slutten av HTTP-headeren
write_header () {
    echo "Content-type: text/xml;charset=utf-8"
    echo
}

# Funksjon for error-meldinger
ERROR_MSG () {
    local message="$1"

    write_header
    echo "$message"
    exit 1
}

# ---- ---- ---- ---- ---- #
# --- Foråndssjekker --- #
# ---- ---- ---- ---- ---- #

# REQUEST_URI kan ikke være tom
if [ -z "$REQUEST_URI" ] || [ "/" = "$REQUEST_URI" ]; then
    ERROR_MSG "<ERROR>\n\t<text> Mangler REQUEST_URI! </text>\n</ERROR>"
fi


# -- Henter variabler fra URI -- #
# Fjerner eventuelle '/' tegn i starten og slutten av URI
input="${REQUEST_URI#/}"
input="${input%/}"

# Deler opp input i variabler separert av '/'
database="${input%%/*}"

# Sjekker om input inneholder element eller bare tabell
if echo "$REQUEST_URI" | grep -qE '^/[^/]+/[^/]+/[^/]+$'; then
    sti="${input#*/}"
    tabell="${sti%%/*}"
    element="${sti#*/}"
else 
    tabell="${input#*/}"
fi


# -- Saniterer input. Fjerner alle tegn som ikke er a-z, A-Z eller 0-9 -- #
database=$(echo "$database" | sed 's/[^a-zA-Z]//g')
tabell=$(echo "$tabell" | sed 's/[^a-zA-Z]//g')
element=$(echo "$element" | sed 's/[^a-zA-Z0-9]//g')


# -- Sjekker om database finnes -- #
if [ "$database" != "Diktdatabase" ]; then
    ERROR_MSG "<ERROR>\n\t<text> Databasen \"$database\" finnes ikke! </text>\n</ERROR>"
else
    database="$database.db"
fi


# -- Sjekker om bruker er logget inn -- #
if [ -z "$HTTP_COOKIE" ]; then
    LOGGED_IN=0
else 
    # Henter session-cookie 
    session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=//g')

    # Sjekker om session-cookie finnes i databasen
    if echo "SELECT * FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $database | grep -qE '^' ; then
        LOGGED_IN=1
        EPOST=$(echo "SELECT Epost FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $database)
    else
        LOGGED_IN=0
    fi

fi

# ---- ---- ---- ---- ---- ---- #
# ---- ---- RESTfull API ---- ---- #
# ---- ---- ---- ---- ---- ---- #

# ---- ---- ---- ---- ---- ---- #
# ---- DIKTSAMLING TABELL ---- #
if [ "$tabell" = "Diktsamling" ]; then

    # ----  GET  ---- #
    if [ "$REQUEST_METHOD" = "GET" ]; then
        write_header

        # Sjekker om element er satt, henter tabell hvis ikke
        if [ -z "$element" ]; then
            # Konverterer fra JSON til XML
            echo "SELECT * FROM $tabell;"               |\
            sqlite3 --json $database                        |\
            jq .                                            |\
            sed 's|"\(.*\)": "*\(.*\)",*|<\1> \2 </\1>|'    |\
            sed 's/"\(.*\)": \([0-9]*\),/<\1> \2 <\/\1>/g'  |\
            sed "s/{/<Dikt>/"                            |\
            sed "s|},*|</Dikt>|"                         |\
            sed "s/\[/<$tabell\>/"               |\
            sed "s|\],*|</$tabell>|"             |\
            grep -v ": null"
        else
            # Sjekk om element finnes i tabell
            if ! echo "SELECT * FROM $tabell WHERE Tittel = '$element';" | sqlite3 $database | grep -qE '^'; then
                echo "<ERROR>\n\t<text> Diktet \"$element\" finnes ikke! </text>\n</ERROR>"
                exit 1
            else
                echo "SELECT * FROM $tabell WHERE Tittel = '$element';"  |\
                sqlite3 --json $database                                |\
                jq .                                                    |\
                sed 's|"\(.*\)": "*\(.*\)",*|<\1> \2 </\1>|'            |\
                sed 's/"\(.*\)": \([0-9]*\),/<\1> \2 <\/\1>/g'          |\
                sed "s/{/<Dikt>/"                                    |\
                sed "s|},*|</Dikt>|"                                 |\
                sed "s/\[/<$tabell\>/"                         |\
                sed "s|\],*|</$tabell>|"                       |\
                grep -v ": null"        
            fi

        fi

    fi

    # ----  DELETE  ---- #
    if [ "$REQUEST_METHOD" = "DELETE" ]; then

        # Sjekker om bruker er logget inn
        if [ $LOGGED_IN -eq 0 ]; then
            ERROR_MSG "<ERROR>\n\t<text> Du er ikke logget inn! </text>\n</ERROR>"
        fi

        if [ -z "$element" ]; then
            # Hvis element er tom, slett alle dikt til bruker

            # Sjekker om bruker har dikt, hvis ja, slett alle dikt til bruker
            if ! echo "SELECT * FROM $tabell WHERE Epost = '$EPOST';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Bruker $EPOST har ingen dikt i databsen! </text>\n</ERROR>"
            else
                write_header

                # Sletter alle dikt til bruker og sender xml respnse
                echo "DELETE FROM $tabell WHERE Epost = '$epost';" | sqlite3 $database
                echo "<message>\n\t<text> Alle dikt til bruker $epost er slettet! </text>\n\r</message>"
            fi
        else
            # Hvis element ikke er tom, slett spesifikt dikt

            # Sjekker om diktet finnes i databasen
            if ! echo "SELECT * FROM $tabell WHERE Tittel = '$element';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Diktet \"$element\" finnes ikke! </text>\n</ERROR>"
            else        
                write_header

                # Sletter diktet og sender xml respnse
                echo "DELETE FROM $tabell WHERE Tittel = '$element';" | sqlite3 $database   
                echo "<message>\n\t<text> Diktet \"$element\" er slettet! </text>\n\r</message>"
            fi

        fi

    fi

    # ----  POST  ---- #
    if [ "$REQUEST_METHOD" = "POST" ]; then
 
        # Sjekker om bruker er logget inn
        if [ $LOGGED_IN -eq 0 ]; then
            ERROR_MSG "<ERROR><text> Du er ikke logget inn! </text></ERROR>"
        fi

        # Sjekker om element er satt
        if [ -z "$element" ] ; then
            ERROR_MSG "<ERROR><text> Element må være satt! </text></ERROR>"
        fi

        # XML Validasjon
        XSD_FILE="${XSD_ROOT}dikt_schema.xsd"
        XML_DATA=$(cat)
        validation_result=$(echo "$XML_DATA" | xmllint --schema "$XSD_FILE" --noout - 2>&1)

        if [ "$validation_result" = "- validates" ]; then
            TITTEL=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/$tabell/Dikt/Tittel)" - )
            TEKST=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/$tabell/Dikt/Tekst)" - )

            # Validerer brukerinput fra XML
            TITTEL=$(echo "$TITTEL" | sed 's/[^a-zA-Z0-9]//g')
            TEKST=$(echo "$TEKST" | sed 's/[^a-zA-Z0-9.,!? ]//g')    

            # sjekker om Tittel i XML er lik element i URI
            if [ "$element" != "$TITTEL" ]; then
                ERROR_MSG "<ERROR>\n\t<text> Tittel i XML matcher ikke element i URI! </text>\n</ERROR>"
            fi

            # Sjekker om diktet allerede eksisterer
            if echo "SELECT * FROM $tabell WHERE Tittel = '$TITTEL';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Diktet \"$TITTEL\" finnes allerede! </text>\n</ERROR>"
            fi

            # Legger til diktet i databasen
            echo "INSERT INTO $tabell VALUES ('$TITTEL', '$EPOST', '$TEKST');" | sqlite3 $database
            
            # -- RESPONSE -- #
            write_header
            echo "<message>\n\t<text> Følgende er nå i diktsamlingen</text>"
            echo "\t<Tittel> $TITTEL </Tittel>"
            echo "\t<Epost> $EPOST </Epost>"
            echo "\t<Tekst> $TEKST </Tekst>\n</message>"
            exit 0
        else
            ERROR_MSG "<ERROR>\n\t<text> XML er ikke validert! </text>\n\r</ERROR>"
        fi

    fi


    # ----  PUT  ---- #
    if [ "$REQUEST_METHOD" = "PUT" ]; then

        # Sjekker om bruker er logget inn
        if [ $LOGGED_IN -eq 0 ]; then
            ERROR_MSG "<ERROR>\n\t<text> Du er ikke logget inn! </text>\n</ERROR>"
        fi

        # Sjekker om element er satt
        if [ -z "$element" ]; then
            ERROR_MSG "<ERROR>\n\t<text> Element må være satt! </text>\n</ERROR>"
        fi

        # XML Validasjon
        XSD_FILE="${XSD_ROOT}dikt_schema.xsd"
        XML_DATA=$(cat)
        validation_result=$(echo "$XML_DATA" | xmllint --schema "$XSD_FILE" --noout - 2>&1)

        if [ "$validation_result" = "- validates" ]; then

            # Henter ut elementer fra XML
            TITTEL=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/$tabell/Dikt/Tittel)" - )
            TEKST=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/$tabell/Dikt/Tekst)" - )

            # Validerer brukerinput fra XML
            TITTEL=$(echo "$TITTEL" | sed 's/[^a-zA-Z0-9]//g')
            TEKST=$(echo "$TEKST" | sed 's/[^a-zA-Z0-9.,!? ]//g')    
            
            # Sjekk om diktet ikke eksisterer
            if ! echo "SELECT * FROM $tabell WHERE Tittel = '$element';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Diktet \"$element\" finnes ikke! </text>\n</ERROR>"
            fi

            # Sjekker om TITTEL finnes allerede i databasen
            if echo "SELECT * FROM $tabell WHERE Tittel = '$TITTEL';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Diktet \"$TITTEL\" finnes allerede! Velg en annen tittel. </text>\n</ERROR>"
            fi

            # Oppdaterer diktet i databasen
            echo "UPDATE $tabell SET Tittel = '$TITTEL', Epost = '$EPOST', Tekst = '$TEKST' WHERE Tittel = '$element';" | sqlite3 $database
            
            # -- RESPONSE -- #
            write_header
            echo "<message>\n\t<text>Følgende er nå oppdatert i diktsamlingen</text>"
            echo "\t<Tittel> $TITTEL </Tittel>"
            echo "\t<Epost> $EPOST </Epost>"
            echo "\t<Tekst> $TEKST </Tekst>\n</message>"
        else
            ERROR_MSG "<ERROR>\n\t<text> XML er ikke validert! </text>\n\r</ERROR>"
        fi

    fi


elif [ "$tabell" = "Bruker" ]; then
    # ---- ---- ---- ---- #
    # ---- BRUKER TABELL ---- #
    
    # ----  GET  ---- #
    # - Logg inn - #
    if [ "$REQUEST_METHOD" = "GET" ]; then
        
        # XML Validasjon
        XSD_FILE="${XSD_ROOT}login_schema.xsd"
        XML_DATA=$(cat)
        validation_result=$(echo "$XML_DATA" | xmllint --schema "$XSD_FILE" --noout - 2>&1)

        if [ "$validation_result" = "- validates" ]; then
            
            # Henter ut elementer fra XML            
            EPOST=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/Login/Epost)" - )
            PSSW=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/Login/Passord)" - )

            # Validerer brukerinput fra XML
            EPOST=$(echo "$EPOST" | sed 's/[^a-zA-Z0-9@.]//g')
            PSSW=$(echo -n "$PSSW" | sed 's/[^a-zA-Z0-9]//g')

            # Sjekker om bruker eksisterer i databasen
            if ! echo "SELECT * FROM $tabell WHERE Epost = '$EPOST';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Brukeren \"$EPOST\" finnes ikke! </text>\n</ERROR>"
            fi

            # Henter salt fra databasen og hasher passordet
            SALT=$(echo "SELECT Salt FROM $tabell WHERE Epost = '$EPOST';" | sqlite3 $database)
            PSSW_SALT="${SALT}${PSSW}"
            PSSW_HASH=$(echo -n "$PSSW_SALT" | sha256sum | awk '{print $1}')

            # Sjekker om passordet er riktig
            if ! echo "SELECT * FROM $tabell WHERE Epost = '$EPOST' AND Passordhash = '$PSSW_HASH';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Feil passord! PSSW: $PSSW_SALT og HASH: $PSSW_HASH </text>\n</ERROR>"
            fi

            # Hvis bruker har en session-cookie fra før, slett den
            if echo "SELECT * FROM Sesjon WHERE Epost = '$EPOST';" | sqlite3 $database | grep -qE '^' ; then
                echo "DELETE FROM Sesjon WHERE Epost = '$EPOST';" | sqlite3 $database
            fi

            # Genererer en session-cookie og legger til i databasen
            session_cookie=$(head -c 32 /dev/urandom | base64 | tr -d '+/' | tr -d '=')
            echo "INSERT INTO Sesjon VALUES ('$EPOST', '$session_cookie');" | sqlite3 $database

            # -- RESPONSE -- #
            # Header
            echo "Set-Cookie: session=$session_cookie; HttpOnly"
            write_header

            # Body
            echo "<message>\n\t<text> Brukeren \"$EPOST\" er logget inn! </text>\n</message>"
        else
            ERROR_MSG "<ERROR>\n\t<text> XML er ikke validert! </text>\n\r</ERROR>"
        fi

    fi

    # ----  POST  ---- #
    # - Registrer bruker - #
    if [ "$REQUEST_METHOD" = "POST" ]; then
        
        # XML Validasjon
        XSD_FILE="${XSD_ROOT}bruker_schema.xsd"
        XML_DATA=$(cat)
        validation_result=$(echo "$XML_DATA" | xmllint --schema "$XSD_FILE" --noout - 2>&1)

        if [ "$validation_result" = "- validates" ]; then
            
            # Henter ut elementer fra XML
            EPOST=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/$tabell/Epost)" - )        
            FORNAVN=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/$tabell/Fornavn)" - )
            ETTERNAVN=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/$tabell/Etternavn)" - )
            PSSW=$(echo "$XML_DATA" | xmllint --xpath "normalize-space(/Autorisering/$tabell/Passord)" - )
            
            # Validerer brukerinput fra XML
            EPOST=$(echo "$EPOST" | sed 's/[^a-zA-Z0-9@.]//g')
            FORNAVN=$(echo "$FORNAVN" | sed 's/[^a-zA-Z]//g')
            ETTERNAVN=$(echo "$ETTERNAVN" | sed 's/[^a-zA-Z]//g')
            PSSW=$(echo -n "$PSSW" | sed 's/[^a-zA-Z0-9]//g')

            # Sjekker om bruker allerede eksisterer basert på epost
            if echo "SELECT * FROM $tabell WHERE Epost = '$EPOST';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Brukeren \"$EPOST\" finnes allerede! </text>\n</ERROR>"
            fi

            # Hasher passordet
            SALT=$(head -c 15 /dev/urandom | base64 -w 0)
            PSSW_SALT="${SALT}${PSSW}"
            PSSW_HASH=$(echo -n "$PSSW_SALT" | sha256sum | awk '{print $1}')

            # Legger til brukeren i databasen
            echo "INSERT INTO $tabell VALUES ('$EPOST', '$FORNAVN', '$ETTERNAVN', '$PSSW_HASH', '$SALT');" | sqlite3 $database
            
            # Genererer en session-cookie og legger til i databasen
            session_cookie=$(head -c 32 /dev/urandom | base64 | tr -d '+/' | tr -d '=')
            echo "INSERT INTO Sesjon VALUES ('$EPOST', '$session_cookie');" | sqlite3 $database
            
            # -- RESPONSE -- #
            # Header
            echo "Set-Cookie: session=$session_cookie; HttpOnly"
            write_header
            
            # Body
            echo "<message>\n\t<text> Brukeren \"$EPOST\" er registrert! </text>\n</message>"
            
        else
            ERROR_MSG "<ERROR>\n\t<text> XML er ikke validert! </text>\n\r</ERROR>"
        fi

    fi

    # ----  DELETE  ---- #
    if [ "$REQUEST_METHOD" = "DELETE" ]; then
        #XML_DATA=$(cat)
        
        # Sjekker om bruker er logget inn
        if [ -z "$HTTP_COOKIE" ]; then
            ERROR_MSG "<ERROR>\n\t<text> Du er ikke logget inn! </text>\n</ERROR>"
        else

            # Fjerner 'session=' fra cookie
            session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=//g')

            # Sjekker om session-cookie er gyldig
            if ! echo "SELECT * FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $database | grep -qE '^' ; then
                ERROR_MSG "<ERROR>\n\t<text> Session-cookie er ikke gyldig! </text>\n</ERROR>"
            fi

            # Sletter cookie fra databasen
            echo "DELETE FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $database

            # -- RESPONSE -- #
            # Header
            echo "Set-Cookie: "
            write_header

            # Body
            echo "<message>\n\t<text> Du er nå logget ut! </text>\n</message>"
        fi

    fi

else
    ERROR_MSG "<ERROR><text> Tabellen finnes ikke! Path: $database, PWD: $PWD </text></ERROR>"
fi

