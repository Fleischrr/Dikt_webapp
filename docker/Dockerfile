FROM httpd:alpine

# Oppdatere pakkeliste og oppgraderer alle pakker
RUN apk update \
    && apk upgrade 

# Sletter default innhold i htdocs og cgi-bin
RUN rm -rf /usr/local/apache2/htdocs/* /usr/local/apache2/cgi-bin/* /usr/local/apache2/conf/extra/*

# Aktiverer cgi og inkluderer vhost config
RUN echo "LoadModule cgi_module modules/mod_cgi.so" >> /usr/local/apache2/conf/httpd.conf