#!/bin/sh
# Restfull API for SQLite-database
# ---- ---- ---- ---- ---- ---- ---- #

# ----- --- ---- --- -----  #
# --- GLOBALE Variabler --- #
LOGGED_IN=0
XSD_ROOT="/usr/local/apache2/cgi-bin/schemas/"


# ----- ----- -----  #
# --- Funksjoner --- #

# For å skrive slutten av HTTP-headeren
WRITE_HEADER () {
    echo "Content-type: text/xml;charset=utf-8"
    echo
}

# Funktion for å sanitere input
SANITIZE() {
    local value="$1"
    local level="$2"

    case "$level" in
        strict)
            echo "$value" | sed 's/[^a-zA-Z0-9]//g'
            ;;
        email)
            echo "$value" | sed 's/[^a-zA-Z0-9@.-_]//g'
            ;;
        *)
            echo "$value" | sed 's/[^a-zA-Z0-9 .,-_!?]//g' 
            ;;
    esac
}



# For vanlige meldinger
STD_MSG () {
    local message="$1"
   
    echo -n "<Message><Text>$message</Text></Message>"
}

# For error meldinger
ERROR_MSG () {
    local message="$1"
   
    WRITE_HEADER
    echo -n "<Error><Message>$message</Message></Error>"
    exit 1
}

# ---- --- ---- --- ---- #
# --- Foråndssjekker --- #

# REQUEST_URI kan ikke være tom
if [ -z "$REQUEST_URI" ] || [ "/" = "$REQUEST_URI" ]; then
    ERROR_MSG "Mangler REQUEST_URI!"
fi


# Henter variabler fra URI:
# Sjekker om URI har form '/db/tabl/' eller '/db/tabl/elm'
# Deler også opp input i variabler separert med '/'
if echo "$REQUEST_URI" | grep -qE '^/[^/]+/[^/]+/$'; then
    DATABASE=$(echo $REQUEST_URI | cut -f2 -d/)
    TABELL=$(echo $REQUEST_URI | cut -f3 -d/)
    ELEMENT=""

elif echo "$REQUEST_URI" | grep -qE '^/[^/]+/[^/]+/[^/]+$'; then
    DATABASE=$(echo $REQUEST_URI | cut -f2 -d/)
    TABELL=$(echo $REQUEST_URI | cut -f3 -d/)
    ELEMENT=$(echo $REQUEST_URI | cut -f4 -d/)

else 
    ERROR_MSG "Feil i URI!"
fi

# Saniterer input. Fjerner alle tegn som ikke er a-z, A-Z eller 0-9
DATABASE=$(SANITIZE "$DATABASE" "strict")
TABELL=$(SANITIZE "$TABELL" "strict")
ELEMENT=$(SANITIZE "$ELEMENT" "strict")


# Sjekker om database finnes
if [ "$DATABASE" != "Diktdatabase" ]; then
    ERROR_MSG "Databasen \"$DATABASE\" finnes ikke!"
else
    DATABASE="$DATABASE.db"
fi


# Sjekker om bruker er logget inn 
if [ -z "$HTTP_COOKIE" ]; then
    LOGGED_IN=0
else 
    # Henter session-cookie verdi og saniterer input
    session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=\([^;]*\).*/\1/')
    session_cookie=$(SANITIZE "$session_cookie" "strict")

    # Sjekker om session-cookie finnes i databasen
    if echo "SELECT * FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $DATABASE | grep -qE '^' ; then
        LOGGED_IN=1
        EPOST=$(echo "SELECT Epost FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $DATABASE)
    else
        LOGGED_IN=0
    fi

fi


# ---- ---- --- ---- ---- ---- #
# --- --- RESTfull API --- --- #
# ---- ---- --- ---- ---- ---- #

# ---- ---- --- ---- ---- ---- #
# ---- DIKTSAMLING TABELL ---- #
if [ "$TABELL" = "Diktsamling" ]; then

    case "$REQUEST_METHOD" in
        GET)
            # ---  Lese dikt fra samlingen  --- #

            WRITE_HEADER

            # Sjekker om element er satt, henter tabell hvis ikke
            if [ -z "$ELEMENT" ]; then

                # Konverterer fra JSON til XML og sender response
                echo "SELECT * FROM $TABELL;"               |\
                sqlite3 --json $DATABASE                        |\
                jq .                                            |\
                sed 's|"\(.*\)": "*\(.*\)",*|<\1> \2 </\1>|'    |\
                sed 's/"\(.*\)": \([0-9]*\),/<\1> \2 <\/\1>/g'  |\
                sed "s/{/<Dikt>/"                            |\
                sed "s|},*|</Dikt>|"                         |\
                sed "s/\[/<$TABELL\>/"               |\
                sed "s|\],*|</$TABELL>|"             |\
                grep -v ": null"

            else

                # Sjekk om element finnes i tabell
                if ! echo "SELECT * FROM $TABELL WHERE Tittel = '$ELEMENT';" | sqlite3 $DATABASE | grep -qE '^'; then
                    ERROR_MSG "Diktet \"$ELEMENT\" finnes ikke!"
                else

                    # Konverterer fra JSON til XML og sender response
                    echo "SELECT * FROM $TABELL WHERE Tittel = '$ELEMENT';"  |\
                    sqlite3 --json $DATABASE                                |\
                    jq .                                                    |\
                    sed 's|"\(.*\)": "*\(.*\)",*|<\1> \2 </\1>|'            |\
                    sed 's/"\(.*\)": \([0-9]*\),/<\1> \2 <\/\1>/g'          |\
                    sed "s/{/<Dikt>/"                                    |\
                    sed "s|},*|</Dikt>|"                                 |\
                    sed "s/\[/<$TABELL\>/"                         |\
                    sed "s|\],*|</$TABELL>|"                       |\
                    grep -v ": null"        
                fi

            fi
            ;;
        DELETE)
            # ----  Slette dikt fra samlingen  ---- #

            # Sjekker om bruker er logget inn
            if [ $LOGGED_IN -eq 0 ]; then
                ERROR_MSG "Du er ikke logget inn!"
            fi

            if [ -z "$ELEMENT" ]; then
                # Hvis element er tom, slett alle dikt til bruker

                # Sjekker om bruker har dikt, hvis ja, slett alle dikt til bruker
                if ! echo "SELECT * FROM $TABELL WHERE Epost = '$EPOST';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Bruker $EPOST har ingen dikt i databsen!"
                else
                    
                    # Sletter alle dikt til bruker og sender xml respnse
                    echo "DELETE FROM $TABELL WHERE Epost = '$EPOST';" | sqlite3 $DATABASE

                    WRITE_HEADER
                    STD_MSG "Alle dikt til bruker $EPOST er slettet!"
                fi
            else
                # Hvis element ikke er tom, slett spesifikt dikt

                # Sjekker om diktet finnes i databasen
                if ! echo "SELECT * FROM $TABELL WHERE Tittel = '$ELEMENT' AND Epost = '$EPOST';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    
                    # Sjekker om bruker eier diktet eller om diktet eksisterer
                    if ! echo "SELECT * FROM $TABELL WHERE Tittel = '$ELEMENT';" | sqlite3 $DATABASE | grep -qE '^' ; then
                        ERROR_MSG "Diktet \"$ELEMENT\" finnes ikke!"
                    else
                        ERROR_MSG "Diktet \"$ELEMENT\" tilhører ikke bruker $EPOST!"
                    fi
                    
                else        
                    
                    # Sletter diktet og sender response
                    echo "DELETE FROM $TABELL WHERE Tittel = '$ELEMENT';" | sqlite3 $DATABASE   
                    
                    WRITE_HEADER
                    STD_MSG "Diktet \"$ELEMENT\" er slettet!"
                fi

            fi
            ;;
        POST)
            # ----  Sende inn dikt til diktsamlingen  ---- #

            # Sjekker om bruker er logget inn
            if [ $LOGGED_IN -eq 0 ]; then
                ERROR_MSG "Du er ikke logget inn!"
            fi

            # Sjekker om element er satt
            if [ -z "$ELEMENT" ] ; then
                ERROR_MSG "Element må være satt!"
            fi

            # XML Validasjon
            xsd_file="${XSD_ROOT}dikt_schema.xsd"
            xml_data=$(cat)
            validation_result=$(echo "$xml_data" | xmllint --schema "$xsd_file" --noout - 2>&1)

            if [ "$validation_result" = "- validates" ]; then
                
                # Henter ut verdier fra XML
                tittel=$(echo "$xml_data" | xmllint --xpath "normalize-space(/$TABELL/Dikt/Tittel)" - )
                tekst=$(echo "$xml_data" | xmllint --xpath "normalize-space(/$TABELL/Dikt/Tekst)" - )

                # Saniterer input
                tittel=$(SANITIZE "$tittel" "strict")
                tekst=$(SANITIZE "$tekst")

                # Sjekker om Tittel i XML er lik element i URL
                if [ "$ELEMENT" != "$tittel" ]; then
                    ERROR_MSG "Tittel i XML matcher ikke element i URI!"
                fi

                # Sjekker om diktet allerede eksisterer
                if echo "SELECT * FROM $TABELL WHERE Tittel = '$tittel';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Diktet \"$tittel\" finnes allerede!"
                fi

                # Legger til diktet i databasen
                echo "INSERT INTO $TABELL VALUES ('$tittel', '$EPOST', '$tekst');" | sqlite3 $DATABASE
                
                # -- RESPONSE -- #
                WRITE_HEADER
                echo -n "<Message><Info> Følgende er nå i diktsamlingen</Info>"
                echo -n "<Tittel> $tittel </Tittel>"
                echo -n "<Epost> $EPOST </Epost>"
                echo -n "<Tekst> $tekst </Tekst></Message>"
                exit 0
            else
                ERROR_MSG "XML er ikke validert!"
            fi
            ;;
        PUT)
            # ----  Oppdatere dikt i diktsamlingen  ---- #

            # Sjekker om bruker er logget inn
            if [ $LOGGED_IN -eq 0 ]; then
                ERROR_MSG "Du er ikke logget inn!"
            fi

            # Sjekker om element er satt
            if [ -z "$ELEMENT" ]; then
                ERROR_MSG "Element må være satt!"
            fi

            # XML Validasjon
            xsd_file="${XSD_ROOT}dikt_schema.xsd"
            xml_data=$(cat)
            validation_result=$(echo "$xml_data" | xmllint --schema "$xsd_file" --noout - 2>&1)

            if [ "$validation_result" = "- validates" ]; then

                # Henter ut elementer fra XML
                tittel=$(echo "$xml_data" | xmllint --xpath "normalize-space(/$TABELL/Dikt/Tittel)" - )
                tekst=$(echo "$xml_data" | xmllint --xpath "normalize-space(/$TABELL/Dikt/Tekst)" - )

                # Validerer brukerinput fra XML
                tittel=$(SANITIZE "$tittel" "strict")
                tekst=$(SANITIZE "$tekst")   
                
                # Sjekk om diktet ikke eksisterer
                if ! echo "SELECT * FROM $TABELL WHERE Tittel = '$ELEMENT';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Diktet \"$ELEMENT\" finnes ikke!"
                fi

                # Sjekker om ny tittel er ulik gammel tittel
                if [ "$ELEMENT" != "$tittel" ]; then
                    
                    # Sjekker om ny tittel allerede eksisterer
                    if echo "SELECT * FROM $TABELL WHERE Tittel = '$tittel';" | sqlite3 $DATABASE | grep -qE '^' ; then
                        ERROR_MSG "Den nye tittelen \"$tittel\" finnes allerede!"
                    fi
                fi

                # Oppdaterer diktet i databasen
                echo "UPDATE $TABELL SET Tittel = '$tittel', Epost = '$EPOST', Tekst = '$tekst' WHERE Tittel = '$ELEMENT';" | sqlite3 $DATABASE
                
                # -- RESPONSE -- #
                WRITE_HEADER
                echo -n "<Message><Info>Følgende er nå oppdatert i diktsamlingen</Info>"
                echo -n "<Tittel> $tittel </Tittel>"
                echo -n "<Epost> $EPOST </Epost>"
                echo -n "<Tekst> $tekst </Tekst></Message>"

            else
                ERROR_MSG "XML er ikke validert!"
            fi
            ;;
        *)
            ERROR_MSG "Ugyldig forespørsel mot Diktsamling!"
            ;;
    esac

# ---- --- ---- ---- ---- #
# ---- BRUKER TABELL ---- #
elif [ "$TABELL" = "Bruker" ]; then
    
    case "$REQUEST_METHOD" in
        POST)
            # ----  Logg inn  ---- #
                    
            # XML Validasjon
            xsd_file="${XSD_ROOT}login_schema.xsd"
            xml_data=$(cat)
            validation_result=$(echo "$xml_data" | xmllint --schema "$xsd_file" --noout - 2>&1)

            if [ "$validation_result" = "- validates" ]; then
                
                # Henter ut elementer fra XML            
                epost=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/Login/Epost)" - )
                pswd=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/Login/Passord)" - )

                # Validerer brukerinput fra XML
                epost=$(SANITIZE "$epost" "email")
                pswd=$(SANITIZE "$pswd")

                # Sjekker om bruker eksisterer i databasen
                if ! echo "SELECT * FROM $TABELL WHERE Epost = '$epost';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Brukeren \"$epost\" finnes ikke!"
                fi

                # Henter salt fra databasen og hasher passordet
                salt=$(echo "SELECT Salt FROM $TABELL WHERE Epost = '$epost';" | sqlite3 $DATABASE)
                pswd_salt="${salt}${pswd}"
                pswd_hash=$(echo -n "$pswd_salt" | sha256sum | awk '{print $1}')

                # Sjekker om passordet er riktig
                if ! echo "SELECT * FROM $TABELL WHERE Epost = '$epost' AND Passordhash = '$pswd_hash';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Feil passord!"
                fi

                # Hvis bruker har en session-cookie fra før, slett den
                if echo "SELECT * FROM Sesjon WHERE Epost = '$epost';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    echo "DELETE FROM Sesjon WHERE Epost = '$epost';" | sqlite3 $DATABASE
                fi

                # Genererer en session-cookie og legger til i databasen
                session_cookie=$(head -c 32 /dev/urandom | base64 | tr -d '+/' | tr -d '=')
                echo "INSERT INTO Sesjon VALUES ('$epost', '$session_cookie');" | sqlite3 $DATABASE

                # -- RESPONSE -- #
                # Header
                echo "Set-Cookie: session=$session_cookie; Path=/"
                WRITE_HEADER

                # Body
                STD_MSG "Brukeren \"$epost\" er logget inn!"
            else
                ERROR_MSG "XML er ikke validert!"
            fi
        ;;
        PUT)
            # ----  Registrer bruker  ---- #
            
            # XML Validasjon
            xsd_file="${XSD_ROOT}bruker_schema.xsd"
            xml_data=$(cat)
            validation_result=$(echo "$xml_data" | xmllint --schema "$xsd_file" --noout - 2>&1)

            if [ "$validation_result" = "- validates" ]; then
                
                # Henter ut elementer fra XML
                epost=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/$TABELL/Epost)" - )        
                fornavn=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/$TABELL/Fornavn)" - )
                etternavn=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/$TABELL/Etternavn)" - )
                pswd=$(echo "$xml_data" | xmllint --xpath "normalize-space(/Autorisering/$TABELL/Passord)" - )
                
                # Validerer brukerinput fra XML
                epost=$(SANITIZE "$epost" "email")
                fornavn=$(SANITIZE "$fornavn" "strict")
                etternavn=$(SANITIZE "$etternavn" "strict")
                pswd=$(SANITIZE "$pswd")

                # Sjekker om bruker allerede eksisterer basert på epost
                if echo "SELECT * FROM $TABELL WHERE Epost = '$epost';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Brukeren \"$epost\" finnes allerede!"
                fi

                # Hasher passordet
                salt=$(head -c 15 /dev/urandom | base64 -w 0)
                pswd_salt="${salt}${pswd}"
                pswd_HASH=$(echo -n "$pswd_salt" | sha256sum | awk '{print $1}')

                # Legger til brukeren i databasen
                echo "INSERT INTO $TABELL VALUES ('$epost', '$fornavn', '$etternavn', '$pswd_HASH', '$salt');" | sqlite3 $DATABASE
                
                # Genererer en session-cookie og legger til i databasen
                session_cookie=$(head -c 32 /dev/urandom | base64 | tr -d '+/' | tr -d '=')
                echo "INSERT INTO Sesjon VALUES ('$epost', '$session_cookie');" | sqlite3 $DATABASE
                
                # -- RESPONSE -- #
                # Header
                echo "Set-Cookie: session=$session_cookie; Path=/"
                WRITE_HEADER
                
                # Body
                STD_MSG "Brukeren \"$epost\" er registrert!"
                
            else
                ERROR_MSG "XML er ikke validert!"
            fi

        ;;
        *)
            ERROR_MSG "Ugyldig forespørsel mot Bruker!"
        ;;
    esac


# ---- --- ---- ---- ---- #
# ---- Sesjon TABELL ---- #
elif [ "$TABELL" = "Sesjon" ]; then


    case "$REQUEST_METHOD" in
        POST)
            # ----  Validering av cookie  ---- #

            # Sjekker om cookie er satt
            if [ -z "$HTTP_COOKIE" ]; then
                ERROR_MSG "Du er ikke logget inn!"
            else

                # Sjekker cookie gyldighet
                session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=\([^;]*\).*/\1/')
                
                if ! echo "SELECT * FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Session-cookie er ikke gyldig!"
                fi

                # -- RESPONSE -- #
                # Header
                WRITE_HEADER

                # Body
                STD_MSG "Gyldig cookie!"
            fi
        
        ;;
        DELETE)
            # ----  Logg ut  ---- #

            # Sjekker om bruker er logget inn
            if [ -z "$HTTP_COOKIE" ]; then
                ERROR_MSG "Du er ikke logget inn!"
            else

                # Fjerner 'session=' fra cookie og stopper ved første ';'
                session_cookie=$(echo "$HTTP_COOKIE" | sed 's/session=\([^;]*\).*/\1/')

                # Sjekker om session-cookie er gyldig
                if ! echo "SELECT * FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $DATABASE | grep -qE '^' ; then
                    ERROR_MSG "Session-cookie er ikke gyldig!"
                fi

                # Sletter cookie fra databasen
                echo "DELETE FROM Sesjon WHERE SesjonsID = '$session_cookie';" | sqlite3 $DATABASE

                # -- RESPONSE -- #
                # Header
                echo "Set-Cookie:"
                WRITE_HEADER

                # Body
                STD_MSG "Du er nå logget ut!"
            fi
        ;;
        *)
            ERROR_MSG "Ugyldig forespørsel til Sesjons-tabelle!"
        ;;
    esac

else
    ERROR_MSG "Tabellen finnes ikke!"
fi

