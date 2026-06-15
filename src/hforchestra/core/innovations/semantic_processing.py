"""
Semantic Processing System
Uses LangExtract for deep semantic understanding and meaning-based processing.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import re
from dataclasses import dataclass
import logging
import textwrap
from datetime import datetime

# Remove module-level langextract import to prevent early initialization
# LANGEXTRACT_AVAILABLE will be checked when needed

logger = logging.getLogger(__name__)

@dataclass
class SemanticConcept:
    """Represents a semantic concept extracted from content."""
    concept: str
    meaning: str
    related_concepts: List[str]
    context: Dict[str, Any]
    confidence: float
    source_location: str
    extraction_method: str

@dataclass
class SemanticRelation:
    """Represents a semantic relationship between concepts."""
    source_concept: str
    target_concept: str
    relation_type: str
    strength: float
    evidence: List[str]
    context: Dict[str, Any]

@dataclass
class SemanticAnalysisResult:
    """Result of semantic analysis."""
    concepts: List[SemanticConcept]
    relations: List[SemanticRelation]
    success: bool
    processing_time_ms: float
    error_message: Optional[str] = None

@dataclass
class SemanticMatchResult:
    matches: List[Dict[str, Any]]
    score: float
    error_message: Optional[str] = None

class SemanticProcessor:
    """Core system for semantic understanding using LangExtract."""
    
    def __init__(self):
        self.semantic_graph: Dict[str, Dict[str, Any]] = {}
        self.concept_history: List[SemanticConcept] = []
        self._lang_extract_available = None
        self.semantic_cache: Dict[str, Any] = {}
    
    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
                logger.info("LangExtract available for semantic processing")
            except ImportError:
                self._lang_extract_available = False
                logger.warning("LangExtract not available. Install with: pip install langextract")
        return self._lang_extract_available

    async def analyze_semantics(self, content: str, context: Dict[str, Any] = None) -> SemanticAnalysisResult:
        """Perform deep semantic analysis of content."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for semantic analysis")

            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            # Create semantic analysis prompt
            analysis_prompt = f"""
            Perform deep semantic analysis of the following content.
            Extract:
            1. Core concepts and their meanings
            2. Relationships between concepts
            3. Contextual implications
            4. Semantic dependencies
            5. Domain-specific terminology
            
            Context information:
            {self._format_context(context) if context else 'No additional context provided'}
            
            Content to analyze:
            {content}
            """

            # Define examples for semantic extraction using proper LangExtract format
            examples = [
                lx.data.ExampleData(
                    text="The system processes data streams in real-time",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="semantic_concept",
                            extraction_text="data stream processing",
                            attributes={
                                "meaning": "Processing of continuous data streams",
                                "related_concepts": ["real-time processing", "data processing"],
                                "confidence": 0.9
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="semantic_concept",
                            extraction_text="real-time processing",
                            attributes={
                                "meaning": "Processing data as it arrives",
                                "related_concepts": ["data stream processing", "streaming"],
                                "confidence": 0.8
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="semantic_relation",
                            extraction_text="system -> data",
                            attributes={
                                "source": "system",
                                "target": "data",
                                "relation_type": "processes",
                                "confidence": 0.9
                            }
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="The AI model learns from training data",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="semantic_concept",
                            extraction_text="AI model",
                            attributes={
                                "meaning": "Artificial intelligence model",
                                "related_concepts": ["machine learning", "neural network"],
                                "confidence": 0.9
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="semantic_concept",
                            extraction_text="training data",
                            attributes={
                                "meaning": "Data used to train machine learning models",
                                "related_concepts": ["dataset", "learning"],
                                "confidence": 0.8
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="semantic_relation",
                            extraction_text="AI model -> training data",
                            attributes={
                                "source": "AI model",
                                "target": "training data",
                                "relation_type": "learns from",
                                "confidence": 0.9
                            }
                        )
                    ]
                )
            ]

            # Use the wrapper for consistent configuration
            result = extract_with_config(
                lx,
                text_or_documents=content,
                prompt_description=analysis_prompt,
                examples=examples
            )

            # Process semantic extractions
            concepts = []
            relations = []
            
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class'):
                        if extraction.extraction_class == "semantic_concept":
                            concept = self._create_semantic_concept(extraction)
                            if concept:
                                concepts.append(concept)
                                self._update_semantic_graph(concept)
                        elif extraction.extraction_class == "semantic_relation":
                            relation = self._create_semantic_relation(extraction)
                            if relation:
                                relations.append(relation)
                                self._update_semantic_graph_relations(relation)

            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return SemanticAnalysisResult(
                concepts=concepts,
                relations=relations,
                success=True,
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Error in semantic analysis: {e}")
            return SemanticAnalysisResult(
                concepts=[],
                relations=[],
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    async def find_semantic_matches(self, query: str, threshold: float = 0.7) -> List[SemanticConcept]:
        """Find semantically matching concepts."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for semantic matching")

            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            # Create semantic matching prompt
            matching_prompt = textwrap.dedent(f"""
            Find semantic matches for the query:
            {query}
            
            Consider:
            1. Direct meaning matches
            2. Synonymous concepts
            3. Related terminology
            4. Domain-specific equivalents
            5. Contextual similarities
            """)

            examples = [
                lx.data.ExampleData(
                    text="Query: 'car'\nCandidates: - 'automobile'\n- 'tree'",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="match",
                            extraction_text="automobile",
                            attributes={"score": 0.9, "reason": "synonym"}
                        ),
                        lx.data.Extraction(
                            extraction_class="match",
                            extraction_text="tree",
                            attributes={"score": 0.1, "reason": "unrelated"}
                        )
                    ]
                )
            ]
            
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")

            import io, contextlib
            buf_out, buf_err = io.StringIO(), io.StringIO()
            # Silence legacy announce prints
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                result = extract_with_config(
                    lx,
                    text_or_documents=query,
                    prompt_description=matching_prompt,
                    examples=examples,
                    override_api_key=lx_api_key
                )

            # Process matches
            matches = []
            for concept in self.concept_history:
                match_score = self._calculate_semantic_similarity(
                    query,
                    concept.concept,
                    result
                )
                if match_score >= threshold:
                    matches.append(concept)

            return sorted(matches, key=lambda x: x.confidence, reverse=True)

        except Exception as e:
            logger.error(f"Error finding semantic matches: {e}")
            return []

    async def analyze_semantic_coverage(self, domain: str) -> Dict[str, Any]:
        """Analyze semantic coverage of a domain."""
        try:
            # Get domain concepts
            domain_concepts = self._get_domain_concepts(domain)
            
            # Analyze coverage
            total_concepts = len(domain_concepts)
            covered_concepts = len(self.semantic_graph)
            
            # Calculate coverage metrics
            coverage = {
                'total_concepts': total_concepts,
                'covered_concepts': covered_concepts,
                'coverage_ratio': covered_concepts / total_concepts if total_concepts > 0 else 0,
                'missing_concepts': list(domain_concepts - set(self.semantic_graph.keys())),
                'strong_concepts': self._get_strong_concepts(),
                'weak_concepts': self._get_weak_concepts()
            }
            
            return coverage

        except Exception as e:
            logger.error(f"Error analyzing semantic coverage: {e}")
            return {}

    async def extract_key_concepts(self, 
                                   text: str,
                                   num_concepts: int = 5) -> List[str]:
        """Extract key concepts from text using LangExtract."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for concept extraction")
            
            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            extraction_prompt = textwrap.dedent(f"""
            Extract up to {num_concepts} key concepts from the following text. List them as a comma-separated string.

            Text:
            {text}
            """)
            
            examples = [
                lx.data.ExampleData(
                    text="The quick brown fox jumps over the lazy dog, emphasizing its agility.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="key_concepts",
                            extraction_text="fox, dog, agility",
                            attributes={}
                        )
                    ]
                )
            ]

            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")

            import io, contextlib
            buf_out, buf_err = io.StringIO(), io.StringIO()
            # Silence legacy announce prints
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                result = extract_with_config(
                    lx,
                    text_or_documents=text,
                    prompt_description=extraction_prompt,
                    examples=examples,
                    override_api_key=lx_api_key
                )

            if result and result.extractions:
                for extraction in result.extractions:
                    if extraction.extraction_class == "key_concepts":
                        return [c.strip() for c in extraction.extraction_text.split(',') if c.strip()]
            return []

        except Exception as e:
            logger.error(f"Error extracting key concepts: {e}")
            return []

    def get_semantic_graph(self) -> Dict[str, Any]:
        """Get the current semantic graph."""
        return self.semantic_graph

    def _create_semantic_concept(self, extraction: Any) -> Optional[SemanticConcept]:
        """Create semantic concept from extraction."""
        try:
            attrs = extraction.attributes if extraction.attributes else {}
            concept = SemanticConcept(
                concept=extraction.extraction_text,
                meaning=attrs.get("meaning", ""),
                related_concepts=attrs.get("related_concepts", []),
                context=attrs,
                confidence=attrs.get("confidence", 0.0),
                source_location=attrs.get("location", "unknown"),
                extraction_method="langextract"
            )
            self.concept_history.append(concept)
            return concept
        except Exception as e:
            logger.error(f"Error creating semantic concept: {e}")
            return None

    def _create_semantic_relation(self, extraction: Any) -> Optional[SemanticRelation]:
        """Create semantic relation from extraction."""
        try:
            attrs = extraction.attributes if getattr(extraction, 'attributes', None) else {}
            text = getattr(extraction, 'extraction_text', '') or ''

            # Prefer explicitly provided attributes
            explicit_source = attrs.get('source')
            explicit_target = attrs.get('target')
            explicit_type = attrs.get('relation_type')

            if explicit_source and explicit_target:
                source = str(explicit_source).strip()
                target = str(explicit_target).strip()
                relation_type = str(explicit_type).strip() if explicit_type else 'related_to'
            else:
                # Try multiple separators: ->, →, ⇒, =>, etc.
                parts = re.split(r"\s*(?:->|→|⇒|=>)\s*", text)
                if len(parts) >= 2:
                    source = parts[0].strip()
                    target = parts[-1].strip()
                    between = "->".join(parts[1:-1]).strip()
                    relation_type = explicit_type or (between if between else 'related_to')
                else:
                    # Try common natural language connectors e.g., "analysis of text"
                    m = re.match(r"\s*(?P<src>.+?)\s*(?P<sep>of|to|in|on|about|:|—|-|–)\s*(?P<tgt>.+)", text, flags=re.IGNORECASE)
                    if m:
                        source = m.group('src').strip()
                        target = m.group('tgt').strip()
                        relation_type = explicit_type or m.group('sep').lower()
                    else:
                        # No parsable relation; stop quietly to avoid noisy warnings
                        return None
            return SemanticRelation(
                source_concept=source,
                target_concept=target,
                relation_type=relation_type,
                strength=attrs.get("strength", 0.0),
                evidence=[text] if text else [],
                context=attrs
            )
        except Exception as e:
            logger.error(f"Error creating semantic relation: {e}")
            return None

    def _update_semantic_graph(self, concept: SemanticConcept) -> None:
        """Update semantic graph with new concept."""
        self.semantic_graph[concept.concept] = {
            'meaning': concept.meaning,
            'related': concept.related_concepts,
            'confidence': concept.confidence,
            'context': concept.context
        }

    def _update_semantic_graph_relations(self, relation: SemanticRelation) -> None:
        """Update semantic graph with new relation."""
        if relation.source_concept in self.semantic_graph:
            if 'relations' not in self.semantic_graph[relation.source_concept]:
                self.semantic_graph[relation.source_concept]['relations'] = []
            self.semantic_graph[relation.source_concept]['relations'].append({
                'target': relation.target_concept,
                'type': relation.relation_type,
                'strength': relation.strength
            })

    def _calculate_semantic_similarity(self, query: str, concept: str, 
                                    extraction_result: Any) -> float:
        """Calculate semantic similarity score."""
        # Implementation would go here
        pass

    def _get_domain_concepts(self, domain: str) -> Set[str]:
        """Get expected concepts for a domain."""
        # Implementation would go here
        pass

    def _get_strong_concepts(self) -> List[str]:
        """Get concepts with high confidence and strong relations."""
        # Implementation would go here
        pass

    def _get_weak_concepts(self) -> List[str]:
        """Get concepts with low confidence or weak relations."""
        # Implementation would go here
        pass

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for prompt."""
        return "\n".join(f"{k}: {v}" for k, v in context.items())
