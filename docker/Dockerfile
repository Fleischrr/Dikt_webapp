FROM httpd:alpine

# Installere sqlite3, jq og xmllint etc.
RUN apk update \
    && apk add nano

# Sletter default innhold i htdocs og cgi-bin
RUN rm -rf /usr/local/apache2/htdocs/* /usr/local/apache2/cgi-bin/* /usr/local/apache2/conf/extra/*

# Aktiverer cgi og inkluderer vhost config
RUN echo "LoadModule cgi_module modules/mod_cgi.so" >> /usr/local/apache2/conf/httpd.conf