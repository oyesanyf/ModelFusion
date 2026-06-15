from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class UnifiedResult:
    success: bool
    content: str = ""
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    models_used: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # Back-compat accessors (so legacy prints keep working)
    @property
    def data(self) -> Dict[str, Any]:
        return self.to_dict()


def coerce_unified(result: Any) -> UnifiedResult:
    """Best-effort conversion of arbitrary result objects into UnifiedResult without breaking callers."""
    if isinstance(result, UnifiedResult):
        return result

    # Try to read common attributes
    success = getattr(result, 'success', True)
    content = getattr(result, 'content', '') or ''
    processing_time_ms = float(getattr(result, 'processing_time_ms', 0.0) or 0.0)
    error_message = getattr(result, 'error_message', None)
    models_used = list(getattr(result, 'models_used', []) or [])

    # Dict-style results
    if isinstance(result, dict):
        success = bool(result.get('success', success))
        content = str(result.get('content', content))
        processing_time_ms = float(result.get('processing_time_ms', processing_time_ms) or 0.0)
        error_message = result.get('error_message', error_message)
        models_used = list(result.get('models_used', models_used) or [])
        artifacts = list(result.get('artifacts', []))
        insights = list(result.get('insights', []))
        provenance = list(result.get('provenance', []))
        metadata = dict(result.get('metadata', {}))
        return UnifiedResult(
            success=success,
            content=content,
            processing_time_ms=processing_time_ms,
            error_message=error_message,
            models_used=models_used,
            artifacts=artifacts,
            insights=insights,
            metadata=metadata,
            provenance=provenance,
        )

    # Fallback without extras
    return UnifiedResult(
        success=success,
        content=content,
        processing_time_ms=processing_time_ms,
        error_message=error_message,
        models_used=models_used,
    )


