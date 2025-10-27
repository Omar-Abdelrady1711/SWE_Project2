"""
Dataset & Code Score Metric Implementation
Evaluates if datasets and example code are well-documented and linked.
"""
from __future__ import annotations
import time
import re
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from huggingface_hub import snapshot_download
from acemcli.models import MetricResult, Category
from acemcli.metrics.base import register
import logging

logger = logging.getLogger(__name__)


class DatasetAndCodeScoreMetric:
    """
    Metric that evaluates the availability and quality of dataset documentation
    and example code for ML models.
    
    Score [0,1] based on:
    - Presence of dataset documentation
    - Quality of dataset descriptions
    - Availability of example code/scripts
    - Links to training datasets
    - Documentation completeness
    """
    
    name = "dataset_and_code_score"
    
    def supports(self, url: str, category: Category) -> bool:
        """Check if this metric supports the given URL and category."""
        return url.startswith("https://huggingface.co/") and category in ("MODEL", "DATASET")
    
    def compute(self, url: str, category: Category) -> MetricResult:
        """Compute the dataset and code score for the given repository."""
        start_time = time.perf_counter()
        
        try:
            # Extract namespace and repo name from URL
            url_parts = url.rstrip("/").split("/")
            if len(url_parts) >= 2:
                namespace, repo = url_parts[-2:]
            else:
                namespace, repo = url_parts[-1], ""
            
            repo_id = f"{namespace}/{repo}" if repo else namespace
            
            logger.info(f"Computing dataset and code score for {repo_id}")
            
            # Download repository for analysis
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_dir = snapshot_download(
                    repo_id=repo_id,
                    local_dir=tmp_dir,
                    local_dir_use_symlinks=False
                )
                
                dataset_code_score = self._analyze_repository(Path(local_dir), category)
                
        except Exception as e:
            logger.error(f"Error computing dataset and code score for {url}: {e}")
            dataset_code_score = 0.0
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
            performance_claims=0.0,  # Not calculated by this metric
            performance_claims_latency=0,
            license=0.0,  # Not calculated by this metric
            license_latency=0,
            size_score={"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
            size_score_latency=0,
            dataset_and_code_score=dataset_code_score,
            dataset_and_code_score_latency=latency_ms,
            dataset_quality=0.0,  # Not calculated by this metric
            dataset_quality_latency=0,
            code_quality=0.0,  # Not calculated by this metric
            code_quality_latency=0,
        )
    
    def _analyze_repository(self, repo_path: Path, category: Category) -> float:
        """Analyze the repository and compute the dataset and code score."""
        score_components = {
            'readme_quality': 0.0,
            'dataset_documentation': 0.0,
            'example_code': 0.0,
            'dataset_links': 0.0,
            'training_scripts': 0.0
        }
        
        # Get all files in the repository
        all_files = [f for f in repo_path.rglob("*") if f.is_file()]
        
        # Analyze README files
        score_components['readme_quality'] = self._analyze_readme_files(all_files)
        
        # Analyze dataset documentation
        score_components['dataset_documentation'] = self._analyze_dataset_documentation(all_files)
        
        # Analyze example code
        score_components['example_code'] = self._analyze_example_code(all_files)
        
        # Analyze dataset links and references
        score_components['dataset_links'] = self._analyze_dataset_links(all_files)
        
        # Analyze training scripts
        score_components['training_scripts'] = self._analyze_training_scripts(all_files)
        
        # Weight the components based on category
        weights = self._get_weights_for_category(category)
        
        # Calculate weighted score
        final_score = sum(
            score_components[component] * weights[component]
            for component in score_components
        )
        
        logger.debug(f"Score components: {score_components}")
        logger.debug(f"Final score: {final_score}")
        
        return min(1.0, max(0.0, final_score))  # Clamp to [0, 1]
    
    def _analyze_readme_files(self, files: List[Path]) -> float:
        """Analyze README files for dataset and code documentation quality."""
        readme_files = [f for f in files if f.name.lower().startswith('readme')]
        
        if not readme_files:
            return 0.0
        
        total_score = 0.0
        
        for readme_file in readme_files:
            try:
                content = readme_file.read_text(encoding='utf-8', errors='ignore')
                score = self._score_readme_content(content)
                total_score += score
            except Exception as e:
                logger.warning(f"Could not read README file {readme_file}: {e}")
                continue
        
        # Average score across README files, with bonus for multiple READMEs
        base_score = total_score / len(readme_files)
        bonus = min(0.1, (len(readme_files) - 1) * 0.05)  # Small bonus for multiple READMEs
        
        return min(1.0, base_score + bonus)
    
    def _score_readme_content(self, content: str) -> float:
        """Score README content based on dataset and code documentation indicators."""
        content_lower = content.lower()
        score = 0.0
        
        # Check for dataset-related keywords and sections
        dataset_indicators = [
            'dataset', 'training data', 'data source', 'data collection',
            'training set', 'test set', 'validation set', 'benchmark',
            'corpus', 'annotations', 'labels'
        ]
        
        dataset_score = sum(1 for indicator in dataset_indicators if indicator in content_lower)
        score += min(0.3, dataset_score * 0.05)  # Max 0.3 for dataset references
        
        # Check for code/example indicators
        code_indicators = [
            'example', 'tutorial', 'how to use', 'quickstart', 'getting started',
            'sample code', 'usage', 'demonstration', 'notebook', 'script'
        ]
        
        code_score = sum(1 for indicator in code_indicators if indicator in content_lower)
        score += min(0.25, code_score * 0.05)  # Max 0.25 for code references
        
        # Check for structured sections (indicates good documentation)
        section_patterns = [
            r'#+\s*(dataset|data)', r'#+\s*(usage|example)', r'#+\s*(quick.*start)',
            r'#+\s*(training)', r'#+\s*(evaluation)', r'#+\s*(citation)',
        ]
        
        section_score = sum(1 for pattern in section_patterns if re.search(pattern, content, re.IGNORECASE))
        score += min(0.2, section_score * 0.04)  # Max 0.2 for structured sections
        
        # Check for links to external resources
        link_patterns = [
            r'https?://[^\s\)]+dataset', r'https?://[^\s\)]+data',
            r'https?://huggingface\.co/datasets', r'https?://github\.com/[^\s\)]+',
        ]
        
        link_score = sum(1 for pattern in link_patterns if re.search(pattern, content, re.IGNORECASE))
        score += min(0.15, link_score * 0.03)  # Max 0.15 for external links
        
        # Check for technical details (model architecture, training details)
        technical_indicators = [
            'architecture', 'parameters', 'epochs', 'learning rate', 'batch size',
            'optimizer', 'loss function', 'metrics', 'evaluation', 'performance'
        ]
        
        technical_score = sum(1 for indicator in technical_indicators if indicator in content_lower)
        score += min(0.1, technical_score * 0.02)  # Max 0.1 for technical details
        
        return score
    
    def _analyze_dataset_documentation(self, files: List[Path]) -> float:
        """Analyze specific dataset documentation files."""
        dataset_files = [
            f for f in files
            if any(keyword in f.name.lower() for keyword in [
                'dataset', 'data_info', 'data.json', 'dataset_info',
                'train.json', 'test.json', 'validation.json'
            ])
        ]
        
        if not dataset_files:
            return 0.0
        
        score = 0.0
        
        # Base score for having dataset files
        score += 0.4
        
        # Additional score based on number and types of dataset files
        json_files = [f for f in dataset_files if f.suffix == '.json']
        csv_files = [f for f in dataset_files if f.suffix == '.csv']
        
        score += min(0.3, len(json_files) * 0.1)  # Bonus for structured data
        score += min(0.2, len(csv_files) * 0.1)   # Bonus for data files
        
        # Analyze content of dataset info files
        for file in dataset_files[:3]:  # Limit to first 3 files to avoid overwhelming
            try:
                content = file.read_text(encoding='utf-8', errors='ignore')
                if self._has_comprehensive_dataset_info(content):
                    score += 0.1
            except Exception:
                continue
        
        return min(1.0, score)
    
    def _has_comprehensive_dataset_info(self, content: str) -> bool:
        """Check if dataset info content is comprehensive."""
        content_lower = content.lower()
        
        required_info = [
            'description', 'source', 'size', 'format', 'license'
        ]
        
        found_info = sum(1 for info in required_info if info in content_lower)
        return found_info >= 3  # At least 3 out of 5 required pieces of info
    
    def _analyze_example_code(self, files: List[Path]) -> float:
        """Analyze example code and scripts."""
        code_extensions = {'.py', '.ipynb', '.sh', '.R', '.js', '.ts'}
        example_patterns = ['example', 'demo', 'tutorial', 'sample', 'quickstart']
        
        example_files = [
            f for f in files
            if (f.suffix in code_extensions and
                any(pattern in f.name.lower() for pattern in example_patterns))
        ]
        
        # Also look for Jupyter notebooks (strong indicator of examples)
        notebook_files = [f for f in files if f.suffix == '.ipynb']
        
        # Python files in examples/ or scripts/ directories
        script_files = [
            f for f in files
            if (f.suffix == '.py' and
                any(part in f.parts for part in ['examples', 'scripts', 'demo', 'tutorials']))
        ]
        
        total_example_files = len(set(example_files + notebook_files + script_files))
        
        if total_example_files == 0:
            return 0.0
        
        # Base score for having examples
        score = 0.4
        
        # Additional score based on variety and number
        score += min(0.3, len(notebook_files) * 0.1)    # Jupyter notebooks are valuable
        score += min(0.2, len(example_files) * 0.05)    # General example files
        score += min(0.1, len(script_files) * 0.03)     # Script files
        
        return min(1.0, score)
    
    def _analyze_dataset_links(self, files: List[Path]) -> float:
        """Analyze links to datasets in documentation."""
        score = 0.0
        
        # Check README and documentation files for dataset links
        doc_files = [
            f for f in files
            if f.suffix in {'.md', '.txt', '.rst'} or 'readme' in f.name.lower()
        ]
        
        dataset_link_patterns = [
            r'https?://huggingface\.co/datasets/[^\s\)]+',
            r'https?://[^\s\)]*(dataset|data)[^\s\)]*',
            r'https?://kaggle\.com/[^\s\)]+',
            r'https?://[^\s\)]*\.csv',
            r'https?://[^\s\)]*\.json',
        ]
        
        found_links = 0
        
        for doc_file in doc_files:
            try:
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                for pattern in dataset_link_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    found_links += len(matches)
            except Exception:
                continue
        
        if found_links > 0:
            score = min(1.0, 0.3 + (found_links * 0.1))
        
        return score
    
    def _analyze_training_scripts(self, files: List[Path]) -> float:
        """Analyze training and evaluation scripts."""
        training_patterns = ['train', 'fine', 'finetune', 'eval', 'evaluate', 'inference']
        
        training_files = [
            f for f in files
            if (f.suffix == '.py' and
                any(pattern in f.name.lower() for pattern in training_patterns))
        ]
        
        if not training_files:
            return 0.0
        
        # Base score for having training scripts
        score = 0.5
        
        # Additional score for variety of scripts
        script_types = set()
        for file in training_files:
            name_lower = file.name.lower()
            if 'train' in name_lower:
                script_types.add('training')
            if any(word in name_lower for word in ['eval', 'evaluate', 'test']):
                script_types.add('evaluation')
            if 'inference' in name_lower:
                script_types.add('inference')
        
        # Bonus for having different types of scripts
        score += len(script_types) * 0.1
        
        return min(1.0, score)
    
    def _get_weights_for_category(self, category: Category) -> Dict[str, float]:
        """Get component weights based on the repository category."""
        if category == "MODEL":
            return {
                'readme_quality': 0.25,
                'dataset_documentation': 0.20,
                'example_code': 0.25,
                'dataset_links': 0.15,
                'training_scripts': 0.15
            }
        elif category == "DATASET":
            return {
                'readme_quality': 0.30,
                'dataset_documentation': 0.35,
                'example_code': 0.20,
                'dataset_links': 0.10,
                'training_scripts': 0.05
            }
        else:  # CODE
            return {
                'readme_quality': 0.20,
                'dataset_documentation': 0.15,
                'example_code': 0.35,
                'dataset_links': 0.15,
                'training_scripts': 0.15
            }


# Register the metric
register(DatasetAndCodeScoreMetric())
