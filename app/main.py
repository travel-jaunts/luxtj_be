from app.core.app import application_factory

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(application_factory(), host="0.0.0.0", port=8000)
