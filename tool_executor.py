"""
Tool Executor module - Dispatcher for calling appropriate pre-written local tools.
Acts as a dispatcher to call specific tools based on orchestrator instructions.
"""

import logging
import importlib
from typing import Dict, Any, Optional
from tools import web_scraper, data_inspector

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Dispatcher that manages and executes local tools.
    Provides a unified interface for calling different analysis tools.
    """
    
    def __init__(self):
        # Registry of available tools
        self.available_tools = {
            'web_scraper': web_scraper,
            'data_inspector': data_inspector,
            'data_reader': self  # Built-in data reading functionality
        }
        logger.info(f"ToolExecutor initialized with tools: {list(self.available_tools.keys())}")
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a specific tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result from tool execution
        """
        logger.info(f"Executing tool: {tool_name} with parameters: {list(parameters.keys())}")
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self.available_tools.keys())}")
        
        try:
            if tool_name == 'web_scraper':
                return self._execute_web_scraper(parameters)
            elif tool_name == 'data_inspector':
                return self._execute_data_inspector(parameters)
            elif tool_name == 'data_reader':
                return self._execute_data_reader(parameters)
            else:
                # Generic tool execution
                tool_module = self.available_tools[tool_name]
                if hasattr(tool_module, 'execute'):
                    return tool_module.execute(parameters)
                else:
                    raise AttributeError(f"Tool '{tool_name}' does not have an 'execute' method")
                    
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {str(e)}")
            raise
    
    def _execute_web_scraper(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web scraper tool."""
        url = parameters.get('url')
        if not url:
            raise ValueError("URL parameter is required for web scraper")
        
        return web_scraper.scrape_url(url)
    
    def _execute_data_inspector(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data inspector tool."""
        data = parameters.get('data')
        source_type = parameters.get('source_type', 'unknown')
        
        if data is None:
            raise ValueError("Data parameter is required for data inspector")
        
        return data_inspector.inspect_data(data, source_type)
    
    def _execute_data_reader(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in data reader for uploaded files."""
        filename = parameters.get('filename', '')
        content = parameters.get('content')
        
        if content is None:
            raise ValueError("Content parameter is required for data reader")
        
        return self._process_file_content(filename, content)
    
    def _process_file_content(self, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Process uploaded file content based on file type.
        
        Args:
            filename: Name of the uploaded file
            content: Raw content of the file
            
        Returns:
            Processed data with metadata
        """
        import pandas as pd
        import io
        import json
        from pathlib import Path
        
        file_ext = Path(filename).suffix.lower()
        
        try:
            if file_ext == '.csv':
                # Process CSV file
                text_content = content.decode('utf-8')
                df = pd.read_csv(io.StringIO(text_content))
                return {
                    'type': 'csv',
                    'filename': filename,
                    'data': df.to_dict('records'),
                    'columns': list(df.columns),
                    'shape': [int(df.shape[0]), int(df.shape[1])],
                    'dtypes': {str(k): str(v) for k, v in df.dtypes.to_dict().items()}
                }
            
            elif file_ext in ['.xlsx', '.xls']:
                # Process Excel file
                df = pd.read_excel(io.BytesIO(content))
                return {
                    'type': 'excel',
                    'filename': filename,
                    'data': df.to_dict('records'),
                    'columns': list(df.columns),
                    'shape': [int(df.shape[0]), int(df.shape[1])],
                    'dtypes': {str(k): str(v) for k, v in df.dtypes.to_dict().items()}
                }
            
            elif file_ext == '.json':
                # Process JSON file
                text_content = content.decode('utf-8')
                json_data = json.loads(text_content)
                return {
                    'type': 'json',
                    'filename': filename,
                    'data': json_data,
                    'structure': self._analyze_json_structure(json_data)
                }
            
            elif file_ext == '.txt':
                # Process text file
                text_content = content.decode('utf-8')
                return {
                    'type': 'text',
                    'filename': filename,
                    'content': text_content,
                    'length': len(text_content),
                    'lines': len(text_content.split('\n'))
                }
            
            else:
                # Try to decode as text for other formats
                try:
                    text_content = content.decode('utf-8')
                    return {
                        'type': 'text',
                        'filename': filename,
                        'content': text_content,
                        'length': len(text_content),
                        'lines': len(text_content.split('\n'))
                    }
                except UnicodeDecodeError:
                    return {
                        'type': 'binary',
                        'filename': filename,
                        'size': len(content),
                        'error': 'Cannot decode as text'
                    }
        
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            return {
                'type': 'error',
                'filename': filename,
                'error': str(e)
            }
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze JSON structure to provide metadata."""
        if max_depth <= 0:
            return {"type": type(data).__name__, "truncated": True}
        
        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys())[:10],  # Limit to first 10 keys
                "key_count": len(data),
                "sample_values": {
                    k: self._analyze_json_structure(v, max_depth - 1) 
                    for k, v in list(data.items())[:3]  # Sample first 3 items
                }
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "sample_items": [
                    self._analyze_json_structure(item, max_depth - 1) 
                    for item in data[:3]  # Sample first 3 items
                ]
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100] if isinstance(data, str) else data
            }
    
    def get_available_tools(self) -> Dict[str, str]:
        """
        Get list of available tools with descriptions.
        
        Returns:
            Dictionary mapping tool names to descriptions
        """
        return {
            'web_scraper': 'Fetches and extracts content from web pages',
            'data_inspector': 'Analyzes data structure and extracts metadata',
            'data_reader': 'Processes uploaded files (CSV, Excel, JSON, text)'
        }
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters for a specific tool.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        if tool_name == 'web_scraper':
            return 'url' in parameters and parameters['url']
        elif tool_name == 'data_inspector':
            return 'data' in parameters
        elif tool_name == 'data_reader':
            return 'content' in parameters
        else:
            return True  # Assume valid for unknown tools