FROM haproxy:1.7
COPY haproxy.cfg server.pem server.key ca.pem /usr/local/etc/haproxy/
RUN cat /usr/local/etc/haproxy/server.pem /usr/local/etc/haproxy/server.key \
    > /usr/local/etc/haproxy/server.combined.pem
