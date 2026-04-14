FROM python:3.12-slim

# Environment configs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Create storage folder
RUN mkdir -p storage/chroma

# Expose port
EXPOSE 8000

# Run application
CMD ["chainlit", "run", "src/presentation/chainlit_app.py", "-w", "--host", "0.0.0.0", "--port", "8000"]