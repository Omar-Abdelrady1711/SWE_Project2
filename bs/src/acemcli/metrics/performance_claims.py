"""
Performance Claims Metric Implementation
Evaluates presence of benchmarks or evidence for claimed performance metrics.
"""
from __future__ import annotations
import time
import re
import tempfile
from pathlib import Path
from typing import List, Dict, Set
from huggingface_hub import snapshot_download
from acemcli.models import MetricResult, Category
from acemcli.metrics.base import register
import logging

logger = logging.getLogger(__name__)


class PerformanceClaimsMetric:
    """
    Metric that evaluates the presence and quality of performance claims,
    benchmarks, and supporting evidence for ML models.
    
    Score [0,1] based on:
    - Presence of benchmark results
    - Quality of performance documentation  
    - Comparison tables with other models
    - Evaluation metrics and test results
    - Credibility of performance claims
    """
    
    name = "performance_claims"
    
    def supports(self, url: str, category: Category) -> bool:
        """Check if this metric supports the given URL and category."""
        return url.startswith("https://huggingface.co/") and category == "MODEL"
    
    def compute(self, url: str, category: Category) -> MetricResult:
        """Compute the performance claims score for the given repository."""
        start_time = time.perf_counter()
        
        try:
            # Extract namespace and repo name from URL
            url_parts = url.rstrip("/").split("/")
            if len(url_parts) >= 2:
                namespace, repo = url_parts[-2:]
            else:
                namespace, repo = url_parts[-1], "unknown"
            
            repo_id = f"{namespace}/{repo}" if repo != "unknown" else namespace
            
            logger.info(f"Computing performance claims score for {repo_id}")
            
            # Download repository for analysis
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_dir = snapshot_download(
                    repo_id=repo_id,
                    local_dir=tmp_dir,
                    local_dir_use_symlinks=False
                )
                
                performance_claims_score = self._analyze_performance_claims(Path(local_dir))
                
        except Exception as e:
            logger.error(f"Error computing performance claims score for {url}: {e}")
            performance_claims_score = 0.0
            namespace, repo = "unknown", "unknown"
            repo_id = f"{namespace}/{repo}"
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Return a complete MetricResult object
        return MetricResult(
            name=repo_id,
            category=category,
            net_score=0.0,  # Will be calculated by orchestrator
            net_score_latency=0,
            ramp_up_time=0.0,  # Not calculated by this metric
            ramp_up_time_latency=0,
            bus_factor=0.0,  # Not calculated by this metric
            bus_factor_latency=0,
            performance_claims=performance_claims_score,
            performance_claims_latency=latency_ms,
            license=0.0,  # Not calculated by this metric
            license_latency=0,
            size_score={"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
            size_score_latency=0,
            dataset_and_code_score=0.0,  # Not calculated by this metric
            dataset_and_code_score_latency=0,
            dataset_quality=0.0,  # Not calculated by this metric
            dataset_quality_latency=0,
            code_quality=0.0,  # Not calculated by this metric
            code_quality_latency=0,
        )
    
    def _analyze_performance_claims(self, repo_path: Path) -> float:
        """Analyze the repository for performance claims and supporting evidence."""
        score_components = {
            'benchmark_results': 0.0,
            'evaluation_metrics': 0.0,
            'comparison_tables': 0.0,
            'performance_documentation': 0.0,
            'credibility_indicators': 0.0
        }
        
        # Get all files in the repository
        all_files = [f for f in repo_path.rglob("*") if f.is_file()]
        
        # Analyze different aspects of performance claims
        score_components['benchmark_results'] = self._analyze_benchmark_results(all_files)
        score_components['evaluation_metrics'] = self._analyze_evaluation_metrics(all_files)
        score_components['comparison_tables'] = self._analyze_comparison_tables(all_files)
        score_components['performance_documentation'] = self._analyze_performance_docs(all_files)
        score_components['credibility_indicators'] = self._analyze_credibility(all_files)
        
        # Calculate weighted final score
        weights = {
            'benchmark_results': 0.30,
            'evaluation_metrics': 0.25,
            'comparison_tables': 0.20,
            'performance_documentation': 0.15,
            'credibility_indicators': 0.10
        }
        
        final_score = sum(
            score_components[component] * weights[component]
            for component in score_components
        )
        
        logger.debug(f"Performance claims score components: {score_components}")
        logger.debug(f"Final performance claims score: {final_score}")
        
        return min(1.0, max(0.0, final_score))
    
    def _analyze_benchmark_results(self, files: List[Path]) -> float:
        """Analyze for the presence of benchmark results."""
        score = 0.0
        
        # Look for common benchmark/evaluation files
        benchmark_patterns = [
            'benchmark', 'eval', 'results', 'scores', 'metrics',
            'evaluation', 'test_results', 'performance'
        ]
        
        benchmark_files = [
            f for f in files
            if any(pattern in f.name.lower() for pattern in benchmark_patterns)
            and f.suffix in {'.json', '.csv', '.txt', '.md', '.yaml', '.yml'}
        ]
        
        if benchmark_files:
            score += 0.4  # Base score for having benchmark files
            
            # Analyze content of benchmark files
            for file in benchmark_files[:5]:  # Limit analysis to prevent slowdown
                try:
                    content = file.read_text(encoding='utf-8', errors='ignore')
                    if self._has_quantitative_results(content):
                        score += 0.1
                except Exception:
                    continue
        
        return min(1.0, score)
    
    def _has_quantitative_results(self, content: str) -> bool:
        """Check if content contains quantitative performance results."""
        # Look for numerical performance indicators
        patterns = [
            r'\b\d+\.?\d*\s*%',  # Percentages
            r'\b\d+\.?\d*\s*(accuracy|precision|recall|f1|bleu|rouge)',  # Common metrics
            r'\b\d+\.?\d*\s*(fps|ms|seconds)',  # Performance metrics
            r'\b\d+\.?\d*[km]?\s*(flops|params|parameters)',  # Model size metrics
        ]
        
        content_lower = content.lower()
        return any(re.search(pattern, content_lower) for pattern in patterns)
    
    def _analyze_evaluation_metrics(self, files: List[Path]) -> float:
        """Analyze for evaluation metrics and methodologies."""
        score = 0.0
        
        # Read documentation files for evaluation information
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        evaluation_keywords = [
            'accuracy', 'precision', 'recall', 'f1-score', 'bleu', 'rouge',
            'perplexity', 'evaluation', 'benchmark', 'test set', 'validation',
            'metrics', 'performance', 'baseline', 'sota', 'state-of-the-art'
        ]
        
        found_metrics = set()
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                for keyword in evaluation_keywords:
                    if keyword in content_lower:
                        found_metrics.add(keyword)
                        
                # Look for structured evaluation sections
                if re.search(r'#+\s*(evaluation|performance|results|benchmark)', content, re.IGNORECASE):
                    score += 0.2
                    
            except Exception:
                continue
        
        # Score based on variety of metrics mentioned
        if found_metrics:
            metric_variety_score = min(0.5, len(found_metrics) * 0.05)
            score += metric_variety_score
        
        return min(1.0, score)
    
    def _analyze_comparison_tables(self, files: List[Path]) -> float:
        """Analyze for comparison tables with other models."""
        score = 0.0
        
        # Look for files that might contain comparison tables
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst', '.csv'} or 'readme' in f.name.lower()
        ]
        
        comparison_indicators = [
            r'\|\s*model\s*\|', r'\|\s*baseline\s*\|', r'\|\s*method\s*\|',  # Markdown tables
            r'vs\.?\s+\w+', r'compared? to', r'outperforms?',  # Comparison language
            r'better than', r'improvement over', r'beats',
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                
                # Check for comparison indicators
                for pattern in comparison_indicators:
                    if re.search(pattern, content, re.IGNORECASE):
                        score += 0.1
                        
                # Look for table-like structures with numbers
                if self._has_comparison_table(content):
                    score += 0.3
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _has_comparison_table(self, content: str) -> bool:
        """Check if content contains what looks like a comparison table."""
        lines = content.split('\n')
        
        # Look for markdown tables with numerical data
        table_lines = [line for line in lines if '|' in line]
        
        if len(table_lines) >= 3:  # Header, separator, and at least one data row
            # Check if table contains numerical data
            data_lines = table_lines[2:]  # Skip header and separator
            numerical_lines = [
                line for line in data_lines
                if re.search(r'\d+\.?\d*', line)
            ]
            
            return len(numerical_lines) >= 1
        
        return False
    
    def _analyze_performance_docs(self, files: List[Path]) -> float:
        """Analyze quality of performance documentation."""
        score = 0.0
        
        # Read main documentation files
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        performance_sections = [
            'performance', 'benchmark', 'evaluation', 'results',
            'metrics', 'accuracy', 'speed', 'efficiency'
        ]
        
        methodology_indicators = [
            'dataset', 'test set', 'validation', 'cross-validation',
            'methodology', 'experimental setup', 'baseline',
            'hyperparameters', 'training details'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for performance sections
                section_score = sum(
                    0.05 for section in performance_sections
                    if section in content_lower
                )
                score += min(0.3, section_score)
                
                # Check for methodology descriptions
                methodology_score = sum(
                    0.03 for indicator in methodology_indicators
                    if indicator in content_lower
                )
                score += min(0.2, methodology_score)
                
                # Bonus for detailed explanations (longer performance content)
                performance_content = self._extract_performance_content(content)
                if len(performance_content) > 500:  # Substantial performance discussion
                    score += 0.1
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _extract_performance_content(self, content: str) -> str:
        """Extract performance-related content from documentation."""
        lines = content.split('\n')
        performance_lines = []
        
        in_performance_section = False
        
        for line in lines:
            # Check if we're entering a performance section
            if re.search(r'#+\s*(performance|benchmark|evaluation|results)', line, re.IGNORECASE):
                in_performance_section = True
                performance_lines.append(line)
            # Check if we're leaving the section (new header at same or higher level)
            elif in_performance_section and re.match(r'#+\s+', line):
                break
            elif in_performance_section:
                performance_lines.append(line)
        
        return '\n'.join(performance_lines)
    
    def _analyze_credibility(self, files: List[Path]) -> float:
        """Analyze credibility indicators of performance claims."""
        score = 0.0
        
        # Read main documentation
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        credibility_indicators = [
            'citation', 'reference', 'paper', 'arxiv', 'doi',
            'published', 'peer-reviewed', 'conference', 'journal',
            'reproducible', 'code available', 'open source'
        ]
        
        academic_patterns = [
            r'arxiv:\d+\.\d+', r'doi:\S+', r'http[s]?://arxiv\.org',
            r'@\w+\{[^}]+\}',  # BibTeX citations
            r'http[s]?://papers\.\w+', r'http[s]?://proceedings\.\w+'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for credibility keywords
                credibility_score = sum(
                    0.05 for indicator in credibility_indicators
                    if indicator in content_lower
                )
                score += min(0.4, credibility_score)
                
                # Check for academic references
                for pattern in academic_patterns:
                    if re.search(pattern, content):
                        score += 0.1
                        break  # Don't double-count multiple academic references
                
                # Check for reproducibility information
                if 'reproduc' in content_lower:  # reproducible, reproduction, etc.
                    score += 0.1
                    
            except Exception:
                continue
        
        return min(1.0, score)


# Register the metric
register(PerformanceClaimsMetric())
