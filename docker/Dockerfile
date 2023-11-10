# Use an appropriate base image that supports Bash CGI and SQLite
FROM httpd:alpine

# Installere sqlite3 og bash
RUN apk update \
    && apk add sqlite \
    && apk add jq \ 
    && apk add libxml2-utils

# Kopierer cgi-bin til container cgi-bin
COPY cgi-bin/ /usr/local/apache2/cgi-bin/

# Gjør db_api.cgi kjørbar
RUN chmod +x /usr/local/apache2/cgi-bin/db_api.cgi

# Kopierer over vhost config til container
COPY cgi-server.conf /usr/local/apache2/conf/extra/custom-vhost.conf

# Aktiverer cgi og inkluderer vhost config
RUN echo "LoadModule cgi_module modules/mod_cgi.so" >> /usr/local/apache2/conf/httpd.conf
RUN echo "Include conf/extra/custom-vhost.conf" >> /usr/local/apache2/conf/httpd.conf
