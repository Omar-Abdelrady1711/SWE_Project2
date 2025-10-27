"""
Metrics module for ACME CLI.
This module contains various metrics for evaluating ML models, datasets, and code repositories.
"""

# Import all metrics to ensure they are registered
from . import base
from . import codeCheck
from . import dataset_code_score
from . import dataset_quality
from . import hf_api
from . import licenseCheck
from . import local_repo
from . import performance_claims
from . import ramp_up_time
from . import size_score

__all__ = [
    'base',
    'codeCheck', 
    'dataset_code_score',
    'dataset_quality',
    'hf_api',
    'licenseCheck',
    'local_repo',
    'performance_claims',
    'ramp_up_time',
    'size_score'
]
