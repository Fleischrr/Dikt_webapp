FROM dikt-image

RUN apk add curl

# Kopierer cgi-bin til container og gjør de kjørbare
COPY cgi-bin/ /usr/local/apache2/cgi-bin/
RUN chmod +x /usr/local/apache2/cgi-bin/*.cgi

# Kopierer over vhost config til container
COPY frontend.conf /usr/local/apache2/conf/extra/custom-vhost.conf

# Gir apache eierskap til cgi-bin 
RUN chown -R www-data:www-data /usr/local/apache2/cgi-bin/

# Inkluderer vhost config
RUN echo "Include conf/extra/custom-vhost.conf" >> /usr/local/apache2/conf/httpd.conf
