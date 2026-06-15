"""
Folder manager utility for file and directory operations.

This module provides utilities for managing folders, files, and paths
in the HFOrchestra system.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class FolderManager:
    """Manages folder operations and file organization."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            "logs",
            "reports", 
            "db",
            "config",
            "backups",
            "audio",
            "audio_processing"
        ]
        
        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(exist_ok=True)
    
    def create_backup(self, source_paths: List[str], backup_name: Optional[str] = None) -> str:
        """Create a backup of specified files/directories."""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        backup_dir = self.base_path / "backups" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for source_path in source_paths:
            source = Path(source_path)
            if source.exists():
                if source.is_file():
                    shutil.copy2(source, backup_dir / source.name)
                else:
                    shutil.copytree(source, backup_dir / source.name, dirs_exist_ok=True)
        
        return str(backup_dir)
    
    def cleanup_old_backups(self, max_backups: int = 10):
        """Remove old backups, keeping only the most recent ones."""
        backup_dir = self.base_path / "backups"
        if not backup_dir.exists():
            return
        
        backups = [d for d in backup_dir.iterdir() if d.is_dir()]
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old backups
        for backup in backups[max_backups:]:
            shutil.rmtree(backup)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information."""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        stat = path.stat()
        return {
            "name": path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "extension": path.suffix,
            "parent": str(path.parent)
        }
    
    def list_files(self, directory: str, pattern: str = "*", recursive: bool = False) -> List[str]:
        """List files in a directory matching a pattern."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        return [str(f) for f in files if f.is_file()]
    
    def safe_delete(self, file_path: str) -> bool:
        """Safely delete a file with error handling."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            return False
    
    def get_directory_size(self, directory: str) -> int:
        """Calculate total size of a directory in bytes."""
        total_size = 0
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return 0
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB" 