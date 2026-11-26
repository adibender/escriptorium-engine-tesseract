# How a deployment adds this engine: extend the eScriptorium image, install the tesseract binary
# and the language files, then pip install this package. Nothing in eScriptorium changes.
# No default on purpose: the base must be an eScriptorium image built with the engine layer
# (branch feature/engine-layer-upstream). Upstream images would build fine but never load the
# engine. Pass it with --build-arg ESCRIPTORIUM_IMAGE=<image>.
ARG ESCRIPTORIUM_IMAGE
FROM ${ESCRIPTORIUM_IMAGE}

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-deu \
        tesseract-ocr-frk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/escriptorium-engine-tesseract
RUN pip install --no-cache-dir -e /opt/escriptorium-engine-tesseract
