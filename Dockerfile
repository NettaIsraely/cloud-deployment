# Use the official Python 3.12 image as the base (gives us a Linux OS with Python pre-installed)
FROM python:3.12

# Tell Python not to write .pyc bytecode files to disk (keeps the image cleaner)
# Tell Python not to buffer stdout/stderr (so logs appear immediately in the terminal)
# Set the port the server will listen on (the app reads this env var at startup)
# Tell the app where to find the CSV data files inside the container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    TLVFLOW_DATA_DIR=/app/data

# Set /app as the working directory — all following commands run from here
WORKDIR /app

# Copy the project config file first (contains package name, version, and dependencies)
COPY pyproject.toml ./

# Copy the application source code into the container
COPY src ./src

# Copy the data folder (vehicles.csv and stations.csv that the app loads on startup)
COPY data ./data

# Install the application and all its dependencies listed in pyproject.toml
# --no-cache-dir: don't save the download cache, keeps the image size smaller
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Document that the container listens on port 8080 (doesn't actually open the port — just metadata)
EXPOSE 8080

# The command to run when the container starts — launches the FastAPI server via the installed script
CMD ["tlvflow-api"]
