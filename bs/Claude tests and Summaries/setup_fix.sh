#!/bin/bash
set -e

echo "🚀 Installing ACME CLI Project Dependencies"
echo "==========================================="

cd "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"

echo "1. Installing pip..."
python3 -m pip install --user --upgrade pip

echo "2. Installing pytest and coverage..."
python3 -m pip install --user pytest pytest-cov

echo "3. Installing core dependencies..."
python3 -m pip install --user huggingface-hub orjson requests typing-extensions

echo "4. Installing project in development mode..."
python3 -m pip install --user -e .

echo "5. Testing imports..."
python3 -c "from acemcli.logging_setup import setup_logging; print('✅ Logging setup imported')"
python3 -c "from acemcli.metrics.performance_claims import PerformanceClaimsMetric; print('✅ Performance claims imported')"
python3 -c "from acemcli.cli import infer_category; print('✅ CLI imported')"

echo "6. Testing pytest..."
python3 -m pytest --version

echo "7. Running quick test..."
python3 -m pytest test/test_cli.py::test_infer_category_model -v

echo ""
echo "🎉 Setup complete! Ready to run ./run test"
