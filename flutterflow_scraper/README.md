# FlutterFlow Documentation Assistant

An intelligent assistant that helps users find information about FlutterFlow by combining official documentation and community insights.

## Features

- **Smart Documentation Search**
  - Searches through titles and summaries to find relevant sections
  - Uses found titles to enhance content search
  - Provides both overview and detailed information
  - Automatically falls back to different URL fields

- **Community Integration**
  - Searches FlutterFlow community discussions
  - Provides real-world examples and user experiences
  - Links directly to relevant community threads

- **Clean Chat Interface**
  - Modern chat-like UI with Streamlit
  - Clear distinction between user and assistant messages
  - Easy access to source links
  - Chat history with newest messages first

## Setup

### Prerequisites

- Python 3.8+
- Supabase account with a project
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd flutterflow-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_api_key
   ```

### Supabase Setup

1. Create a new Supabase project

2. Enable the pg_trgm extension:
   - Go to SQL Editor in your Supabase dashboard
   - Run the contents of `supabase/search_metadata.sql`

3. Create the documents table:
   - Run the contents of `supabase/init.sql`

## Usage

1. Start the application:
   ```bash
   cd flutterflow_scraper
   streamlit run src/app.py
   ```

2. Open your browser and navigate to `http://localhost:8501`

3. Start asking questions about FlutterFlow!

## Architecture

### Components

1. **FlutterFlowAgent** (`src/agent.py`)
   - Main agent class that coordinates all components
   - Handles conversation memory and tool selection
   - Uses LangChain for agent orchestration

2. **Documentation Tools** (`src/tools.py`)
   - Enhanced documentation search combining metadata and content
   - Community search for user discussions
   - URL fallback system for reliable source linking

3. **Streamlit UI** (`src/app.py`)
   - Chat interface with message history
   - Clear visual distinction between sources
   - Real-time response streaming

4. **Supabase Integration**
   - Vector store for documentation
   - Metadata search with similarity matching
   - Efficient content retrieval

### Search Process

1. When a question is asked:
   - First searches documentation metadata (titles and summaries)
   - Uses found titles to enhance content search
   - Searches community discussions if needed

2. Results are combined into a comprehensive answer:
   - Overview from metadata search
   - Detailed information from content search
   - Supplementary insights from community (if relevant)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
