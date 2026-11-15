FROM mysql:8.4
# strip Windows line endings so the init script always runs, whatever the checkout settings were
COPY init/ /docker-entrypoint-initdb.d/
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/*.sh && chmod 644 /docker-entrypoint-initdb.d/*.sh
