FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG INSTALL_LOCAL_DEPS=false

RUN if [ "$INSTALL_LOCAL_DEPS" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends git \
      && rm -rf /var/lib/apt/lists/*; \
    fi

COPY requirements.txt .
COPY requirements.local.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_LOCAL_DEPS" = "true" ]; then \
         pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.local.txt; \
       fi

COPY app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
