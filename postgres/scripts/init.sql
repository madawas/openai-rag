create table documents (
    id uuid default uuid_generate_v4(),
    file_name varchar(200) unique not null,
    process_status varchar(20) not null,
    process_description varchar(150),
    collection_name varchar(100),
    summary varchar(1000),
    vectors varchar(36)[],
    constraint documents_pkey primary key (id)
);
create table langchain_pg_collection (
    name varchar null,
    cmetadata json null,
    uuid uuid not null,
    constraint langchain_pg_collection_pkey primary key (uuid)
);
create table langchain_pg_embedding (
    collection_id uuid null,
    embedding public.vector null,
    document varchar null,
    cmetadata json null,
    custom_id varchar null,
    uuid uuid not null,
    constraint langchain_pg_embedding_pkey primary key (uuid),
    constraint langchain_pg_embedding_collection_id_fkey foreign key (collection_id)
        references langchain_pg_collection(uuid) on delete cascade
);
