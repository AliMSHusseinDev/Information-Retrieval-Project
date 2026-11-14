FROM python:3.12-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY requirements.txt .
# Optional build-time CA bundle for managed networks; TLS verification stays on.
# Ordinary Docker Desktop users can build without providing this secret.
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then \
        pip install --cert /run/secrets/pip_ca --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi
COPY . .
ENV SPARK_LOCAL_IP=127.0.0.1
CMD ["python", "run_spark.py"]
