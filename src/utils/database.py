"""
Database management utilities
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class DatabaseManager:
    """Simple JSON-based database manager (can be replaced with MongoDB later)"""
    
    def __init__(self, db_file: str = "data/database.json"):
        self.db_file = Path(db_file)
        self.db_file.parent.mkdir(exist_ok=True)
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        if self.db_file.exists():
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"[DB ERROR] Không thể đọc file {self.db_file}")
                return {}
        return {}
    
    def _save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[DB ERROR] Không thể ghi file {self.db_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set value by key"""
        self.data[key] = value
        self._save_data()
    
    def delete(self, key: str):
        """Delete key"""
        if key in self.data:
            del self.data[key]
            self._save_data()
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self.data
    
    def get_all(self) -> Dict[str, Any]:
        """Get all data"""
        return self.data.copy()
    
    def clear(self):
        """Clear all data"""
        self.data.clear()
        self._save_data()
    
    # Tour-specific methods
    def get_station(self, station_id: int) -> Optional[Dict[str, Any]]:
        """Get station by ID"""
        return self.get(f"station_{station_id}")
    
    def set_station(self, station_id: int, data: Dict[str, Any]):
        """Set station data"""
        self.set(f"station_{station_id}", data)
    
    def get_team(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Get team by name"""
        return self.get(f"team_{team_name}")
    
    def set_team(self, team_name: str, data: Dict[str, Any]):
        """Set team data"""
        self.set(f"team_{team_name}", data)
    
    def delete_team(self, team_name: str):
        """Delete team"""
        self.delete(f"team_{team_name}")
    
    def get_all_stations(self) -> Dict[int, Dict[str, Any]]:
        """Get all stations"""
        stations = {}
        for key, value in self.data.items():
            if key.startswith("station_"):
                station_id = int(key.split("_")[1])
                stations[station_id] = value
        return stations
    
    def get_all_teams(self) -> Dict[str, Dict[str, Any]]:
        """Get all teams"""
        teams = {}
        for key, value in self.data.items():
            if key.startswith("team_"):
                team_name = key.split("_", 1)[1]
                teams[team_name] = value
        return teams


# Global database instance
db = DatabaseManager()

