#define _GNU_SOURCE
#include <arpa/inet.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <sched.h>

#define BACK_LOG 10
#define REQUEST_SIZ 100 

void log_controller();
void mode_handler();
void mime_types_linked_list();
void disassosiate();
void bad_request();
void bad_permission(char *requested_file);
void not_found(char *requested_file);
void request_handler(int new_sd);
void response_handler(int new_sd, char *requested_file, char *requested_filetype);
char *concat_file_and_type(char *filepath, char *filetype);
char *mime_types_check(char *filetpye);

int LOCAL_PORT = 8000;
char *TARGET_DIR = "/var/www";
char *LOG_FILE = "/var/log/web_tjener.log";
int log_fd;
int is_daemon = 0;

/**
 * Struktur for å lagre filendelser og mime-typer i en lenket liste.
 * 
 * @param end Filendelsen
 * @param type Mime-typen
 * @param next Peker til neste node (struct mime_end_and_type)
 */
struct mime_end_and_type {
    char *end;
    char *type;
    struct mime_end_and_type *next; 
};

struct mime_end_and_type *ll_head;


int main()
{
    struct sockaddr_in loc_addr;
    int sd, request_sd;
    int request_len;
    char request_buffer[REQUEST_SIZ];
    char response_buffer[BUFSIZ];
    ll_head = malloc(sizeof(struct mime_end_and_type));

    // Setter modus og initialiserer logging
    mode_handler();
    log_controller();

    // Forhindrer zombie prosesser
    struct sigaction sigchld_action = {
        
        // Setter default signal til å ha flagg som reaper child prosesser
        .sa_handler = SIG_DFL,
        .sa_flags = SA_NOCLDWAIT
    };
    
    sigaction(SIGCHLD, &sigchld_action, NULL);

    // Redirigerer stderr til log-discriptoren
    if (dup2(log_fd, 2) < 0)
    {
        perror("dup2");
        exit(1);
    }

    fprintf(stderr, "Starter tjener med PID: %d\n", getpid());

    // Setter opp socket-strukturen.
    if ( (sd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0 )
    {
        perror("socket");
        exit(1);
    }

    // Aktiverer SO_REUSEADDR for å tillate gjenbruk av socket ved omstart av tjener
    if (setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) < 0)
    {
        perror("setsockopt");
        exit(1);
    }

    // Initierer lokal adresse (BE 16/32-bit)
    loc_addr.sin_family = AF_INET;
    loc_addr.sin_port = htons((__u_short)LOCAL_PORT);
    loc_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    // Kobler sammen socket med strukturen deklarert ovenfor
    if (bind(sd, (struct sockaddr *)&loc_addr, sizeof(loc_addr)) < 0)
    {
        perror("bind");
        exit(1);
    }

    // Gjør socket passiv, aksepterer forespørsler og setter opp en kø
    if (listen(sd, BACK_LOG) < 0)
    {
        perror("listen");
        exit(1);
    }

    fprintf(stderr, "PID: %d\tKnyttet til port %d.\n", getpid(), LOCAL_PORT);

    if (!is_daemon) 
    {
        // Hvis ikke daemon, kopierer mime.types inn til en linked-list  
        fprintf(stderr, "PID: %d\tIkke en daemon, kopierer mime.tpyes...\n", getpid());
        mime_types_linked_list();
        fprintf(stderr, "PID: %d\tmime.types kopiert\n", getpid());
    } 

    // Endrer arbeidskatalog og Demoniserer web-tjeneren
    disassosiate();
    
    fprintf(stderr, "PID: %d\tOppsett fullført. Avventer forespørsel...\n\n", getpid());

    while (1)
    {
        // Aksepterer mottatt forespørsel på socket og lagrer descriptor
        request_sd = accept(sd, NULL, NULL);
        
        if (request_sd < 0)
        {
            perror("accept");
            exit(1);
        }

        // Re-diriger stdout til socket 
        if (dup2(request_sd, 1) < 0)
        {
            perror("dup2");
            exit(1);
        }

        fprintf(stderr, "PID: %d\tForespørsel mottatt. Forker prosess...\n", getpid());

        if (0 != fork())
        {
            // Lukker socket i foreldre-prosessen
            close(request_sd);
        }
        else
        {
            fprintf(stderr, "Fork PID: %d\n%d: Starter request handler...\n---Request---\n", getpid(), getpid());
            
            // Håndterer forespørsel
            request_handler(request_sd);

            // Stenger read/write endene av socket
            fprintf(stderr, "%d: Stenger socket og avslutter fork\n", getpid());
            shutdown(request_sd, SHUT_RDWR);
            exit(0);
        }

    }

    close(log_fd);
    return 0;
}



/**
 * Håndterer lesing av en forespørsel fra en klient.
 * Starter også respons-håndteringen på slutten.
 *
 * @param request_sd Socket-deskriptor for klientforespørselen.
 */
void request_handler(int request_sd)
{
    char *pointer;
    char *request;
    char *method;
    char *filepath;
    char *filetype;

    int request_len;
    char request_string[REQUEST_SIZ];
    char requested_file[257];

    // Leser inn forespørsel fra socket og skriver forespørsel til log-fil
    request_len = read(request_sd, request_string, REQUEST_SIZ);
    write(log_fd, request_string, request_len);
    
    if (request_len <= 0)
    {
        bad_request();
    } 
    else 
    {
        // Setter pointer til starten av forespørselen
        pointer = request_string;

        // Henter forespørselen og lagrer i request_string
        request = malloc(strlen(request_string)+sizeof('\0'));
        strcpy(request, request_string);

        // Peker pointer til første whitespace, altså på slutten av http metoden
        pointer = strtok(request, " ");

        // Lagrer http metode
        method = malloc(strlen(pointer)+sizeof('\0'));
        strcpy(method, pointer);
        fprintf(stderr, "\n\n%d: HTTP Method: %s\n", getpid(), method);

        // Peker til neste whitespace, altså på starten av http filsti
        pointer = strtok(NULL, " ");

        // Lagrer http filsti
        filepath=malloc(strlen(pointer)+sizeof('\0'));
        strcpy(filepath, pointer);

        // Sjekker filsti og henter ut filtype
        if (strcmp(filepath, "/") == 0 || strlen(filepath) < 1)
        {
            // Hvis filsti er default, eller om den er tom, setter til index.html
            strcpy(filepath, "index"); 

            filetype=malloc(strlen("html")+sizeof('\0'));
            strcpy(filetype, "html");
        } 
        else if (strchr(filepath, '.') != NULL) 
        {
            // Hvis filsti inneholder punktum. Itererer over filstien til siste punktum, for å peke til filtype
            strtok(filepath, ".");
            pointer = strtok(NULL, ".");
                        
            // Lagrer filtype
            filetype=malloc(strlen(pointer)+sizeof('\0'));
            strcpy(filetype, pointer);
        } 
        else 
        {
            bad_request();
        }

        fprintf(stderr, "%d: HTTP Filepath: %s og Filetype: %s\n", getpid(), filepath, filetype);

        if (strcmp(method, "GET") != 0)
        {
            // Send feilmelding hvis metoden ikke er GET
            fprintf(stderr, "\n\n%d: Ugyldig metode mottatt: %s\n", getpid(), method);
            bad_request();
        } 
        else 
        {
            // Starter respons håndtering hvis metoden er GET
            fprintf(stderr, "\n\n%d: Gyldig forespørsel mottatt, etterspurt fil: %s\n", getpid(), filepath);
            response_handler(request_sd, filepath, filetype);
        }

    }

}



/**
 * Håndterer responsen til en klient for en HTTP-forespørsel.
 * 
 * @param response_sd Den tilkoblede socketen for responsen.
 * @param requested_filepath Stien til den forespurte filen.
 * @param requested_filetype Filtypen til den forespurte filen.
 */
void response_handler(int response_sd, char *requested_filepath, char *requested_filetype)
{
    char *file;
    char *content_type;
    int bytes_file, response_fd;
    char response_buffer[10000];

    // Slår sammen filsti og filtype til en string
    file = concat_file_and_type(requested_filepath, requested_filetype);
    
    if (strcmp(requested_filetype , "asis") == 0)
    {   
        fprintf(stderr, "%d: Filtype er asis, setter content-type til asis\n", getpid());

        // Hvis filtype er asis, setter content-type til asis
        content_type = malloc(strlen("asis")+sizeof('\0'));
        strcpy(content_type, "asis");
    } 
    else if (strcmp(requested_filetype , "xsd") == 0)
    {   
        fprintf(stderr, "%d: Filtype er xsd, setter content-type til text/xml\n", getpid());

        // Hvis filtype er xsd, setter content-type til text/xml
        content_type = malloc(strlen("text/xml")+sizeof('\0'));
        strcpy(content_type, "text/xml");
    }  
    else if (!is_daemon)      
    {
        fprintf(stderr, "%d: Forespurt filtype er ikke asis, sjekker om filtype er i mime.tpyes\n", getpid());

        // Hvis ikke daemon, sjekker om filtype er i mime.types
        content_type = mime_types_check(requested_filetype);
    }
    else 
    {
        not_found(file);    
    }

    fprintf(stderr, "%d: Forespurt filtype: %s, content-type: %s\n", getpid(), requested_filetype, content_type);

    
    if ( strlen(content_type) < 1 )
    {
        // Hvis content-type er tom, send feilmelding
        bad_request();
    } 
    else 
    {
        // Håndter fil og respons
                
        fprintf(stderr, "%d: Forespurt fil: %s\n", getpid(), file);
        
        if ((response_fd = open(file, O_RDONLY)) == -1)
        {
            // Hvis åpning av fil feiler, sjekk error type
            if (errno == EACCES)
            {
                // Ikke tilgang til fil
                bad_permission(file);
            }
            else
            {
                // Filen finnes ikke
                not_found(file);
            }

        }
        else
        {
            // Filen finnes, leser og sender respons

            fprintf(stderr, "%d: Filen %s finnes, sender den\n", getpid(), file);
                        
            while ((bytes_file = read(response_fd, response_buffer, sizeof(response_buffer))) > 0)
            {
                if ( ! strcmp(content_type, "asis") == 0) {
                    
                    // Skriv header hvis filtype ikke er asis   
                    printf("HTTP/1.1 200 OK\r\n"
                            "Content-Length: %d\r\n"
                            "Content-Type: %s\r\n"
                            "Access-Control-Allow-Origin: *\r\n"
                            "\r\n", bytes_file, content_type);
                    
                    fflush(stdout);
                }

                // Skriver filen til socket
                write(response_sd, response_buffer, bytes_file);
            }

        }

    }

}


/**
 * Sjekker om filtypen er støttet i mime-types.
 * Benytter linked-list for å sjekke om filtypen er støttet.
 * 
 * @param filetype Filtypen som skal sjekkes.
 * @return Mime-typen som er assosiert med filtypen hvis den er støttet, ellers en tom streng.
 */
char *mime_types_check(char *filetype) 
{
    struct mime_end_and_type *ll_current;
    ll_current = ll_head;
    
    fprintf(stderr, "Sjekker om filtype %s er støttet i mime-types\n", filetype);

    // Itererer over linked-listen og sjekker om filtypen matcher en av filendelsene
    while (ll_current != NULL) 
    {
        if (strcmp(ll_current->end, filetype) == 0) 
        {
            fprintf(stderr, "Filtype %s er støttet\n", filetype);
            return ll_current->type;
        }

        ll_current = ll_current->next;
    }

    fprintf(stderr, "Filtype %s er ikke støttet\n", filetype);

    return "";
}



/**
 * Funksjon for å opprette en lenket liste av mime-typer fra filen mime.types.
 * Benytter global variabel ll_head for å lagre peker til første node.
 * 
 * @param None
 * @return None
 */
void mime_types_linked_list() 
{
    // Variabler
    char    *buffer = NULL;
    char    *file_end = NULL;
    char    *mime_type = NULL;

    size_t  buff_size = 0;
    int     read_ant = 0;
    int     type_len = 0;

    // Pekere for linked-list
    struct mime_end_and_type *ll_current = ll_head;
    struct mime_end_and_type *ll_end = NULL;

    // Åpner mime.types
    FILE *mime_types_file = fopen("/etc/mime.types", "r");
    if ( mime_types_file == NULL )
    {
        perror("fopen");
        exit(1);
    }

    fprintf(stderr, "Åpnet mime.types\n");

    while ( 0 < ( read_ant = getline( &buffer, &buff_size, mime_types_file) ) ) 
    {
        // Hopper over kommentarer og liner med mindre enn 2 tegn
        if ( buffer[0] == '#') { continue; }   
        if ( read_ant < 2 ) { continue; }
        
        // Fjerner newline
        buffer[read_ant-1] = '\0';

        // Henter ut mime-typen
        mime_type = strtok(buffer, "\t ");
        type_len = strlen(mime_type);

        // Henter ut filendelser
        while ( 0 != (file_end = strtok(NULL, "\t ") ) )
        {
            // Legger til filendelsen i linked-listen
            ll_current->end = malloc(strlen(file_end)+sizeof('\0'));
            strcpy(ll_current->end, file_end);

            // Legger til mime-typen i linked-listen
            ll_current->type = malloc( type_len + sizeof('\0') );
            strcpy(ll_current->type, mime_type);

            // Setter peker som neste node, samt ende-pekeren lik pekeren
            ll_current->next = malloc(sizeof(struct mime_end_and_type));
            ll_end = ll_current;
            ll_current = ll_current->next;
        }

    }

    fprintf(stderr, "Mime-types er lest inn i linked listen\n");

    // Lukker filen og frigjør buffer
    fclose(mime_types_file);
    free(buffer);

    fprintf(stderr, "mime.types filen lukket\n");

    // Avslutter linked-listen og frigjør pekeren
    ll_end->next = NULL;
    free(ll_current);

}


/**
 * Disassosierer prosessen fra sin opprinnelige rotkatalog og arbeidskatalog.
 * 
 * Hvis prosessen kjører som en daemon, demoniserer den prosessen og begrenser privilegiene.
 */
void disassosiate()
{
    fprintf(stderr, "Endrer root og arbeidsdir\n");

    // Setter arbeidskatalogen til root-katalogen
    if (chdir(TARGET_DIR) != 0)
    {
        perror("chdir");
        exit(1);
    }

    // Setter root-katalogen til /var/www/
    if (chroot(TARGET_DIR) != 0)
    {
        perror("chroot");
        exit(1);
    }

    // Hvis daemon, demoniserer prosessen
    if (is_daemon) {

        fprintf(stderr, "Demoniserer\n");

        // Legger prosessen i bakgrunnen og ikke prosessgruppe leder
        if (0 != fork()) 
        {
            exit(0);
        }

        // Lager ny session som prosessen er leder av. Frigjør fra kontrollterminal.
        if (setsid() < 0)
        {
            perror("setsid");
            exit(1);

        }

        // Ignorerer SIGCHLD for å unngå zombie prosesser
        signal(SIGCHLD, SIG_IGN);

        // Ignorerer SIGHUP for å unngå å bli lukket når kontrollterminalen avsluttes.
        signal(SIGHUP, SIG_IGN);

        // Setter uid til en ikke-privilegert bruker.
        if (seteuid(1000) < 0)
        {
            perror("seteuid");
            exit(1);
        }

        // Forker igjen for å hindre sesjonsleder og tilknytting til en ledig kontrollterminal
        if (0 != fork()) 
        {
            exit(0);
        }

    }

}

/**
 * Funksjonen concat_file_and_type tar inn en filbane og en filtype og returnerer en ny streng som er en kombinasjon av filbanen og filtypen.
 *
 * @param filepath Filbanen som skal kombineres.
 * @param filetype Filtypen som skal kombineres.
 * @return En ny streng som er en kombinasjon av filbanen og filtypen, separert med et punktum.
 */
char *concat_file_and_type(char *filepath, char *filetype) 
{
    char *file;

    file=malloc( strlen(filepath) + strlen(filepath) + sizeof('\0') );
    strcpy(file, filepath);
    strcat(file, ".");
    strcat(file, filetype);

    return file;
}


/**
 * Funksjon for å håndtere en ugyldig forespørsel.
 * Skriver ut en feilmelding til stderr og sender en HTTP 400 Bad Request respons til klienten.
 */
void bad_request()
{
    fprintf(stderr, "%d: (400) Ugyldig filtype eller forespørsel mottatt\n", getpid());

    printf("HTTP/1.1 400 Bad Request\r\n"
           "Content-Length: 57\r\n"
           "Content-Type: text/plain\r\n"
           "\r\n"
           "Bad Request: Invalid request or unsupported file type\r\n\r\n");

    // Flusher stdout for å unngå at data blir liggende i bufferen
    fflush(stdout);
}


/**
 * Funksjonen for å håndtere en fil som ikke finnes.
 * Skriver ut en feilmelding til stderr og sender en HTTP 404 Not Found respons til klienten.
 *
 * @param requested_file Forespurte filen
 */
void not_found(char *requested_file)
{
    fprintf(stderr, "%d: (404) Filen %s finnes ikke\n", getpid(), requested_file);

    printf("HTTP/1.1 404 Not Found\r\n"
           "Content-Length: 18\r\n"
           "Content-Type: text/plain\r\n"
           "\r\n"
           "File not found\r\n\r\n");

    // Flusher stdout for å unngå at data blir liggende i bufferen
    fflush(stdout);
}

/**
 * Funksjon for å håndtere en fil som ikke kan åpnes.
 * Skriver ut en feilmelding til stderr og sender en HTTP 403 Forbidden respons til klienten.
 * 
 * @param requested_file Den forespurte filen som ikke kan åpnes.
 */
void bad_permission(char *requested_file)
{
    fprintf(stderr, "%d: (403) Forespurt fil %s kan ikke åpnes\n", getpid(), requested_file);
    
    printf("HTTP/1.1 403 Forbidden\r\n"
            "Content-Length: 18\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "Forbidden access\r\n\r\n");

    // Flusher stdout for å unngå at data blir liggende i bufferen
    fflush(stdout);
}

/**
 * Funksjonen log_controller() åpner en loggfil for skriving. Hvis filen ikke eksisterer, blir den opprettet.
 * Benytter globale variabler, log_fd og LOG_FILE, for å lagre deskriptoren og filbanen.
 */
void log_controller()
{
    log_fd = open(LOG_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (log_fd == -1)
    {
        perror("open log file");
        exit(1);
    }
}

/**
 * Håndterer modusen til tjeneren.
 * Sjekker om parent pid er 1 (konteiner), hvis ikke er tjeneren en daemon.
 */
void mode_handler() 
{
    if (getppid() != 1)
    {
        is_daemon = 1;
        TARGET_DIR = "/opt/Dikt_webapp/var/www";
        LOG_FILE = "/opt/Dikt_webapp/var/log/web_tjener.log";
        LOCAL_PORT = 8000;
    }
}
