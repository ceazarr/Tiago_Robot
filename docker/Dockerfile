FROM palroboticssl/tiago_tutorials:noetic

# Install Python 3 Pip, ONNX Runtime, Ultralytics YOLO, and ONNX
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip python3-setuptools python3-wheel && \
    pip3 install --no-cache-dir onnxruntime ultralytics onnx && \
    rm -rf /var/lib/apt/lists/*
