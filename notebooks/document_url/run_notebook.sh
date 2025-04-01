#!/bin/bash

# change to root directory
cd "$(realpath "$(dirname "$0")/../..")"

# install dependencies
echo "📦 Activating Poetry environment..."
poetry install  

# start notebook
echo "🚀 Starting Jupyter Notebook..."
poetry run jupyter notebook notebooks/document_url/document_url_notebook.ipynb
