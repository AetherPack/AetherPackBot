"""
Web Search Extension - Search the web for information.

Provides web search capabilities using multiple search engines.
"""

from __future__ import annotations

import asyncio
import html
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from core.api.plugins import Plugin, PluginMetadata, PluginStatus
from core.api.agents import Tool, ToolParameter, ToolResult

if TYPE_CHECKING:
    from core.kernel.container import ServiceContainer


class WebSearchExtension(Plugin):
    """
    Web search extension.
    
    Provides tools for searching the web using various search APIs.
    """
    
    def __init__(self) -> None:
        self._status = PluginStatus.LOADED
        self._container: ServiceContainer | None = None
        self._search_engine: str = "duckduckgo"
        self._api_key: str | None = None
        self._max_results: int = 5
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_search",
            version="1.0.0",
            description="Search the web for information",
            author="AetherPackBot",
            dependencies=[],
            entry_point="",
        )
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @property
    def is_builtin(self) -> bool:
        return True
    
    async def initialize(self, container: "ServiceContainer") -> None:
        """Initialize the extension."""
        self._container = container
        self._status = PluginStatus.LOADED
        
        try:
            from core.storage.config import ConfigurationManager
            config = await container.resolve(ConfigurationManager)
            
            search_config = config.get("search", {})
            self._search_engine = search_config.get("engine", "duckduckgo")
            self._api_key = search_config.get("api_key")
            self._max_results = search_config.get("max_results", 5)
        except Exception:
            pass
    
    async def activate(self) -> None:
        """Activate the extension."""
        self._status = PluginStatus.RUNNING
    
    async def deactivate(self) -> None:
        """Deactivate the extension."""
        self._status = PluginStatus.LOADED
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._status = PluginStatus.UNLOADED
    
    def get_tool(self) -> Tool:
        """Get the web search tool."""
        return Tool(
            name="web_search",
            description="Search the web for current information. "
                        "Use this when you need up-to-date information or facts.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results to return (default 5)",
                    required=False,
                    default=5,
                ),
            ],
            handler=self.search,
            enabled=True,
        )
    
    async def search(self, query: str, num_results: int = 5) -> ToolResult:
        """
        Search the web.
        
        Args:
            query: Search query.
            num_results: Maximum number of results.
            
        Returns:
            Tool result with search results.
        """
        num_results = min(num_results, self._max_results)
        
        try:
            if self._search_engine == "google" and self._api_key:
                results = await self._search_google(query, num_results)
            elif self._search_engine == "bing" and self._api_key:
                results = await self._search_bing(query, num_results)
            else:
                results = await self._search_duckduckgo(query, num_results)
            
            if not results:
                return ToolResult(
                    success=True,
                    output="No results found for the query.",
                    error=None,
                )
            
            # Format results
            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(f"{i}. **{result['title']}**")
                formatted.append(f"   URL: {result['url']}")
                if result.get('snippet'):
                    formatted.append(f"   {result['snippet']}")
                formatted.append("")
            
            return ToolResult(
                success=True,
                output="\n".join(formatted),
                error=None,
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    async def _search_duckduckgo(
        self,
        query: str,
        num_results: int,
    ) -> list[dict[str, str]]:
        """Search using DuckDuckGo."""
        import aiohttp
        
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data={"q": query},
                headers=headers,
            ) as response:
                if response.status != 200:
                    raise Exception(f"Search failed with status {response.status}")
                
                html_content = await response.text()
        
        # Parse results
        results = []
        
        # Simple regex parsing
        result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>(.+?)</a>'
        
        matches = re.findall(result_pattern, html_content)
        snippets = re.findall(snippet_pattern, html_content, re.DOTALL)
        
        for i, (url, title) in enumerate(matches[:num_results]):
            result = {
                "url": html.unescape(url),
                "title": html.unescape(title).strip(),
                "snippet": "",
            }
            
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i])
                result["snippet"] = html.unescape(snippet).strip()
            
            results.append(result)
        
        return results
    
    async def _search_google(
        self,
        query: str,
        num_results: int,
    ) -> list[dict[str, str]]:
        """Search using Google Custom Search API."""
        import aiohttp
        
        if not self._api_key:
            raise Exception("Google API key not configured")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self._api_key,
            "cx": "YOUR_SEARCH_ENGINE_ID",  # Needs configuration
            "q": query,
            "num": num_results,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Google search failed: {response.status}")
                
                data = await response.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "url": item["link"],
                "title": item["title"],
                "snippet": item.get("snippet", ""),
            })
        
        return results
    
    async def _search_bing(
        self,
        query: str,
        num_results: int,
    ) -> list[dict[str, str]]:
        """Search using Bing Search API."""
        import aiohttp
        
        if not self._api_key:
            raise Exception("Bing API key not configured")
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
        }
        params = {
            "q": query,
            "count": num_results,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                params=params,
            ) as response:
                if response.status != 200:
                    raise Exception(f"Bing search failed: {response.status}")
                
                data = await response.json()
        
        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "url": item["url"],
                "title": item["name"],
                "snippet": item.get("snippet", ""),
            })
        
        return results


class FetchWebpageExtension(Plugin):
    """
    Fetch and extract content from web pages.
    """
    
    def __init__(self) -> None:
        self._status = PluginStatus.LOADED
        self._container: ServiceContainer | None = None
        self._max_length: int = 10000
    
    @property
    def name(self) -> str:
        return "fetch_webpage"
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="fetch_webpage",
            version="1.0.0",
            description="Fetch and extract content from web pages",
            author="AetherPackBot",
            dependencies=[],
            entry_point="",
        )
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @property
    def is_builtin(self) -> bool:
        return True
    
    async def initialize(self, container: "ServiceContainer") -> None:
        """Initialize the extension."""
        self._container = container
        self._status = PluginStatus.LOADED
    
    async def activate(self) -> None:
        """Activate the extension."""
        self._status = PluginStatus.RUNNING
    
    async def deactivate(self) -> None:
        """Deactivate the extension."""
        self._status = PluginStatus.LOADED
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._status = PluginStatus.UNLOADED
    
    def get_tool(self) -> Tool:
        """Get the fetch webpage tool."""
        return Tool(
            name="fetch_webpage",
            description="Fetch and extract text content from a URL. "
                        "Use this to read the content of a specific web page.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL of the webpage to fetch",
                    required=True,
                ),
            ],
            handler=self.fetch,
            enabled=True,
        )
    
    async def fetch(self, url: str) -> ToolResult:
        """
        Fetch and extract content from a URL.
        
        Args:
            url: URL to fetch.
            
        Returns:
            Tool result with extracted content.
        """
        import aiohttp
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Failed to fetch URL: HTTP {response.status}",
                        )
                    
                    content_type = response.headers.get("Content-Type", "")
                    
                    if "text/html" in content_type:
                        html_content = await response.text()
                        text = self._extract_text(html_content)
                    elif "text/" in content_type:
                        text = await response.text()
                    else:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Unsupported content type: {content_type}",
                        )
            
            # Truncate if needed
            if len(text) > self._max_length:
                text = text[:self._max_length] + "\n\n... (content truncated)"
            
            return ToolResult(
                success=True,
                output=text,
                error=None,
            )
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error="Request timed out",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    def _extract_text(self, html_content: str) -> str:
        """Extract readable text from HTML."""
        # Remove scripts and styles
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<head[^>]*>.*?</head>', '', html_content, flags=re.DOTALL)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Decode entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
