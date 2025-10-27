"""
Ramp-up Time Metric Implementation
Evaluates how easy it is for developers to get started with a model or dataset.
Score based on documentation quality, examples, installation instructions, and usability factors.
"""
from __future__ import annotations
import time
import re
import tempfile
from pathlib import Path
from typing import List, Dict, Set, Tuple
from huggingface_hub import snapshot_download
from acemcli.models import MetricResult, Category
from acemcli.metrics.base import register
import logging

logger = logging.getLogger(__name__)


class RampUpTimeMetric:
    """
    Metric that evaluates how easy it is for developers to get started with a model or dataset.
    
    Score [0,1] based on:
    - Quality and completeness of documentation
    - Presence of code examples and tutorials
    - Installation and setup instructions
    - API usage examples
    - Quick start guides
    - Error handling and troubleshooting info
    - Community support indicators
    """
    
    name = "ramp_up_time"
    
    def supports(self, url: str, category: Category) -> bool:
        """Check if this metric supports the given URL and category."""
        return url.startswith("https://huggingface.co/") and category in ("MODEL", "DATASET")
    
    def compute(self, url: str, category: Category) -> MetricResult:
        """Compute the ramp-up time score for the given repository."""
        start_time = time.perf_counter()
        
        try:
            # Extract namespace and repo name from URL
            url_parts = url.rstrip("/").split("/")
            if len(url_parts) >= 2:
                namespace, repo = url_parts[-2:]
            else:
                namespace, repo = url_parts[-1], "unknown"
            
            repo_id = f"{namespace}/{repo}" if repo != "unknown" else namespace
            
            logger.info(f"Computing ramp-up time score for {repo_id}")
            
            # Download repository for analysis
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_dir = snapshot_download(
                    repo_id=repo_id,
                    local_dir=tmp_dir,
                    local_dir_use_symlinks=False
                )
                
                ramp_up_score = self._analyze_ramp_up_factors(Path(local_dir), category)
                
        except Exception as e:
            logger.error(f"Error computing ramp-up time score for {url}: {e}")
            ramp_up_score = 0.0
            namespace, repo = "unknown", "unknown"
            repo_id = f"{namespace}/{repo}"
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Return a complete MetricResult object
        return MetricResult(
            name=repo_id,
            category=category,
            net_score=0.0,  # Will be calculated by orchestrator
            net_score_latency=0,
            ramp_up_time=ramp_up_score,
            ramp_up_time_latency=latency_ms,
            bus_factor=0.0,  # Not calculated by this metric
            bus_factor_latency=0,
            performance_claims=0.0,  # Not calculated by this metric
            performance_claims_latency=0,
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
    
    def _analyze_ramp_up_factors(self, repo_path: Path, category: Category) -> float:
        """Analyze the repository for factors that affect ramp-up time."""
        score_components = {
            'documentation_quality': 0.0,
            'examples_and_tutorials': 0.0,
            'installation_instructions': 0.0,
            'api_examples': 0.0,
            'quick_start_guide': 0.0,
            'troubleshooting_info': 0.0,
            'community_support': 0.0
        }
        
        # Get all files in the repository
        all_files = [f for f in repo_path.rglob("*") if f.is_file()]
        
        # Analyze different aspects of ramp-up experience
        score_components['documentation_quality'] = self._analyze_documentation_quality(all_files)
        score_components['examples_and_tutorials'] = self._analyze_examples_and_tutorials(all_files)
        score_components['installation_instructions'] = self._analyze_installation_instructions(all_files)
        score_components['api_examples'] = self._analyze_api_examples(all_files, category)
        score_components['quick_start_guide'] = self._analyze_quick_start_guide(all_files)
        score_components['troubleshooting_info'] = self._analyze_troubleshooting_info(all_files)
        score_components['community_support'] = self._analyze_community_support(all_files)
        
        # Calculate weighted final score
        weights = {
            'documentation_quality': 0.25,
            'examples_and_tutorials': 0.20,
            'installation_instructions': 0.15,
            'api_examples': 0.15,
            'quick_start_guide': 0.10,
            'troubleshooting_info': 0.10,
            'community_support': 0.05
        }
        
        final_score = sum(
            score_components[component] * weights[component]
            for component in score_components
        )
        
        logger.debug(f"Ramp-up time score components: {score_components}")
        logger.debug(f"Final ramp-up time score: {final_score}")
        
        return min(1.0, max(0.0, final_score))
    
    def _analyze_documentation_quality(self, files: List[Path]) -> float:
        """Analyze the quality and completeness of documentation."""
        score = 0.0
        
        # Find documentation files
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        if not doc_files:
            return 0.0
        
        # Read main README file
        main_readme = None
        for doc_file in doc_files:
            if 'readme' in doc_file.name.lower():
                main_readme = doc_file
                break
        
        if not main_readme and doc_files:
            main_readme = doc_files[0]  # Use first doc file if no README
        
        if main_readme:
            try:
                content = main_readme.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for essential documentation sections
                essential_sections = [
                    'description', 'overview', 'about', 'what is',
                    'usage', 'how to use', 'getting started', 'quick start',
                    'examples', 'demo', 'sample',
                    'requirements', 'dependencies', 'installation',
                    'api', 'interface', 'parameters', 'configuration'
                ]
                
                found_sections = sum(1 for section in essential_sections if section in content_lower)
                section_score = min(0.4, found_sections * 0.05)
                score += section_score
                
                # Check for code blocks (indicates practical examples)
                code_blocks = len(re.findall(r'```', content))
                if code_blocks > 0:
                    score += min(0.2, code_blocks * 0.02)
                
                # Check for links to external resources
                links = len(re.findall(r'https?://', content))
                if links > 0:
                    score += min(0.1, links * 0.01)
                
                # Check for structured formatting (headers, lists, etc.)
                headers = len(re.findall(r'^#+', content, re.MULTILINE))
                lists = len(re.findall(r'^\s*[-*+]', content, re.MULTILINE))
                if headers > 3 or lists > 5:
                    score += 0.1
                
                # Length bonus for substantial documentation
                if len(content) > 1000:
                    score += 0.2
                    
            except Exception:
                pass
        
        return min(1.0, score)
    
    def _analyze_examples_and_tutorials(self, files: List[Path]) -> float:
        """Analyze presence of examples and tutorials."""
        score = 0.0
        
        # Look for example files and directories
        example_patterns = [
            'example', 'demo', 'sample', 'tutorial', 'notebook',
            'test', 'example_', 'demo_', 'sample_'
        ]
        
        example_files = [
            f for f in files
            if any(pattern in f.name.lower() for pattern in example_patterns)
            and f.suffix in {'.py', '.ipynb', '.md', '.txt', '.json', '.yaml', '.yml'}
        ]
        
        if example_files:
            score += 0.4  # Base score for having examples
            
            # Analyze example quality
            python_examples = [f for f in example_files if f.suffix == '.py']
            notebook_examples = [f for f in example_files if f.suffix == '.ipynb']
            
            if python_examples:
                score += 0.2  # Python examples are very valuable
            if notebook_examples:
                score += 0.2  # Jupyter notebooks are excellent for learning
            
            # Check for example diversity
            unique_example_types = set()
            for f in example_files:
                if 'basic' in f.name.lower() or 'simple' in f.name.lower():
                    unique_example_types.add('basic')
                if 'advanced' in f.name.lower() or 'complex' in f.name.lower():
                    unique_example_types.add('advanced')
                if 'api' in f.name.lower() or 'usage' in f.name.lower():
                    unique_example_types.add('api')
            
            score += len(unique_example_types) * 0.1
        
        return min(1.0, score)
    
    def _analyze_installation_instructions(self, files: List[Path]) -> float:
        """Analyze installation and setup instructions."""
        score = 0.0
        
        # Look for installation-related files
        install_files = [
            f for f in files
            if f.name.lower() in {'requirements.txt', 'setup.py', 'pyproject.toml', 
                                'environment.yml', 'conda.yml', 'dockerfile', 'docker-compose.yml'}
        ]
        
        if install_files:
            score += 0.3  # Base score for having installation files
        
        # Check documentation for installation instructions
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        install_keywords = [
            'install', 'setup', 'requirements', 'dependencies',
            'pip install', 'conda install', 'docker', 'environment',
            'getting started', 'quick start'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Count installation-related keywords
                install_mentions = sum(1 for keyword in install_keywords if keyword in content_lower)
                if install_mentions > 0:
                    score += min(0.4, install_mentions * 0.08)
                
                # Look for installation code blocks
                install_code_blocks = len(re.findall(r'```(?:bash|shell|sh).*?install.*?```', content, re.DOTALL | re.IGNORECASE))
                if install_code_blocks > 0:
                    score += min(0.2, install_code_blocks * 0.1)
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _analyze_api_examples(self, files: List[Path], category: Category) -> float:
        """Analyze API usage examples specific to the category."""
        score = 0.0
        
        # Look for API-related files and content
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        if category == "MODEL":
            api_keywords = [
                'model', 'load', 'predict', 'inference', 'forward',
                'tokenizer', 'pipeline', 'transformers', 'torch',
                'tensorflow', 'keras', 'from_pretrained'
            ]
        elif category == "DATASET":
            api_keywords = [
                'dataset', 'load_dataset', 'data', 'train', 'test',
                'split', 'features', 'map', 'filter', 'download'
            ]
        else:
            api_keywords = ['api', 'usage', 'example', 'code']
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Count API-related keywords
                api_mentions = sum(1 for keyword in api_keywords if keyword in content_lower)
                if api_mentions > 3:  # Need substantial API documentation
                    score += min(0.5, api_mentions * 0.05)
                
                # Look for code examples with API usage
                code_blocks = re.findall(r'```(?:python|py).*?```', content, re.DOTALL | re.IGNORECASE)
                api_code_blocks = 0
                
                for code_block in code_blocks:
                    code_lower = code_block.lower()
                    if any(keyword in code_lower for keyword in api_keywords):
                        api_code_blocks += 1
                
                if api_code_blocks > 0:
                    score += min(0.3, api_code_blocks * 0.1)
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _analyze_quick_start_guide(self, files: List[Path]) -> float:
        """Analyze presence of quick start guides."""
        score = 0.0
        
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        quick_start_indicators = [
            'quick start', 'getting started', '5 minute', 'hello world',
            'basic usage', 'simple example', 'first steps', 'minimal example'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for quick start indicators
                quick_start_found = any(indicator in content_lower for indicator in quick_start_indicators)
                if quick_start_found:
                    score += 0.3
                
                # Look for numbered steps or tutorial format
                numbered_steps = len(re.findall(r'^\s*\d+\.', content, re.MULTILINE))
                if numbered_steps >= 3:
                    score += 0.2
                
                # Check for "hello world" or minimal examples
                if 'hello' in content_lower and 'world' in content_lower:
                    score += 0.2
                
                # Look for step-by-step tutorials
                if 'step' in content_lower and ('1' in content or 'first' in content_lower):
                    score += 0.3
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _analyze_troubleshooting_info(self, files: List[Path]) -> float:
        """Analyze troubleshooting and error handling information."""
        score = 0.0
        
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        troubleshooting_keywords = [
            'troubleshoot', 'troubleshooting', 'faq', 'frequently asked',
            'common issues', 'problems', 'errors', 'debug', 'debugging',
            'known issues', 'limitations', 'caveats', 'notes'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for troubleshooting sections
                troubleshooting_found = any(keyword in content_lower for keyword in troubleshooting_keywords)
                if troubleshooting_found:
                    score += 0.4
                
                # Look for FAQ format
                faq_indicators = len(re.findall(r'q:|a:|question|answer', content_lower))
                if faq_indicators >= 4:
                    score += 0.3
                
                # Check for error message examples
                error_examples = len(re.findall(r'error|exception|traceback|failed', content_lower))
                if error_examples >= 3:
                    score += 0.2
                
                # Look for solutions or fixes
                solution_keywords = ['solution', 'fix', 'workaround', 'resolve', 'solve']
                solutions_found = any(keyword in content_lower for keyword in solution_keywords)
                if solutions_found:
                    score += 0.1
                    
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _analyze_community_support(self, files: List[Path]) -> float:
        """Analyze community support indicators."""
        score = 0.0
        
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        community_indicators = [
            'discussions', 'issues', 'github', 'community', 'support',
            'help', 'contact', 'discord', 'slack', 'forum', 'gitter',
            'contributing', 'contribute', 'pull request', 'pr'
        ]
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Check for community support mentions
                community_mentions = sum(1 for indicator in community_indicators if indicator in content_lower)
                if community_mentions > 0:
                    score += min(0.5, community_mentions * 0.1)
                
                # Look for contribution guidelines
                contrib_keywords = ['contributing', 'contribute', 'pull request', 'development']
                contrib_found = any(keyword in content_lower for keyword in contrib_keywords)
                if contrib_found:
                    score += 0.3
                
                # Check for badges or links to community platforms
                badges = len(re.findall(r'https?://.*?(?:github|discord|slack|gitter)', content_lower))
                if badges > 0:
                    score += min(0.2, badges * 0.1)
                    
            except Exception:
                continue
        
        return min(1.0, score)


# Register the metric
register(RampUpTimeMetric())
