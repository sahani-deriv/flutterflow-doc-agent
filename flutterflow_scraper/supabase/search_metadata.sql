-- Enable the pg_trgm extension for text similarity search
create extension if not exists pg_trgm;

-- Create a function to search document metadata (titles and summaries)
create or replace function search_doc_metadata(query_text text, match_limit int default 3)
returns table (
    id bigint,
    title text,
    url text,
    summary text,
    similarity real
)
language plpgsql
as $$
begin
    return query
    select 
        d.id,
        coalesce(d.metadata->>'title', 'Untitled') as title,
        coalesce(
            d.metadata->>'url',
            d.metadata->>'source',
            d.metadata->>'link',
            d.metadata->>'href',
            'https://docs.flutterflow.io'
        ) as url,
        coalesce(d.metadata->>'summary', d.metadata->>'description', substring(d.content for 200) || '...') as summary,
        similarity(
            lower(d.metadata->>'title') || ' ' || 
            coalesce(lower(d.metadata->>'summary'), ''),
            lower(query_text)
        ) as similarity
    from documents d
    where 
        d.metadata->>'title' is not null
    order by similarity desc
    limit match_limit;
end;
$$;
