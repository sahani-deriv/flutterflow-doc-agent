import os
from typing import Optional
from langchain.tools import Tool
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_openai import ChatOpenAI

def create_tools(vector_store: SupabaseVectorStore, supabase_client, openai_api_key: Optional[str] = None) -> list:
    """Create and return a list of tools for the agent"""
    
    # Content Search Tool (RAG)
    def search_documentation(query: str, metadata_context: str = "") -> str:
        """Search FlutterFlow documentation content for relevant information"""
        try:
            # If we have metadata context, combine it with the query
            search_query = query
            if metadata_context:
                search_query = f"{query} {metadata_context}"
            
            docs = vector_store.similarity_search(search_query, k=3)
            if not docs:
                return "No relevant documentation found."
            
            # Format results
            formatted_results = []
            for idx, doc in enumerate(docs, 1):
                formatted_results.append(
                    f"Documentation {idx}:\n"
                    f"Title: {doc.metadata.get('title', 'Untitled') if doc.metadata else 'Untitled'}\n"
                    f"URL: {doc.metadata.get('url', doc.metadata.get('source', doc.metadata.get('link', doc.metadata.get('href', 'https://docs.flutterflow.io')))) if doc.metadata else 'https://docs.flutterflow.io'}\n"
                    f"Content: {doc.page_content if hasattr(doc, 'page_content') else doc.content}\n"
                )
            
            return "\n\n".join(formatted_results)
        
        except Exception as e:
            return f"Error searching documentation: {str(e)}"
    
    # Metadata Search Tool
    def search_by_metadata(query: str) -> tuple[str, str]:
        """Search FlutterFlow documentation by titles and summaries"""
        try:
            # Execute raw SQL query to search titles and summaries
            result = supabase_client.rpc(
                'search_doc_metadata',
                {
                    'query_text': query,
                    'match_limit': 3
                }
            ).execute()
            
            if not result.data:
                return "No relevant documentation found in titles or summaries."
            
            # Format results
            formatted_results = []
            for idx, doc in enumerate(result.data, 1):
                formatted_results.append(
                    f"Documentation {idx}:\n"
                    f"Title: {doc.get('title', 'Untitled')}\n"
                    f"URL: {doc.get('url', 'No URL available')}\n"
                    f"Summary: {doc.get('summary', 'No summary available')}\n"
                )
            
            # Extract titles for context
            titles_context = " ".join([doc.get('title', '') for doc in result.data if doc.get('title')])
            
            return "\n\n".join(formatted_results), titles_context
            
        except Exception as e:
            return f"Error searching metadata: {str(e)}"
    
    # Wrapper function to combine metadata and content search
    def enhanced_documentation_search(query: str) -> str:
        """Search FlutterFlow documentation using both metadata and content"""
        try:
            # First search metadata
            metadata_results, titles_context = search_by_metadata(query)
            if not metadata_results:
                return "No relevant documentation found."
            
            # Then search content with metadata context
            content_results = search_documentation(query, titles_context)
            
            return f"Overview from Documentation:\n{metadata_results}\n\nDetailed Information:\n{content_results}"
            
        except Exception as e:
            return f"Error searching documentation: {str(e)}"
    
    # Initialize OpenAI components if API key is provided
    if not openai_api_key:
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OpenAI API key is required")
        
    # Create documentation search tool
    documentation_tool = Tool(
        name="search_documentation",
        description="Search the FlutterFlow documentation comprehensively, including titles, summaries, and detailed content.",
        func=enhanced_documentation_search
    )
    
    return [documentation_tool]
