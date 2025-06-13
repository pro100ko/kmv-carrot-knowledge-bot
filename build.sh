#!/bin/bash
set -e

# Set Python path
export PYTHONPATH=/opt/render/project/src

# Upgrade pip
python -m pip install --upgrade pip

# Install the package in development mode with verbose output
echo "Installing package in development mode..."
pip install -e . -v

# Install requirements with verbose output
echo "Installing requirements..."
pip install -r requirements.txt -v

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p /opt/render/project/src/monitoring/data
mkdir -p /opt/render/project/src/logs
mkdir -p /opt/render/project/src/metrics
mkdir -p /opt/render/project/src/backups
mkdir -p /opt/render/project/src/media/products
mkdir -p /opt/render/project/src/media/categories
mkdir -p /opt/render/project/src/media/tests
mkdir -p /opt/render/project/src/media/users
mkdir -p /opt/render/project/src/media/temp
mkdir -p /opt/render/project/src/migrations

# Verify installation
echo "Verifying package installation..."
python -c "import monitoring.metrics; print('monitoring.metrics module found')" 