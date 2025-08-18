FROM python:3.13-slim

# # Install system dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /luxtj_be

# Copy the application code
COPY . .

# Copy requirements and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Expose the port
EXPOSE 8000

# Default command (can be overridden at runtime)
CMD ["uvicorn", "app.core.app:application_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
