from pathlib import Path
import re
import time
from typing import Tuple

#licenses compatible with LGPL v2.1
COMPATIBLE_LICENSES = { 
    "lgpl-2.1", "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "mpl-2.0"
}

def extract_license(readme_text: str) -> str:
    """
    Return just the License section text from a README, or "" if not found.
    """
    m = re.search(r"##\s*License\s+([\s\S]+?)(?:\n## |\Z)", readme_text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def detect_license(readme_text: str) -> str:
    text = readme_text.lower()

    # Strong, specific patterns first
    patterns = [
        (r'\blgpl\s*[- ]?2\.1\b', 'lgpl-2.1'),
        (r'\bgnu\s+lesser\s+general\s+public\s+license\b.*\b2\.1\b', 'lgpl-2.1'),
        (r'\bapache\b.*\b2\.0\b', 'apache-2.0'),
        (r'\bmit\b', 'mit'),
        (r'\bbsd\b.*\b3\b', 'bsd-3-clause'),
        (r'\bbsd\b.*\b2\b', 'bsd-2-clause'),
        (r'\bmozilla public license\b.*\b2\.0\b|\bmpl\s*[- ]?2\.0\b', 'mpl-2.0'),
    ]
    for pat, lid in patterns:
        if re.search(pat, text, flags=re.IGNORECASE | re.DOTALL):
            return lid

    # Looser fallbacks
    if "lgpl" in text and "2.1" in text:
        return "lgpl-2.1"

    return "unknown"


def find_license(repo_path: str) -> str:
    """
    Look for license text in LICENSE files, then fallback to README License section.
    Returns a string (possibly empty).
    """
    repo = Path(repo_path)
    candidates = ["LICENSE", "LICENSE.txt", "LICENSE.md", "README.md"]

    for fname in candidates:
        fpath = repo / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        if fname.lower().startswith("readme"):
            content = extract_license(content)  # ✅ ensure this returns a str
        if isinstance(content, str) and content.strip():  # ✅ defensive check
            return content
    return ""


def check_license(repo_path: str) -> Tuple[float, int]:
    #check repo for license file or license in readme return a score and latency
    start_time = time.time()
    repo = Path(repo_path)
    
    license_text = find_license(repo_path)

    license_id = detect_license(license_text)
    if license_id in COMPATIBLE_LICENSES:
        score = 1.0 # valid license
    elif license_id == "unknown" and license_text:
        score = 0.5 # license exists but is not recognized
    else: 
        score = 0.0 # no license or is incompatible

    latency_ms = int((time.time() - start_time) * 1000)
    return score, latency_ms