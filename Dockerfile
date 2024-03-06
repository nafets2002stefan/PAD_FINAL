FROM python:3.8

RUN apt-get update

# Set the working directory in the container
WORKDIR /app

# Copy the entire content of the current directory into the container
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Change directory to the src folder
WORKDIR /app/src

EXPOSE 5003

# Run service.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=5003"]
