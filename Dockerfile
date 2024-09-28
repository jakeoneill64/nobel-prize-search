# Use the official Ubuntu 22.04 base image
FROM ubuntu:22.04

# Install Python 3.12 and necessary packages
RUN apt update && apt install -y python3.12 python3.12-venv python3-pip
COPY requirements.txt .

RUN python3.12 -m venv /venv
RUN /venv/bin/pip install -r requirements.txt

# Copy the rest of your application code into the container
COPY src/main/app.py .

# Command to run your application (change this as needed)
CMD ["python3", "app.py"]
