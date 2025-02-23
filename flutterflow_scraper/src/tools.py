import requests
from bs4 import BeautifulSoup
from typing import Optional
from langchain.tools import Tool
from langchain_community.vectorstores.supabase import SupabaseVectorStore

def search_community(query: str) -> str:
    """Search FlutterFlow community for relevant discussions"""
    try:
        # Format query for URL
        formatted_query = query.replace(' ', '+')
        url = f"https://community.flutterflow.io/search?q={formatted_query}"
        
        # Send request with desktop user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find search results
        results = []
        for post in soup.find_all('div', class_='topic-list-item'):
            try:
                title_elem = post.find('a', class_='title')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                link = f"https://community.flutterflow.io{title_elem['href']}"
                
                # Get post content
                post_response = requests.get(link, headers=headers)
                post_response.raise_for_status()
                post_soup = BeautifulSoup(post_response.text, 'html.parser')
                
                # Find the first post content
                content_elem = post_soup.find('div', class_='post')
                if not content_elem:
                    continue
                    
                content = content_elem.get_text(strip=True)
                
                results.append({
                    'title': title,
                    'link': link,
                    'content': content[:500] + '...' if len(content) > 500 else content
                })
                
                if len(results) >= 3:  # Limit to top 3 results
                    break
                    
            except Exception as e:
                print(f"Error processing post: {str(e)}")
                continue
        
        if not results:
            return "No relevant community discussions found."
        
        # Format results
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append(
                f"Result {idx}:\n"
                f"Title: {result['title']}\n"
                f"Link: {result['link']}\n"
                f"Content: {result['content']}\n"
            )
        
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching community: {str(e)}"

def create_tools(vector_store: SupabaseVectorStore, supabase_client) -> list:
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
    
    # Create tools
    documentation_tool = Tool(
        name="search_documentation",
        description="Search the FlutterFlow documentation comprehensively, including titles, summaries, and detailed content. Use this first for authoritative information.",
        func=enhanced_documentation_search
    )
    
    community_tool = Tool(
        name="search_community",
        description="Search the FlutterFlow community forums for discussions, solutions, and user experiences. Use this after checking the official documentation.",
        func=search_community
    )
    
    return [documentation_tool, community_tool]
