# Syllabus Chatbot

A Flask application that uses OpenAI GPT and vector embeddings to create an interactive chatbot for course syllabi.

## Prerequisites

- Python 3.9+
- pip
- OpenAI API key
- SQLite

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```
Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```



## Do these steps after installation.

4. Initialize database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
python manage.py
```

5. Start application:
```bash
flask run
```

## Default Users

- Admin account:
  - Username: admin
  - Password: admin123
 
## Pytests
```python
pytest #run all tests
pytest -v # run all tests with verbose
```
