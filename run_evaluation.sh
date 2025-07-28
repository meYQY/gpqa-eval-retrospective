#!/bin/bash

# GPQA Evaluation Quick Start Script

echo "=== GPQA Evaluation Framework ==="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo
    echo "⚠️  Warning: .env file not found!"
    echo "Please copy .env.example to .env and add your API key:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env to add your GROK_API_KEY"
    exit 1
fi

# Verify environment
echo
echo "Verifying environment..."
python scripts/verify_config.py

if [ $? -ne 0 ]; then
    echo "❌ Environment verification failed!"
    exit 1
fi

# Check if data is preprocessed
if [ ! -f "data/gpqa_processed.json" ]; then
    echo
    echo "Preprocessing GPQA data..."
    echo "Note: You'll need to enter the password: deserted-untie-orchid"
    python scripts/preprocess_gpqa.py
fi

# Start evaluation
echo
echo "Starting GPQA evaluation..."
echo "This will take 4-5 hours for all 448 questions."
echo "The evaluation supports checkpoint/resume, so you can interrupt safely."
echo
read -p "Press Enter to start evaluation, or Ctrl+C to cancel..."

python core/gpqa_test_resumable.py