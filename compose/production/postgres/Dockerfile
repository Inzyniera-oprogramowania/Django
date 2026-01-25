FROM postgis/postgis:15-3.3

COPY ./compose/production/postgres/maintenance /usr/local/bin
RUN apt-get update \
    && apt-get install -y postgresql-15-postgis-3 postgresql-15-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*
RUN chmod +x /usr/local/bin/backup /usr/local/bin/restore /usr/local/bin/backups /usr/local/bin/rmbackup
