import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from supabase import create_client, Client
from tools import create_tools

class FlutterFlowAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Initialize OpenAI with custom base URL
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            api_key=openai_api_key,
            base_url="https://litellm.deriv.ai/v1",
            model="text-embedding-3-small"
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            base_url="https://litellm.deriv.ai/v1",
            model="gpt-4o",
            temperature=0.3
        )
        
        # Initialize vector store
        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name="documents",
            query_name="match_documents",
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create tools
        self.tools = create_tools(self.vector_store, self.supabase)
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful FlutterFlow expert assistant that helps users with their FlutterFlow questions and issues.
            
            IMPORTANT: Use the search_documentation tool to find comprehensive information from the official documentation:
            - This will search both metadata (titles and summaries) and detailed content
            - Pay attention to both the overview and detailed sections in the results
            
            When answering:
            1. Structure your response clearly:
               - Start with a high-level overview from documentation
               - Follow with detailed technical information
               - Always include relevant documentation URLs
               - Use code examples when available
            
            2. Make information actionable:
               - Break down complex topics into steps
               - Highlight important considerations
               - Explain any prerequisites
            
            If you don't find relevant information:
            1. Clearly state that no relevant documentation was found
            2. Suggest rephrasing the question
            3. Direct the user to the FlutterFlow documentation: https://docs.flutterflow.io
            
            Remember: Focus on providing accurate, well-structured information from the official documentation."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("system", "{agent_scratchpad}"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )

    async def query(self, question: str) -> dict:
        """
        Query FlutterFlow documentation with a question
        
        Args:
            question: The question to ask about FlutterFlow
            
        Returns:
            dict: Contains the answer with relevant documentation information
        """
        try:
            # Get response from agent
            response = await self.agent_executor.ainvoke({"input": question})
            
            # Extract any source information from the response
            # The agent's response might include source information in a structured way
            return {
                "answer": response["output"],
                "sources": []  # Sources are now included in the answer text
            }
            
        except Exception as e:
            print(f"Error querying agent: {str(e)}")
            return {
                "error": str(e),
                "answer": "I encountered an error while trying to answer your question.",
                "sources": []
            }

    def clear_memory(self):
        """Clear the conversation memory"""
        self.memory.clear()

async def main():
    # Example usage
    agent = FlutterFlowAgent()
    
    # Example question
    question = "How do I set up FlutterFlow?"
    response = await agent.query(question)
    
    print("\nQuestion:", question)
    print("\nAnswer:", response["answer"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
