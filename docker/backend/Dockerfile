FROM dikt-image

# Kopierer cgi-bin til container cgi-bin og gjør db_api.cgi kjørbar
COPY cgi-bin/ /usr/local/apache2/cgi-bin/
RUN chmod +x /usr/local/apache2/cgi-bin/db_api.cgi

# Kopierer over vhost config til container
COPY cgi-server.conf /usr/local/apache2/conf/extra/custom-vhost.conf

# Gir apache eierskap til cgi-bin
RUN chown -R www-data:www-data /usr/local/apache2/cgi-bin/

# Aktiverer cgi og inkluderer vhost config
RUN echo "Include conf/extra/custom-vhost.conf" >> /usr/local/apache2/conf/httpd.conf
