# pull the official docker image
FROM python:3.10-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set the working directory in the container
WORKDIR /app

# Copy the requirements directory into the container
COPY requirements/  app/requirements/

# Install dependencies from base.txt
RUN pip install --no-cache-dir -r app/requirements/base.txt

# Optionally, install dependencies from dev.txt or prod.txt if needed
#RUN pip install --no-cache-dir -r /app/requirements/dev.txt
#RUN pip install --no-cache-dir -r /app/requirements/prod.txt

# copy the content of the local src directory to the working directory
COPY . .

# expose port 8000 for the FastAPI application
EXPOSE 8000

# Command to run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]