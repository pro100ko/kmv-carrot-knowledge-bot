#!/bin/bash
set -e

# Upgrade pip
python -m pip install --upgrade pip

# Install the package in development mode
pip install -e .

# Install requirements
pip install -r requirements.txt

# Create necessary directories
mkdir -p monitoring/data
mkdir -p logs
mkdir -p metrics
mkdir -p backups
mkdir -p data
mkdir -p media/products
mkdir -p media/categories
mkdir -p media/tests
mkdir -p media/users
mkdir -p media/temp
mkdir -p migrations 