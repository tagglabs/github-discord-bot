FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies including GCC
RUN apt-get update && \
    apt-get install -y --no-install-recommends g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements to cache them
WORKDIR /app
COPY requirements.txt ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip uv && \
    uv pip install --no-cache-dir -r requirements.txt --system

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user and group in a single RUN command
RUN addgroup --system app && adduser --system --group app

# Set work directory
WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code and set ownership to the non-root user
COPY --chown=app:app . .

# Change ownership of the /app directory to the app user
RUN chown app:app /app*

# Expose the port FastAPI runs on
EXPOSE 8000

# Change ownership of the /app directory to the app user
RUN chown app:app /app*

CMD ["sh", "-c", "python3 bot.py"]
