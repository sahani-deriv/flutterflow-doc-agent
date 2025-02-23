import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Set
import requests
from lxml import etree
from tqdm import tqdm
from urllib.parse import urlparse
from openai import AsyncOpenAI
from supabase import create_client, Client
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

class FlutterFlowScraper:
    def __init__(self):
        # Load environment variables from .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        print(f"Loading .env file from: {env_path}")
        
        # Read .env file directly
        with open(env_path) as f:
            env_lines = f.readlines()
            env_vars = {}
            for line in env_lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
        
        # Initialize OpenAI client
        openai_api_key = env_vars.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        self.openai_client = AsyncOpenAI(api_key=openai_api_key, base_url="https://litellm.deriv.ai/v1")

        # Initialize Supabase client
        self.supabase_url = env_vars.get("SUPABASE_URL")
        self.supabase_key = env_vars.get("SUPABASE_KEY")
        print(f"Supabase URL from .env: {self.supabase_url}")
        print(f"Supabase key from .env: {self.supabase_key[:10]}...")  # Print first 10 chars for verification
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        # Create Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
         
        # Configure client headers
        self.supabase.postgrest.auth(self.supabase_key)
        
        # Verify Supabase connection on initialization
        try:
            test_query = self.supabase.table("documents").select("id").limit(1).execute()
            print("Successfully connected to Supabase and verified table existence")
        except Exception as e:
            print(f"Error connecting to Supabase: {str(e)}")
            print(f"Full error details: {repr(e)}")
            raise
        
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.base_url = "https://docs.flutterflow.io"
        self.batch_size = 1  # Process one URL at a time for testing
        self.max_concurrent = 1  # Single concurrent request
        self.max_retries = 5  # More retries for browser initialization
        self.page_timeout = 60000  # Longer timeout (60 seconds)
        
        # Configure browser settings
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=True,
            # Additional browser args
        )
        
        # Initialize semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Disallowed paths from robots.txt
        self.disallowed_paths = [
            "/tags/",
            "/blog/",
            "/troubleshooting/"
        ]
        
        # Configure browser settings
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=True,
        )
        
        # Configure crawler settings
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.48,
                    threshold_type="fixed",
                    min_word_threshold=0
                )
            ),
            js_code=[
                """
                async function extractContent() {
                    try {
                        console.log('Starting content extraction...');
                        
                        // Wait for dynamic content to load
                        await new Promise(r => setTimeout(r, 8000));
                        console.log('Finished waiting for content load');
                        
                        // Log the entire document HTML for debugging
                        console.log('Document HTML:', document.documentElement.outerHTML);
                        
                        // Try to find the main content using more specific selectors
                        const selectors = [
                            'article[class*="docItemContainer"]',
                            'article[class*="theme-doc-markdown"]',
                            'div[class*="theme-doc-markdown"]',
                            'div[class*="docItemContainer"]',
                            'main[class*="docMainContainer"]',
                            'div[class*="docMainContainer"]',
                            'main article',
                            '.markdown',
                            'main',
                            'article'
                        ];
                        
                        // Log all elements matching each selector
                        selectors.forEach(selector => {
                            const elements = document.querySelectorAll(selector);
                            console.log(`Found ${elements.length} elements matching selector: ${selector}`);
                            elements.forEach((el, i) => {
                                console.log(`Element ${i} classes:`, el.className);
                                console.log(`Element ${i} content length:`, el.innerHTML.length);
                            });
                        });
                        
                        let content = '';
                        let usedSelector = '';
                        
                        // Try each selector
                        for (const selector of selectors) {
                            console.log(`Trying selector: ${selector}`);
                            const element = document.querySelector(selector);
                            if (element) {
                                console.log(`Found content with selector: ${selector}`);
                                
                                // Clone the element to avoid modifying the original
                                const clonedElement = element.cloneNode(true);
                                
                                // Remove navigation and other non-content elements
                                const elementsToRemove = clonedElement.querySelectorAll(
                                    'nav, footer, .sidebar, .pagination-nav, ' +
                                    '.tableOfContents_Dwai, .theme-doc-toc-desktop, ' +
                                    '.theme-doc-toc-mobile, .breadcrumbs, ' +
                                    '.theme-doc-version-badge, .theme-doc-version-banner, ' +
                                    '.theme-doc-footer, .pagination-nav__link'
                                );
                                elementsToRemove.forEach(el => el.remove());
                                
                                // Get cleaned content
                                content = clonedElement.innerHTML;
                                usedSelector = selector;
                                console.log(`Content length with selector ${selector}: ${content.length}`);
                                break;
                            }
                        }
                        
                        // If no content found with selectors, try to get main content area
                        if (!content) {
                            console.log('No content found with primary selectors, trying fallbacks...');
                            const mainContent = document.querySelector('.main-content, .container, #__docusaurus');
                            if (mainContent) {
                                console.log('Found content with fallback selector');
                                const clonedContent = mainContent.cloneNode(true);
                                const elementsToRemove = clonedContent.querySelectorAll(
                                    'nav, footer, .sidebar, .pagination-nav, header'
                                );
                                elementsToRemove.forEach(el => el.remove());
                                content = clonedContent.innerHTML;
                                usedSelector = '.main-content/.container/#__docusaurus';
                                console.log(`Content length with fallback: ${content.length}`);
                            } else {
                                console.log('No content found with any selector');
                                content = document.body.innerHTML;
                                usedSelector = 'body';
                                console.log(`Using body content, length: ${content.length}`);
                            }
                        }
                        
                        // Get the page title
                        const title = document.title || '';
                        console.log(`Page title: ${title}`);
                        
                        return {
                            content: content,
                            usedSelector: usedSelector,
                            documentTitle: title,
                            url: window.location.href,
                            success: true
                        };
                    } catch (error) {
                        console.error('Error in content extraction:', error);
                        return {
                            content: '',
                            usedSelector: '',
                            documentTitle: '',
                            url: window.location.href,
                            success: false,
                            error: error.toString()
                        };
                    }
                }
                return await extractContent();
                """
            ]
        )

    def is_allowed_url(self, url: str) -> bool:
        """
        Check if URL is allowed based on robots.txt rules
        """
        parsed = urlparse(url)
        path = parsed.path
        
        # Check against disallowed paths
        for disallowed in self.disallowed_paths:
            if path.startswith(disallowed):
                print(f"Skipping disallowed URL: {url}")
                return False
        return True

    def get_urls_from_sitemap(self) -> List[str]:
        """
        Get URLs from sitemap.xml and filter based on robots.txt rules
        """
        try:
            print("Fetching URLs from sitemap.xml...")
            response = requests.get(f"{self.base_url}/sitemap.xml")
            response.raise_for_status()
            
            # Parse XML
            root = etree.fromstring(response.content)
            
            # Extract URLs (handle both standard and namespaced XML)
            urls = []
            namespaces = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Try different XPath patterns
            for pattern in ['//url/loc/text()', '//s:url/s:loc/text()']:
                try:
                    found_urls = root.xpath(pattern, namespaces=namespaces)
                    if found_urls:
                        urls.extend([url.strip() for url in found_urls])
                except Exception as e:
                    print(f"Error with XPath pattern {pattern}: {str(e)}")
            
            # Filter URLs based on:
            # 1. Must be documentation URLs
            # 2. Must be allowed by robots.txt
            filtered_urls = [
                url for url in urls 
                if url.startswith(self.base_url) and self.is_allowed_url(url)
            ]
            
            print(f"Found {len(filtered_urls)} allowed documentation URLs in sitemap")
            return filtered_urls
            
        except Exception as e:
            print(f"Error fetching sitemap: {str(e)}")
            # Return a single URL for testing
            return [
                f"{self.base_url}/before-you-begin/setup-flutterflow"
            ]

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text using OpenAI's API
        """
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return []

    async def store_in_supabase(self, doc_data: Dict, embedding: List[float]) -> None:
        """
        Store document data and its embedding in Supabase
        """
        # Store in documents table
        doc_record = {
            "url": doc_data["url"],
            "title": doc_data["title"],
            "summary": doc_data["summary"],
            "content": doc_data["content"],
            "metadata": doc_data["metadata"],
            "embedding": embedding
        }
        
        try:
            # First verify connection and table existence
            test_query = self.supabase.table("documents").select("id").limit(1).execute()
            print("Successfully connected to Supabase and verified table existence")
            
            # Then attempt to insert the document
            result = self.supabase.table("documents").insert(doc_record).execute()
            print(f"Stored document in Supabase: {doc_data['url']}")
            
        except Exception as e:
            print(f"Error storing in Supabase: {str(e)}")
            print(f"Full error details: {repr(e)}")
            # Try to get more details about the connection
            try:
                auth_test = self.supabase.auth.get_user()
                print("Auth test result:", auth_test)
            except Exception as auth_e:
                print("Auth test failed:", str(auth_e))
            raise  # Re-raise the original exception

    async def generate_summary(self, content: str, title: str) -> str:
        """
        Generate a summary of the content using OpenAI
        """
        try:
            prompt = f"Title: {title}\n\nContent:\n{content}\n\nPlease provide a concise 2-3 sentence summary of this FlutterFlow documentation page that captures its key points:"
            
            response = await self.openai_client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[
                    {"role": "system", "content": "You are a technical documentation summarizer. Create clear, concise summaries that capture the key points."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return ""

    async def scrape_single_url(self, url: str, crawler: AsyncWebCrawler, pbar: tqdm) -> Dict:
        """
        Scrape a single URL with semaphore control and generate summary
        """
        try:
            async with self.semaphore:  # Control concurrency
                print(f"\nScraping {url}")
                result = await crawler.arun(
                    url=url,
                    config=self.run_config
                )
                print(result.markdown)
                print(f"\nProcessing result for {url}:")
                # print(f"Result object attributes: {dir(result) if result else 'No result'}")
                # print(f"Raw result: {result.__dict__ if result else 'No result'}")
                title = url.split("/")[-1]
                summary = await self.generate_summary(result.markdown, title)
                content = result.markdown
                # Create document data
                doc_data = {
                    "url": url,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "metadata": {
                        "title": title,
                        "description": result.metadata.get("description", "") if hasattr(result, 'metadata') else "",
                        "last_modified": result.metadata.get("last_modified", "") if hasattr(result, 'metadata') else ""
                    }
                }

                # Generate embedding for the content
                embedding = await self.generate_embedding(content)
                
                # Store in Supabase
                await self.store_in_supabase(doc_data, embedding)
                
                return doc_data
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None
        finally:
            pbar.update(1)

    async def init_crawler_with_retry(self) -> AsyncWebCrawler:
        """
        Initialize crawler with retry logic and timeout
        """
        crawler = None
        for attempt in range(self.max_retries):
            try:
                if crawler:
                    try:
                        await crawler.__aexit__(None, None, None)
                    except:
                        pass
                
                crawler = AsyncWebCrawler(config=self.browser_config)
                await crawler.__aenter__()
                return crawler
            except Exception as e:
                print(f"Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retrying
                else:
                    if crawler:
                        try:
                            await crawler.__aexit__(None, None, None)
                        except:
                            pass
                    raise
    
    async def scrape_urls_batch(self, urls: List[str], pbar: tqdm) -> List[Dict]:
        """
        Scrape a batch of URLs concurrently with improved error handling and retry logic
        """
        results = []
        crawler = None
        try:
            crawler = await self.init_crawler_with_retry()
            
            # Process URLs in smaller sub-batches for better stability
            sub_batch_size = 2
            for i in range(0, len(urls), sub_batch_size):
                sub_batch = urls[i:i + sub_batch_size]
                
                # Create tasks for URLs in sub-batch
                tasks = [self.scrape_single_url(url, crawler, pbar) for url in sub_batch]
                
                try:
                    # Execute tasks concurrently and gather results
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Filter out errors and None results
                    valid_results = [r for r in batch_results if r is not None and not isinstance(r, Exception)]
                    results.extend(valid_results)
                    
                    # Longer delay between sub-batches
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"Error in sub-batch processing: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"Error in batch processing: {str(e)}")
        finally:
            if crawler:
                try:
                    await crawler.__aexit__(None, None, None)
                except Exception as e:
                    print(f"Error closing crawler: {str(e)}")
        
        return results

    def save_results(self, results: List[Dict], filename: str = "scraped_docs.json"):
        """
        Save scraped results to a JSON file
        """
        # Filter out None results from failed scrapes
        valid_results = [r for r in results if r is not None]
        
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(valid_results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_path}")
        print(f"Successfully scraped {len(valid_results)} pages")

    def save_progress(self, results: List[Dict], filename: str = "scraped_docs_partial.json"):
        """
        Save partial results in case of interruption
        """
        try:
            self.save_results(results, filename)
            print("Progress saved successfully")
        except Exception as e:
            print(f"Error saving progress: {str(e)}")

async def main():
    try:
        # Initialize scraper
        scraper = FlutterFlowScraper()
        
        # Get URLs from sitemap
        urls = scraper.get_urls_from_sitemap()
        
        print(f"Starting scrape of {len(urls)} pages...")
        
        # Process URLs in batches
        results = []
        with tqdm(total=len(urls), desc="Scraping pages") as pbar:
            for i in range(0, len(urls), scraper.batch_size):
                batch = urls[i:i + scraper.batch_size]
                batch_results = await scraper.scrape_urls_batch(batch, pbar)
                results.extend(batch_results)
                
                # Save progress after each batch
                scraper.save_progress(results)
        
        # Save final results
        scraper.save_results(results)
        
    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
        # Save progress before exit
        if 'results' in locals() and results:
            scraper.save_progress(results)
        print("Partial results have been saved")        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if 'results' in locals() and results:
            scraper.save_progress(results)

if __name__ == "__main__":
    asyncio.run(main())
