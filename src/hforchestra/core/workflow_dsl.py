from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class WorkflowStep:
    task: str
    params: Dict[str, Any]


def parse_workflow(text: str) -> List[WorkflowStep]:
    """Tiny DSL: lines of 'task key=value key=value'."""
    steps: List[WorkflowStep] = []
    if not text:
        return steps
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        task = parts[0]
        params: Dict[str, Any] = {}
        for token in parts[1:]:
            if '=' in token:
                k, v = token.split('=', 1)
                params[k.strip()] = v.strip()
        steps.append(WorkflowStep(task=task, params=params))
    return steps


