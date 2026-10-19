# Linux Troubleshooting AI Assistant

## Overview
The Linux Troubleshooting AI Assistant helps users investigate common Linux problems using Retrieval-Augmented Generation (RAG) and AI-assisted responses.

## Features
- Streamlit-based user interface
- Linux troubleshooting questions and answers
- Retrieves relevant information from local documentation
- Includes Linux services and Nginx troubleshooting guides
- Designed to support Linux learning and troubleshooting

## Project Structure
```text
linux-troubleshooter/
├── streamlit_app.py
├── rag_app.py
├── docs/
│   ├── linux_services.txt
│   └── nginx_troubleshooting.txt
├── README.md
└── requirements.txt
```

## Requirements
- Python 3
- Streamlit
- The additional Python packages required by the application
- Ollama and a compatible local model, if configured in the application

## Setup
1. Clone or download this repository.
2. Create and activate a Python virtual environment.
3. Install the dependencies listed in `requirements.txt`.
4. Start the application using the command appropriate for your entry-point file.

Example:
```bash
streamlit run streamlit_app.py
```

## Documentation
The `docs/` directory contains Linux services and Nginx troubleshooting information.

## Learning Project
This project demonstrates Linux troubleshooting, Python, RAG concepts, local AI integration, and Streamlit application development.
