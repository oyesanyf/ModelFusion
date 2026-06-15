"""
Contextual Understanding Innovation
Provides advanced context analysis and understanding capabilities.
"""

import asyncio
import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from datetime import datetime

# Remove module-level langextract import to prevent early initialization
# LANGEXTRACT_AVAILABLE will be checked when needed

logger = logging.getLogger(__name__)

class ContextualUnderstanding:
    """Advanced contextual understanding and analysis."""
    
    def __init__(self):
        self._lang_extract_available = None
        self.context_cache = {}
        self.related_contexts = []
    
    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
            except ImportError:
                self._lang_extract_available = False
        return self._lang_extract_available

    async def analyze_context(self, content: str, task_type: str = "text-generation") -> Dict[str, Any]:
        """Analyze content for contextual understanding."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for context analysis")
            
            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config
            
            # Prepare analysis prompt
            analysis_prompt = f"""
            Analyze the following content for contextual understanding:
            
            Content: {content}
            Task Type: {task_type}
            
            Extract:
            1. Key themes and topics
            2. Sentiment and tone
            3. Contextual relationships
            4. Domain-specific terminology
            5. Cultural or temporal context
            """
            
            # Define examples for better extraction using proper LangExtract format
            examples = [
                lx.data.ExampleData(
                    text="The stock market reached new highs today",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="themes",
                            extraction_text="finance, markets, economics",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="sentiment",
                            extraction_text="positive",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="relationships",
                            extraction_text="market performance, economic indicators",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="terminology",
                            extraction_text="stock market, new highs",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="context",
                            extraction_text="financial news",
                            attributes={}
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="The AI model achieved 95% accuracy",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="themes",
                            extraction_text="artificial intelligence, technology, performance",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="sentiment",
                            extraction_text="positive",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="relationships",
                            extraction_text="model evaluation, accuracy metrics",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="terminology",
                            extraction_text="AI model, accuracy",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="context",
                            extraction_text="technical evaluation",
                            attributes={}
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
            
            return self._extract_context_analysis(result)
            
        except Exception as e:
            logger.error(f"Error in context analysis: {e}")
            return {
                'themes': [],
                'sentiment': 'neutral',
                'relationships': [],
                'terminology': [],
                'context': 'general'
            }

    def _extract_context_analysis(self, result: Any) -> Dict[str, Any]:
        """Extract context analysis from LangExtract result."""
        try:
            if hasattr(result, 'extractions') and result.extractions:
                # Extract information from result
                themes = []
                sentiment = 'neutral'
                relationships = []
                terminology = []
                context = 'general'
                
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class'):
                        if extraction.extraction_class == 'themes':
                            themes = extraction.extraction_text.split(', ') if extraction.extraction_text else []
                        elif extraction.extraction_class == 'sentiment':
                            sentiment = extraction.extraction_text
                        elif extraction.extraction_class == 'relationships':
                            relationships = extraction.extraction_text.split(', ') if extraction.extraction_text else []
                        elif extraction.extraction_class == 'terminology':
                            terminology = extraction.extraction_text.split(', ') if extraction.extraction_text else []
                        elif extraction.extraction_class == 'context':
                            context = extraction.extraction_text
                
                return {
                    'themes': themes,
                    'sentiment': sentiment,
                    'relationships': relationships,
                    'terminology': terminology,
                    'context': context
                }
            else:
                return {
                    'themes': [],
                    'sentiment': 'neutral',
                    'relationships': [],
                    'terminology': [],
                    'context': 'general'
                }
        except Exception as e:
            logger.error(f"Error extracting context analysis: {e}")
            return {
                'themes': [],
                'sentiment': 'neutral',
                'relationships': [],
                'terminology': [],
                'context': 'general'
            }

    async def analyze_workspace_context(self, workspace_path: Path) -> Dict[str, Any]:
        """Analyze entire workspace for contextual understanding."""
        try:
            # Gather workspace content
            workspace_content = await self._gather_workspace_content(workspace_path)
            
            # Analyze each content piece
            context_results = []
            for file_path, content in workspace_content.items():
                if content:  # Only analyze if content exists
                    result = await self.analyze_context(
                        content,
                        task_type=self._determine_context_type(file_path)
                    )
                    context_results.append(result)

            # Merge insights
            merged_insights = self._merge_workspace_insights(context_results)
            
            return {
                'insights': merged_insights,
                'success': True,
                'processing_time_ms': 0  # Simplified for now
            }

        except Exception as e:
            logger.error(f"Error analyzing workspace context: {e}")
            return {
                'insights': [],
                'success': False,
                'processing_time_ms': 0,
                'error_message': str(e)
            }

    def get_historical_context(self, context_type: str = None) -> List[Dict[str, Any]]:
        """Get historical context insights."""
        # Simplified implementation
        return []

    def _extract_related_contexts(self, result: Any) -> List[str]:
        """Extract related contexts from LangExtract result."""
        if not result or not hasattr(result, 'extractions'):
            return []
            
        contexts = []
        for extraction in result.extractions:
            if isinstance(extraction, dict):
                contexts.extend(extraction.get('related_contexts', []))
        return contexts

    def _determine_context_type(self, file_path: str) -> str:
        """Determine context type from file path."""
        ext = Path(file_path).suffix.lower()
        context_types = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json'
        }
        return context_types.get(ext, 'unknown')

    async def _gather_workspace_content(self, workspace_path: Path) -> Dict[str, str]:
        """Gather content from workspace files."""
        content_dict = {}
        try:
            if workspace_path.is_file():
                content = await self._read_file_content(workspace_path)
                if content:
                    content_dict[str(workspace_path)] = content
            elif workspace_path.is_dir():
                for path in workspace_path.rglob('*'):
                    if path.is_file() and not path.name.startswith('.'):
                        content = await self._read_file_content(path)
                        if content:
                            content_dict[str(path)] = content
        except Exception as e:
            logger.error(f"Error gathering workspace content: {e}")
        return content_dict

    async def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read content from a file."""
        try:
            # Simplified implementation without aiofiles dependency
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def _merge_workspace_insights(self, context_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge workspace insights from multiple files."""
        merged = []
        for result in context_results:
            if isinstance(result, dict) and result.get('themes'):
                merged.append(result)
        return merged