# FastAPI Application

A stateless FastAPI application with basic setup.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

To run the application, use one of the following methods:

1. Using Python directly:
```bash
python main.py
```

2. Using Uvicorn directly:
```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## Available Endpoints

- `GET /`: Welcome message
- `GET /health`: Health check endpoint
