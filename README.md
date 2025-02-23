# FlutterFlow Documentation Agent

This repository contains a Python-based agent for scraping and processing FlutterFlow documentation, combining official documentation with community insights to provide intelligent assistance.

## Project Structure

```
.
├── flutterflow_scraper/    # Main scraper module
│   ├── src/               # Source code
│   │   ├── agent.py      # Agent implementation
│   │   ├── app.py        # Streamlit UI
│   │   ├── scraper.py    # Documentation scraper
│   │   └── tools.py      # Search and processing tools
│   ├── supabase/         # Database setup scripts
│   └── output/           # Scraper output
├── tests/                # Test files
└── requirements.txt      # Project dependencies
```

## Prerequisites

- Python 3.8+
- Supabase account with a project
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sahani-deriv/flutterflow-doc-agent.git
   cd flutterflow-doc-agent
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

## Running the Project

1. **Setup Supabase:**
   - Create a new Supabase project
   - Enable pg_trgm extension using `supabase/search_metadata.sql`
   - Initialize the documents table using `supabase/init.sql`

2. **Run the Documentation Scraper:**
   ```bash
   cd flutterflow_scraper
   python src/scraper.py
   ```
   This will scrape the FlutterFlow documentation and store it in the output directory.

3. **Start the Assistant:**
   ```bash
   cd flutterflow_scraper
   streamlit run src/app.py
   ```
   The application will be available at `http://localhost:8501`

## Features

- Smart documentation search with metadata and content matching
- Community integration for real-world examples
- Modern chat interface built with Streamlit
- Efficient data storage and retrieval using Supabase

## Dependencies

- langchain, langchain-openai, langchain-community: For agent orchestration
- supabase: Database integration
- streamlit: Web interface
- beautifulsoup4: Web scraping
- python-dotenv: Environment management
- requests: HTTP client

## License

This project is licensed under the MIT License - see the LICENSE file for details.
