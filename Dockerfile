# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for compiling libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python libraries
# requests is needed for API calls, pandas for data handling, streamlit for UI
RUN pip install streamlit pandas requests streamlit-oauth

# Copy your python files into the container
COPY ./frontend/app.py .

COPY backend/ ./backend/
# ^ Ensure your functions are in backend_logic.py or inside app.py

# Expose Streamlit's default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]