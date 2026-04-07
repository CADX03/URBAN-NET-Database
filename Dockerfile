# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for compiling libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file FIRST to leverage Docker cache
COPY requirements.txt .

# Install python libraries from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy your python files into the container
COPY ./frontend/app.py ./frontend/utils.py ./
COPY backend/ ./backend/
COPY examples/ ./examples/

# Expose Streamlit's default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]