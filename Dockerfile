# Use Python 3.8 as the base image
FROM python:3.8-slim

# Set the working directory inside the container
WORKDIR /app

<<<<<<< HEAD
# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
=======
# Install dependencies
COPY requirements.txt .
>>>>>>> 8277c123cf8002538fc590af19e2036c221cb51f
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for Flask app
EXPOSE 5050

# Run the Flask app
CMD ["python", "app.py"]
