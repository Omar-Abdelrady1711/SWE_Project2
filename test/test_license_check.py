# tests/test_license_check.py
import textwrap
from pathlib import Path
from src.metrics.licenseCheck import check_license  # adjust import path to your project

def write(p: Path, name: str, content: str):
    f = p / name
    f.write_text(content, encoding="utf-8")
    return f

def test_license_file_mit(tmp_path):
    write(tmp_path, "LICENSE", "MIT License\nPermission is hereby granted...")
    score, ms = check_license(str(tmp_path))
    assert score == 1.0
    assert isinstance(ms, int) and ms >= 0

def test_license_file_apache(tmp_path):
    write(tmp_path, "LICENSE.txt", "Apache License, Version 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_license_file_bsd3(tmp_path):
    write(tmp_path, "LICENSE.md", "BSD 3-Clause License\nRedistribution and use...")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_license_readme_section(tmp_path):
    readme = textwrap.dedent("""
        # My Model

        ## License
        This project is licensed under the MIT License. See LICENSE for details.

        ## Usage
        some instructions...
    """)
    write(tmp_path, "README.md", readme)
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_license_unknown_but_present(tmp_path):
    # Custom/non-standard wording → should map to "unknown" and return 0.5
    write(tmp_path, "LICENSE", "This software is free for academic use only.")
    score, _ = check_license(str(tmp_path))
    assert score == 0.5

def test_no_license_anywhere(tmp_path):
    write(tmp_path, "README.md", "# Title\n\nNo license info here.")
    score, _ = check_license(str(tmp_path))
    assert score == 0.0

def test_case_insensitive_detection(tmp_path):
    write(tmp_path, "LICENSE", "mIt liCenSe")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_readme_without_license_section_ignored(tmp_path):
    readme = "# Readme\n\n## Overview\nblah\n\n## Usage\nrun it"
    write(tmp_path, "README.md", readme)
    score, _ = check_license(str(tmp_path))
    assert score == 0.0

def test_prefer_license_file_over_readme(tmp_path):
    # If both exist, license file should win (we check candidates in order)
    write(tmp_path, "README.md", "## License\nLicensed under Apache-2.0")
    write(tmp_path, "LICENSE", "MIT License...")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0  # MIT wins from LICENSE

def test_lgpl_21_maps_to_compatible(tmp_path):
    write(tmp_path, "LICENSE", "GNU Lesser General Public License Version 2.1")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_bsd2_vs_bsd3_detection(tmp_path):
    write(tmp_path, "LICENSE", "BSD 2-Clause License")
    score2, _ = check_license(str(tmp_path))
    assert score2 == 1.0
    write(tmp_path, "LICENSE", "BSD 3-Clause License")
    score3, _ = check_license(str(tmp_path))
    assert score3 == 1.0

def test_encoding_weird_chars(tmp_path):
    # Ensure we don't crash on odd encodings / characters
    content = "MIT Licénsê – permiso otorgado…"
    (tmp_path / "LICENSE").write_text(content, encoding="utf-8", errors="ignore")
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_multiple_files_first_match_wins(tmp_path):
    # Order: LICENSE, LICENSE.txt, LICENSE.md, README.md
    write(tmp_path, "LICENSE.md", "Apache License, Version 2.0")
    write(tmp_path, "LICENSE", "MIT License")  # should be picked first
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_readme_license_extraction_only_section(tmp_path):
    readme = textwrap.dedent("""
        # Title

        ## License
        Apache License, Version 2.0

        ## Something Else
        (should not be considered part of license)
    """)
    write(tmp_path, "README.md", readme)
    score, _ = check_license(str(tmp_path))
    assert score == 1.0

def test_custom_license_yields_half(tmp_path):
    readme = "## License\nCustom internal use only, not open source."
    write(tmp_path, "README.md", readme)
    score, _ = check_license(str(tmp_path))
    assert score == 0.5
