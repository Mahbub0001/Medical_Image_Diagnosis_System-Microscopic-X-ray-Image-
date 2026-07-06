FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for OpenCV, Matplotlib, and YOLO
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first to prevent downloading heavy GPU wheels (keeps container lightweight)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for temp heatmaps and files
RUN mkdir -p temp_heatmaps temp_files models

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
