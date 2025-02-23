-- Enable the pgvector extension to work with embedding vectors
create extension vector;

-- Create a table for storing documents with embeddings
create table documents (
    id bigint primary key generated always as identity,
    url text not null,
    title text,
    summary text,
    content text,
    metadata jsonb,
    embedding vector(1536),  -- OpenAI embeddings are 1536 dimensions
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create a function to search documents by similarity
-- Function that accepts a single query_embedding parameter
create or replace function match_documents (
  query_embedding vector(1536)
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from documents
  where 1 - (embedding <=> query_embedding) > 0.7
  order by similarity desc
  limit 3;
$$;

-- Function that accepts a single JSON parameter (alternative method)
create or replace function match_documents_json(
  query_json json
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> (query_json->>'query_embedding')::vector) as similarity
  from documents
  where 1 - (embedding <=> (query_json->>'query_embedding')::vector) > 0.7
  order by similarity desc
  limit 3;
$$;
