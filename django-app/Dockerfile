FROM python:3.12

WORKDIR /app

# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     build-essential \
#     curl && \
#     curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
#     export PATH="$HOME/.cargo/bin:$PATH" && \
#     echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Install pip and upgrade it to the latest version
RUN pip install --upgrade pip

# Install PyTorch
# RUN pip install torch==2.5.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD echo "waiting 5sec to startup db .." && \
    sleep 5 && \
    python manage.py migrate && \
    python manage.py runserver 0.0.0.0:8000
