FROM pgvector/pgvector:pg16

COPY scripts/extension.sql /docker-entrypoint-initdb.d/
COPY scripts/init.sql /docker-entrypoint-initdb.d/

RUN addgroup --gid 10016 vdbgroup && \
    adduser --system --no-create-home --uid 10020 --ingroup vdbgroup vdbuser

# Set ownership and permissions on data directory
RUN chown -R 10020:10016 /var/lib/postgresql/data && \
    chmod 755 /var/lib/postgresql/data

USER 10020

EXPOSE 5432
