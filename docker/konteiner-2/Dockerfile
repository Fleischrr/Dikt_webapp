FROM dikt-image

RUN apk add sqlite \
    && apk add jq \
    && apk add libxml2-utils 

# Kopierer cgi-bin til container cgi-bin og gjør dikt_db.cgi kjørbar
COPY cgi-bin/ /usr/local/apache2/cgi-bin/
RUN chmod +x /usr/local/apache2/cgi-bin/dikt_db.cgi

# Kopierer over vhost config til container
COPY backend.conf /usr/local/apache2/conf/extra/custom-vhost.conf

# Gir apache eierskap til cgi-bin
RUN chown -R www-data:www-data /usr/local/apache2/cgi-bin/

# Aktiverer cgi og inkluderer vhost config
RUN echo "Include conf/extra/custom-vhost.conf" >> /usr/local/apache2/conf/httpd.conf
