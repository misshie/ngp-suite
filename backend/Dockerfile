FROM python:3.10

WORKDIR /app

# Default: CPU-only PyTorch. Set USE_CUDA=1 to install CUDA-enabled PyTorch instead.
ARG USE_CUDA=0

COPY requirements_docker.txt requirements_docker_cuda.txt ./

# Pin torch/torchvision so later deps (e.g. onnx2torch -> torchvision) cannot
# replace a CPU wheel with a newer CUDA build from PyPI.
RUN printf 'torch==2.3.1\ntorchvision==0.18.1\n' > /tmp/torch-constraints.txt; \
    if [ "$USE_CUDA" = "1" ]; then \
      echo "Installing CUDA-enabled PyTorch and dependencies..."; \
      pip install --no-cache-dir torch==2.3.1 torchvision==0.18.1; \
      pip install --no-cache-dir -r requirements_docker_cuda.txt \
        -c /tmp/torch-constraints.txt; \
    else \
      echo "Installing CPU-only PyTorch and dependencies..."; \
      pip install --no-cache-dir torch==2.3.1 torchvision==0.18.1 \
        --index-url https://download.pytorch.org/whl/cpu; \
      pip install --no-cache-dir -r requirements_docker.txt \
        -c /tmp/torch-constraints.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu; \
    fi

# GMDB models, gallery encodings and metadata contain patient-derived data and are NOT
# baked into the image. compose.yml bind-mounts them read-only at /app/data and
# /app/saved_models (host side: $NGPSUITE_GMDB_DIR/{data,saved_models}).
# MONDO is CC BY 4.0 and contains no patient data, so it ships inside the image
# (and is tracked in git under mondo/, unlike backend/data/).
COPY mondo ./mondo
COPY main.py ./main.py
COPY config.json ./config.json
COPY lib ./lib
COPY static ./static

# Fail fast with a full list of missing GMDB files before starting the workers.
CMD ["sh", "-c", "python -m lib.runtime_files && exec uvicorn main:app --host 0.0.0.0 --port 5000 --workers 2"]
