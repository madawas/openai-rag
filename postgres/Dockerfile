FROM pgvector/pgvector:pg16

COPY scripts/extension.sql /docker-entrypoint-initdb.d/
COPY scripts/init.sql /docker-entrypoint-initdb.d/

RUN addgroup --gid 10016 vdbgroup && \
    adduser --system --home /home/vdbuser --uid 10020 --ingroup vdbgroup vdbuser

RUN mkdir -p /home/vdbuser/postgresql/data

ENV PGDATA=/home/vdbuser/postgresql/data

RUN chown -R 10020:10016 /home/vdbuser && \
    chmod 755 /home/vdbuser/postgresql/data && \
    chown -R 10020:10016 /var/run/postgresql

USER 10020

EXPOSE 5432
