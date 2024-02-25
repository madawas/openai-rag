FROM pgvector/pgvector:pg16

COPY scripts/extension.sql /docker-entrypoint-initdb.d/
COPY scripts/init.sql /docker-entrypoint-initdb.d/

RUN addgroup --gid 10016 vdbgroup && \
    adduser --system --home /home/vdbuser --uid 10020 --ingroup vdbgroup vdbuser

RUN chown -R 10020:10016 /var/lib/postgresql/data && \
    chmod 755 /var/lib/postgresql/data && \
    chown -R 10020:10016 /var/run/postgresql

USER 10020

EXPOSE 5432
