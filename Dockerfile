FROM python:3.8

# Install required ODBC libraries
RUN apt-get update && \
    apt-get install -y unixodbc unixodbc-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Set the working directory in the container
WORKDIR /app

# Copy the entire content of the current directory into the container
COPY . .


RUN pip install --no-cache-dir -r requirements.txt

# Change directory to the src folder
WORKDIR /app/src

EXPOSE 5003

# Run service.py when the container launches
CMD ["python", "service.py"]
