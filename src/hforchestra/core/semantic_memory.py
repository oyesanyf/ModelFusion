import json
import os
from typing import Dict, Any, List
from datetime import datetime


class SemanticMemory:
    def __init__(self, path: str = "db/semantic_memory.json"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"sessions": []}
        return {"sessions": []}

    def save(self) -> None:
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def add_session(self, session_id: str, context: Dict[str, Any]) -> None:
        self._data.setdefault("sessions", []).append({
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "context": context,
        })
        self.save()

    def get_recent_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        sessions = self._data.get("sessions", [])
        return sessions[-limit:]


