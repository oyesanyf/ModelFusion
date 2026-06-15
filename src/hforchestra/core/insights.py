from typing import List, Dict, Any


def generate_auto_insights(content: str, analysis: Dict[str, Any], artifacts: List[str]) -> List[str]:
    """Lightweight insight generator: produces short, evidence-linked bullets."""
    insights: List[str] = []
    if not content:
        return insights

    # Example heuristics
    if 'semantic_analysis' in analysis:
        sem = analysis['semantic_analysis']
        if isinstance(sem, dict):
            concepts = sem.get('concepts') or sem.get('concepts_count') or []
            if concepts:
                if isinstance(concepts, list):
                    insights.append(f"Semantic focus on: {', '.join(map(str, concepts[:5]))}")
                else:
                    insights.append(f"Semantic concepts detected: {concepts}")

    if 'temporal_analysis' in analysis:
        temp = analysis['temporal_analysis']
        changes = temp.get('changes', []) if isinstance(temp, dict) else []
        if changes:
            insights.append(f"Detected {len(changes)} temporal change(s)")

    if artifacts:
        first = artifacts[0]
        insights.append(f"See artifact: {first}")

    return insights


