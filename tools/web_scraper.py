"""
Web Scraper tool - Fetches and extracts content from web pages.
Handles various types of web content and extracts structured data.
"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import time
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)

def scrape_url(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Scrape content from a given URL.
    
    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary containing scraped content and metadata
    """
    logger.info(f"Starting web scraping for URL: {url}")
    
    try:
        # Validate URL
        if not _is_valid_url(url):
            return {
                "success": False,
                "error": "Invalid URL format",
                "url": url
            }
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parse content based on content type
        content_type = response.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type:
            return _parse_html_content(response.text, url)
        elif 'application/json' in content_type:
            return _parse_json_content(response.text, url)
        elif 'text/csv' in content_type:
            return _parse_csv_content(response.text, url)
        else:
            return _parse_text_content(response.text, url, content_type)
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while scraping {url}")
        return {
            "success": False,
            "error": f"Request timeout after {timeout} seconds",
            "url": url
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while scraping {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "url": url
        }
    
    except Exception as e:
        logger.error(f"Unexpected error while scraping {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": url
        }

def _is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def _parse_html_content(html: str, url: str) -> Dict[str, Any]:
    """Parse HTML content and extract structured data."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract basic metadata
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title"
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        # Extract headings
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                headings.append({
                    'level': i,
                    'text': heading.get_text().strip()
                })
        
        # Extract paragraphs
        paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
        
        # Extract tables
        tables = _extract_tables(soup)
        
        # Extract links
        links = _extract_links(soup, url)
        
        # Extract images
        images = _extract_images(soup, url)
        
        # Clean text content
        # Remove scripts and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text_content = soup.get_text()
        cleaned_text = _clean_text(text_content)
        
        return {
            "success": True,
            "url": url,
            "content_type": "html",
            "title": title_text,
            "description": description,
            "text_content": cleaned_text,
            "word_count": len(cleaned_text.split()),
            "structure": {
                "headings": headings[:20],  # Limit to first 20 headings
                "paragraphs": paragraphs[:10],  # Limit to first 10 paragraphs
                "tables": tables,
                "links": links[:50],  # Limit to first 50 links
                "images": images[:20]  # Limit to first 20 images
            }
        }
    
    except Exception as e:
        logger.error(f"Error parsing HTML content: {str(e)}")
        return {
            "success": False,
            "error": f"HTML parsing failed: {str(e)}",
            "url": url
        }

def _extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract table data from HTML."""
    tables = []
    
    for table in soup.find_all('table'):
        rows = []
        headers = []
        
        # Try to find headers
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
        
        # Extract all rows
        for row in table.find_all('tr'):
            cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
            if cells:
                rows.append(cells)
        
        if rows:
            tables.append({
                'headers': headers,
                'rows': rows[:50],  # Limit to first 50 rows
                'row_count': len(rows)
            })
    
    return tables

def _extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """Extract links from HTML."""
    links = []
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text().strip()
        
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)
        
        if text and absolute_url:
            links.append({
                'text': text,
                'url': absolute_url
            })
    
    return links

def _extract_images(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """Extract image information from HTML."""
    images = []
    
    for img in soup.find_all('img'):
        src = img.get('src')
        alt = img.get('alt', '')
        
        if src:
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, src)
            
            images.append({
                'src': absolute_url,
                'alt': alt
            })
    
    return images

def _parse_json_content(json_text: str, url: str) -> Dict[str, Any]:
    """Parse JSON content."""
    try:
        import json
        data = json.loads(json_text)
        
        return {
            "success": True,
            "url": url,
            "content_type": "json",
            "data": data,
            "structure": _analyze_json_structure(data)
        }
    
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON: {str(e)}",
            "url": url
        }

def _parse_csv_content(csv_text: str, url: str) -> Dict[str, Any]:
    """Parse CSV content."""
    try:
        import csv
        import io
        
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        
        return {
            "success": True,
            "url": url,
            "content_type": "csv",
            "headers": headers,
            "rows": data_rows[:100],  # Limit to first 100 rows
            "total_rows": len(data_rows)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"CSV parsing failed: {str(e)}",
            "url": url
        }

def _parse_text_content(text: str, url: str, content_type: str) -> Dict[str, Any]:
    """Parse plain text content."""
    cleaned_text = _clean_text(text)
    
    return {
        "success": True,
        "url": url,
        "content_type": content_type,
        "text_content": cleaned_text,
        "word_count": len(cleaned_text.split()),
        "line_count": len(cleaned_text.split('\n'))
    }

def _clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Limit length to prevent memory issues
    max_length = 50000  # 50KB
    if len(text) > max_length:
        text = text[:max_length] + "... [TRUNCATED]"
    
    return text

def _analyze_json_structure(data: Any, max_depth: int = 3) -> Dict[str, Any]:
    """Analyze JSON structure recursively."""
    if max_depth <= 0:
        return {"type": type(data).__name__, "truncated": True}
    
    if isinstance(data, dict):
        return {
            "type": "dict",
            "keys": list(data.keys())[:10],
            "key_count": len(data),
            "sample_values": {
                k: _analyze_json_structure(v, max_depth - 1)
                for k, v in list(data.items())[:3]
            }
        }
    elif isinstance(data, list):
        return {
            "type": "list",
            "length": len(data),
            "sample_items": [
                _analyze_json_structure(item, max_depth - 1)
                for item in data[:3]
            ]
        }
    else:
        return {
            "type": type(data).__name__,
            "value": str(data)[:100] if isinstance(data, str) else data
        }