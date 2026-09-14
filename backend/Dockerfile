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

COPY saved_models/Resnet50_Final.pth ./saved_models/Resnet50_Final.pth
COPY saved_models/glint360k_r100.onnx ./saved_models/glint360k_r100.onnx
COPY saved_models/s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth ./saved_models/s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth
COPY saved_models/s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth ./saved_models/s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth
COPY data/gallery_encodings/GMDB_gallery_encodings_23052026_v1.1.4_service.pkl ./data/gallery_encodings/GMDB_gallery_encodings_23052026_v1.1.4_service.pkl
COPY data/transformation_probabilities_07052025.csv ./data/transformation_probabilities_07052025.csv
COPY data/image_gene_and_syndrome_metadata_pp4_23052026_v1.1.4.p ./data/image_gene_and_syndrome_metadata_pp4_23052026_v1.1.4.p
COPY main.py ./main.py
COPY config.json ./config.json
COPY lib ./lib
COPY static ./static

CMD [ "uvicorn",  "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
