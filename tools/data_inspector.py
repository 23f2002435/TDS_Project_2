"""
Data Inspector tool - Analyzes data structure and extracts compact metadata.
Provides structural metadata for different types of data sources.
"""

import logging
from typing import Dict, Any, Union, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def inspect_data(data: Any, source_type: str = 'unknown') -> Dict[str, Any]:
    """
    Inspect data and extract compact metadata.
    
    Args:
        data: The data to inspect
        source_type: Type of data source ('url', 'file', 'text_only', etc.)
        
    Returns:
        Dictionary containing data metadata and structure information
    """
    logger.info(f"Inspecting data of source type: {source_type}")
    
    try:
        if source_type == 'url':
            return _inspect_web_data(data)
        elif source_type == 'file':
            return _inspect_file_data(data)
        else:
            return _inspect_generic_data(data, source_type)
    
    except Exception as e:
        logger.error(f"Error inspecting data: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "source_type": source_type
        }

def _inspect_web_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect web-scraped data."""
    if not data.get("success", False):
        return {
            "success": False,
            "error": data.get("error", "Web scraping failed"),
            "source_type": "url"
        }
    
    content_type = data.get("content_type", "unknown")
    metadata = {
        "success": True,
        "source_type": "url",
        "content_type": content_type,
        "url": data.get("url", ""),
    }
    
    if content_type == "html":
        metadata.update(_analyze_html_data(data))
    elif content_type == "json":
        metadata.update(_analyze_json_data(data))
    elif content_type == "csv":
        metadata.update(_analyze_csv_data(data))
    else:
        metadata.update(_analyze_text_data(data))
    
    return metadata

def _inspect_file_data(data: Union[List[Dict], Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect file data."""
    if isinstance(data, list):
        # Multiple files
        files_metadata = []
        for file_data in data:
            files_metadata.append(_inspect_single_file(file_data))
        
        return {
            "success": True,
            "source_type": "file",
            "file_count": len(data),
            "files": files_metadata
        }
    else:
        # Single file
        single_file_meta = _inspect_single_file(data)
        return {
            "success": True,
            "source_type": "file",
            "file_count": 1,
            **single_file_meta
        }

def _inspect_single_file(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect a single file's data."""
    file_type = file_data.get("type", "unknown")
    filename = file_data.get("filename", "unknown")
    
    metadata = {
        "filename": filename,
        "file_type": file_type
    }
    
    if file_type == "csv":
        metadata.update(_analyze_dataframe_data(file_data))
    elif file_type == "excel":
        metadata.update(_analyze_dataframe_data(file_data))
    elif file_type == "json":
        metadata.update(_analyze_json_file_data(file_data))
    elif file_type == "text":
        metadata.update(_analyze_text_file_data(file_data))
    else:
        metadata["error"] = file_data.get("error", "Unknown file type")
    
    return metadata

def _inspect_generic_data(data: Any, source_type: str) -> Dict[str, Any]:
    """Inspect generic data."""
    return {
        "success": True,
        "source_type": source_type,
        "data_type": type(data).__name__,
        "summary": _get_data_summary(data)
    }

def _analyze_html_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze HTML web page data."""
    structure = data.get("structure", {})
    
    return {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "word_count": data.get("word_count", 0),
        "structure_summary": {
            "heading_count": len(structure.get("headings", [])),
            "paragraph_count": len(structure.get("paragraphs", [])),
            "table_count": len(structure.get("tables", [])),
            "link_count": len(structure.get("links", [])),
            "image_count": len(structure.get("images", []))
        },
        "tables": _summarize_tables(structure.get("tables", [])),
        "headings": [h.get("text", "") for h in structure.get("headings", [])[:10]],
        "key_content": structure.get("paragraphs", [])[:5]
    }

def _analyze_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze JSON web data."""
    json_data = data.get("data", {})
    structure = data.get("structure", {})
    
    return {
        "json_structure": structure,
        "data_summary": _get_data_summary(json_data),
        "estimated_size": _estimate_data_size(json_data)
    }

def _analyze_csv_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze CSV web data."""
    headers = data.get("headers", [])
    total_rows = data.get("total_rows", 0)
    
    return {
        "columns": headers,
        "column_count": len(headers),
        "row_count": total_rows,
        "sample_data": data.get("rows", [])[:5]
    }

def _analyze_text_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze plain text data."""
    return {
        "word_count": data.get("word_count", 0),
        "line_count": data.get("line_count", 0),
        "content_preview": data.get("text_content", "")[:500]
    }

def _analyze_dataframe_data(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze CSV/Excel file data."""
    columns = file_data.get("columns", [])
    shape = file_data.get("shape", (0, 0))
    dtypes = file_data.get("dtypes", {})
    sample_data = file_data.get("data", [])
    
    # Analyze column types
    column_analysis = {}
    for col in columns:
        dtype = str(dtypes.get(col, 'unknown'))
        column_analysis[col] = {
            "type": dtype,
            "category": _categorize_column_type(dtype)
        }
    
    # Get basic statistics
    numeric_columns = [col for col, info in column_analysis.items() 
                      if info["category"] == "numeric"]
    text_columns = [col for col, info in column_analysis.items() 
                   if info["category"] == "text"]
    
    return {
        "shape": shape,
        "columns": columns,
        "column_count": len(columns),
        "row_count": shape[0] if shape else 0,
        "column_analysis": column_analysis,
        "summary": {
            "numeric_columns": len(numeric_columns),
            "text_columns": len(text_columns),
            "total_columns": len(columns)
        },
        "sample_data": sample_data[:5],
        "data_types": dtypes
    }

def _analyze_json_file_data(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze JSON file data."""
    json_data = file_data.get("data", {})
    structure = file_data.get("structure", {})
    
    return {
        "json_structure": structure,
        "data_summary": _get_data_summary(json_data),
        "estimated_size": _estimate_data_size(json_data)
    }

def _analyze_text_file_data(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze text file data."""
    content = file_data.get("content", "")
    
    return {
        "length": file_data.get("length", 0),
        "line_count": file_data.get("lines", 0),
        "word_count": len(content.split()) if content else 0,
        "content_preview": content[:500] if content else ""
    }

def _summarize_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Summarize table structures."""
    summaries = []
    
    for i, table in enumerate(tables):
        headers = table.get("headers", [])
        row_count = table.get("row_count", 0)
        
        summary = {
            "table_index": i,
            "headers": headers,
            "column_count": len(headers),
            "row_count": row_count,
            "sample_data": table.get("rows", [])[:3]
        }
        summaries.append(summary)
    
    return summaries

def _categorize_column_type(dtype_str: str) -> str:
    """Categorize column data type."""
    dtype_lower = dtype_str.lower()
    
    if any(t in dtype_lower for t in ['int', 'float', 'number']):
        return "numeric"
    elif any(t in dtype_lower for t in ['datetime', 'timestamp', 'date']):
        return "datetime"
    elif any(t in dtype_lower for t in ['bool', 'boolean']):
        return "boolean"
    else:
        return "text"

def _get_data_summary(data: Any) -> Dict[str, Any]:
    """Get a general summary of any data structure."""
    summary = {
        "type": type(data).__name__,
        "size": _estimate_data_size(data)
    }
    
    if isinstance(data, dict):
        summary.update({
            "key_count": len(data),
            "keys": list(data.keys())[:10]
        })
    elif isinstance(data, list):
        summary.update({
            "length": len(data),
            "item_types": list(set(type(item).__name__ for item in data[:100]))
        })
    elif isinstance(data, str):
        summary.update({
            "length": len(data),
            "word_count": len(data.split()),
            "preview": data[:200]
        })
    
    return summary

def _estimate_data_size(data: Any) -> str:
    """Estimate the size of data structure."""
    try:
        import sys
        size_bytes = sys.getsizeof(data)
        
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    except:
        return "unknown"

def get_column_statistics(data: List[Dict[str, Any]], column: str) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific column.
    
    Args:
        data: List of dictionaries (rows)
        column: Column name to analyze
        
    Returns:
        Dictionary with column statistics
    """
    try:
        # Extract column values
        values = [row.get(column) for row in data if column in row]
        non_null_values = [v for v in values if v is not None and v != '']
        
        if not non_null_values:
            return {"error": "No valid values found in column"}
        
        # Basic statistics
        stats = {
            "total_count": len(values),
            "non_null_count": len(non_null_values),
            "null_count": len(values) - len(non_null_values),
            "unique_count": len(set(str(v) for v in non_null_values))
        }
        
        # Try to convert to numeric for more stats
        try:
            numeric_values = [float(v) for v in non_null_values 
                            if str(v).replace('.', '').replace('-', '').isdigit()]
            
            if numeric_values:
                stats.update({
                    "numeric_count": len(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "mean": sum(numeric_values) / len(numeric_values),
                    "median": sorted(numeric_values)[len(numeric_values) // 2]
                })
        except:
            pass
        
        # Sample values
        stats["sample_values"] = list(set(str(v) for v in non_null_values))[:10]
        
        return stats
    
    except Exception as e:
        return {"error": str(e)}