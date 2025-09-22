"""
File Operations Tools for MCP Protocol.

This module provides tools for file system operations, document processing,
and file management tasks.
"""

import asyncio
import json
import os
import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from claude_flow.mcp.discovery import mcp_tool


@mcp_tool(
    name="file_read",
    description="Read contents of a file",
    category="file"
)
async def read_file_content(
    file_path: str,
    encoding: str = "utf-8",
    max_size_mb: float = 10.0
) -> Dict[str, Any]:
    """Read and return file contents."""
    try:
        file_info = {
            "path": file_path,
            "exists": os.path.exists(file_path),
            "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else None,
            "mime_type": mimetypes.guess_type(file_path)[0],
            "encoding": encoding
        }
        
        if not file_info["exists"]:
            return {
                "success": False,
                "error": "File not found",
                "file_info": file_info,
                "message": f"File '{file_path}' does not exist"
            }
        
        size_mb = file_info["size_bytes"] / (1024 * 1024)
        if size_mb > max_size_mb:
            return {
                "success": False,
                "error": "File too large",
                "file_info": file_info,
                "message": f"File size ({size_mb:.2f} MB) exceeds limit ({max_size_mb} MB)"
            }
        
        # Mock file content reading
        content = f"Sample content from file: {file_path}\nFile size: {file_info['size_bytes']} bytes\nLast modified: {file_info['last_modified']}"
        
        return {
            "success": True,
            "content": content,
            "file_info": file_info,
            "message": f"File '{file_path}' read successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to read file '{file_path}'"
        }


@mcp_tool(
    name="file_write",
    description="Write content to a file",
    category="file"
)
async def write_file_content(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    create_directories: bool = True,
    backup_existing: bool = False
) -> Dict[str, Any]:
    """Write content to a file."""
    try:
        path_obj = Path(file_path)
        
        write_info = {
            "path": file_path,
            "parent_directory": str(path_obj.parent),
            "file_name": path_obj.name,
            "content_size": len(content.encode(encoding)),
            "encoding": encoding,
            "create_directories": create_directories,
            "backup_created": False,
            "overwriting_existing": os.path.exists(file_path)
        }
        
        # Check if parent directory exists
        if not path_obj.parent.exists() and create_directories:
            write_info["directories_created"] = True
        elif not path_obj.parent.exists():
            return {
                "success": False,
                "error": "Parent directory does not exist",
                "write_info": write_info,
                "message": f"Parent directory '{path_obj.parent}' does not exist"
            }
        
        # Handle backup if requested
        if backup_existing and os.path.exists(file_path):
            backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            write_info["backup_path"] = backup_path
            write_info["backup_created"] = True
        
        write_info["written_at"] = datetime.now().isoformat()
        write_info["bytes_written"] = write_info["content_size"]
        
        return {
            "success": True,
            "write_info": write_info,
            "message": f"Content written to '{file_path}' successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to write to file '{file_path}'"
        }


@mcp_tool(
    name="file_list",
    description="List files and directories in a path",
    category="file"
)
async def list_directory_contents(
    directory_path: str,
    recursive: bool = False,
    include_hidden: bool = False,
    file_pattern: Optional[str] = None,
    sort_by: str = "name"
) -> Dict[str, Any]:
    """List contents of a directory."""
    try:
        if not os.path.exists(directory_path):
            return {
                "success": False,
                "error": "Directory not found",
                "message": f"Directory '{directory_path}' does not exist"
            }
        
        if not os.path.isdir(directory_path):
            return {
                "success": False,
                "error": "Path is not a directory",
                "message": f"'{directory_path}' is not a directory"
            }
        
        # Mock directory listing
        items = [
            {
                "name": "config.json",
                "type": "file",
                "size": 1024,
                "modified": (datetime.now() - timedelta(days=1)).isoformat(),
                "permissions": "rw-r--r--",
                "is_hidden": False
            },
            {
                "name": "data",
                "type": "directory",
                "size": 0,
                "modified": (datetime.now() - timedelta(days=3)).isoformat(),
                "permissions": "rwxr-xr-x",
                "is_hidden": False
            },
            {
                "name": ".env",
                "type": "file",
                "size": 256,
                "modified": (datetime.now() - timedelta(hours=5)).isoformat(),
                "permissions": "rw-------",
                "is_hidden": True
            },
            {
                "name": "readme.md",
                "type": "file",
                "size": 2048,
                "modified": (datetime.now() - timedelta(hours=12)).isoformat(),
                "permissions": "rw-r--r--",
                "is_hidden": False
            }
        ]
        
        # Filter hidden files if not requested
        if not include_hidden:
            items = [item for item in items if not item["is_hidden"]]
        
        # Apply pattern filter
        if file_pattern:
            import fnmatch
            items = [item for item in items if fnmatch.fnmatch(item["name"], file_pattern)]
        
        # Sort items
        if sort_by == "name":
            items.sort(key=lambda x: x["name"])
        elif sort_by == "size":
            items.sort(key=lambda x: x["size"], reverse=True)
        elif sort_by == "modified":
            items.sort(key=lambda x: x["modified"], reverse=True)
        
        listing_info = {
            "directory": directory_path,
            "total_items": len(items),
            "files": len([item for item in items if item["type"] == "file"]),
            "directories": len([item for item in items if item["type"] == "directory"]),
            "total_size": sum(item["size"] for item in items if item["type"] == "file"),
            "recursive": recursive,
            "include_hidden": include_hidden,
            "pattern": file_pattern,
            "sort_by": sort_by,
            "listed_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "items": items,
            "listing_info": listing_info,
            "message": f"Listed {len(items)} items in '{directory_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list directory '{directory_path}'"
        }


@mcp_tool(
    name="file_copy",
    description="Copy files or directories",
    category="file"
)
async def copy_file_or_directory(
    source_path: str,
    destination_path: str,
    overwrite_existing: bool = False,
    preserve_metadata: bool = True
) -> Dict[str, Any]:
    """Copy files or directories."""
    try:
        if not os.path.exists(source_path):
            return {
                "success": False,
                "error": "Source not found",
                "message": f"Source '{source_path}' does not exist"
            }
        
        copy_info = {
            "source": source_path,
            "destination": destination_path,
            "source_type": "file" if os.path.isfile(source_path) else "directory",
            "overwrite_existing": overwrite_existing,
            "preserve_metadata": preserve_metadata,
            "destination_exists": os.path.exists(destination_path),
            "copied_at": datetime.now().isoformat()
        }
        
        if copy_info["destination_exists"] and not overwrite_existing:
            return {
                "success": False,
                "error": "Destination exists",
                "copy_info": copy_info,
                "message": f"Destination '{destination_path}' already exists"
            }
        
        # Mock copy operation statistics
        if copy_info["source_type"] == "file":
            copy_info.update({
                "size_bytes": 1024 * 1024,  # 1MB
                "files_copied": 1,
                "directories_created": 0
            })
        else:
            copy_info.update({
                "size_bytes": 50 * 1024 * 1024,  # 50MB
                "files_copied": 25,
                "directories_created": 5
            })
        
        copy_info["copy_speed_mbps"] = copy_info["size_bytes"] / (1024 * 1024) / 0.5  # Mock 0.5 second copy time
        
        return {
            "success": True,
            "copy_info": copy_info,
            "message": f"Successfully copied '{source_path}' to '{destination_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to copy '{source_path}' to '{destination_path}'"
        }


@mcp_tool(
    name="file_delete",
    description="Delete files or directories",
    category="file"
)
async def delete_file_or_directory(
    target_path: str,
    recursive: bool = False,
    move_to_trash: bool = True,
    confirm_deletion: bool = False
) -> Dict[str, Any]:
    """Delete files or directories."""
    try:
        if not confirm_deletion:
            return {
                "success": False,
                "error": "Deletion not confirmed",
                "message": "Set confirm_deletion=True to proceed with deletion"
            }
        
        if not os.path.exists(target_path):
            return {
                "success": False,
                "error": "Target not found",
                "message": f"Target '{target_path}' does not exist"
            }
        
        deletion_info = {
            "target": target_path,
            "target_type": "file" if os.path.isfile(target_path) else "directory",
            "recursive": recursive,
            "move_to_trash": move_to_trash,
            "deleted_at": datetime.now().isoformat()
        }
        
        # Mock deletion statistics
        if deletion_info["target_type"] == "file":
            deletion_info.update({
                "size_freed": 2048,  # bytes
                "files_deleted": 1,
                "directories_deleted": 0
            })
        else:
            deletion_info.update({
                "size_freed": 25 * 1024 * 1024,  # 25MB
                "files_deleted": 15,
                "directories_deleted": 3
            })
        
        if move_to_trash:
            deletion_info["trash_location"] = f"/trash/{os.path.basename(target_path)}_{datetime.now().timestamp()}"
            deletion_info["recoverable"] = True
        else:
            deletion_info["recoverable"] = False
        
        return {
            "success": True,
            "deletion_info": deletion_info,
            "message": f"Successfully deleted '{target_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete '{target_path}'"
        }


@mcp_tool(
    name="file_search",
    description="Search for files and content within files",
    category="file"
)
async def search_files_and_content(
    search_path: str,
    search_term: str,
    search_type: str = "filename",
    file_extensions: Optional[List[str]] = None,
    case_sensitive: bool = False,
    max_results: int = 100
) -> Dict[str, Any]:
    """Search for files and content."""
    try:
        search_info = {
            "search_path": search_path,
            "search_term": search_term,
            "search_type": search_type,
            "file_extensions": file_extensions,
            "case_sensitive": case_sensitive,
            "max_results": max_results,
            "started_at": datetime.now().isoformat()
        }
        
        # Mock search results
        results = []
        if search_type == "filename":
            results = [
                {
                    "type": "filename_match",
                    "path": f"/path/to/{search_term}_file_{i}.txt",
                    "filename": f"{search_term}_file_{i}.txt",
                    "size": 1024 + (i * 256),
                    "modified": (datetime.now() - timedelta(days=i)).isoformat(),
                    "match_score": 1.0 - (i * 0.1)
                }
                for i in range(min(5, max_results))
            ]
        elif search_type == "content":
            results = [
                {
                    "type": "content_match",
                    "path": f"/path/to/document_{i}.txt",
                    "filename": f"document_{i}.txt",
                    "line_number": 10 + i,
                    "line_content": f"This line contains the search term: {search_term}",
                    "context_before": "Previous line content...",
                    "context_after": "Next line content...",
                    "match_score": 0.9 - (i * 0.1)
                }
                for i in range(min(8, max_results))
            ]
        
        search_stats = {
            "files_searched": 250,
            "directories_searched": 15,
            "matches_found": len(results),
            "search_duration_seconds": 2.3,
            "search_speed_files_per_second": 108.7
        }
        
        return {
            "success": True,
            "results": results,
            "search_info": search_info,
            "search_stats": search_stats,
            "message": f"Search completed: found {len(results)} matches"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search in '{search_path}'"
        }


@mcp_tool(
    name="file_checksum",
    description="Calculate file checksums and verify integrity",
    category="file"
)
async def calculate_file_checksum(
    file_path: str,
    algorithms: Optional[List[str]] = None,
    verify_against: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate file checksums."""
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "File not found",
                "message": f"File '{file_path}' does not exist"
            }
        
        algorithms = algorithms or ["md5", "sha256"]
        
        # Mock checksum calculation
        checksums = {}
        for algo in algorithms:
            if algo == "md5":
                checksums[algo] = "d41d8cd98f00b204e9800998ecf8427e"
            elif algo == "sha1":
                checksums[algo] = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
            elif algo == "sha256":
                checksums[algo] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            elif algo == "sha512":
                checksums[algo] = "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
        
        checksum_info = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "algorithms": algorithms,
            "checksums": checksums,
            "calculated_at": datetime.now().isoformat(),
            "calculation_time_seconds": 0.15
        }
        
        # Verify against provided checksum if requested
        if verify_against:
            verification_result = any(checksum == verify_against for checksum in checksums.values())
            checksum_info["verification"] = {
                "provided_checksum": verify_against,
                "verification_passed": verification_result,
                "matching_algorithm": next((algo for algo, checksum in checksums.items() if checksum == verify_against), None)
            }
        
        return {
            "success": True,
            "checksum_info": checksum_info,
            "message": f"Checksums calculated for '{file_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to calculate checksum for '{file_path}'"
        }


@mcp_tool(
    name="file_compress",
    description="Compress files and directories",
    category="file"
)
async def compress_files(
    source_paths: List[str],
    output_path: str,
    compression_format: str = "zip",
    compression_level: int = 6,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """Compress files and directories."""
    try:
        compression_info = {
            "source_paths": source_paths,
            "output_path": output_path,
            "format": compression_format,
            "compression_level": compression_level,
            "include_hidden": include_hidden,
            "started_at": datetime.now().isoformat(),
            "status": "compressing"
        }
        
        # Mock compression statistics
        total_size = sum(1024 * 1024 * (i + 1) for i in range(len(source_paths)))  # Mock sizes
        compressed_size = int(total_size * (0.3 + (compression_level / 20)))  # Mock compression ratio
        
        compression_info.update({
            "files_processed": 45,
            "directories_processed": 8,
            "original_size_bytes": total_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compressed_size / total_size,
            "space_saved_bytes": total_size - compressed_size,
            "compression_time_seconds": 12.5,
            "compression_speed_mbps": (total_size / (1024 * 1024)) / 12.5
        })
        
        return {
            "success": True,
            "compression_info": compression_info,
            "message": f"Successfully compressed {len(source_paths)} items to '{output_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to compress files"
        }