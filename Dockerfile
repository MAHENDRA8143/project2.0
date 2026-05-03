FROM python:3.11-slim

WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Start FastAPI
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
