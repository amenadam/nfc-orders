FROM python:3.10-slim

# Install dependencies for dlib
RUN apt-get update && apt-get install -y \
    cmake \
    libboost-all-dev \
    build-essential \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app uses
EXPOSE 8000

# Command to run the bot
CMD ["python", "bot.py"]
