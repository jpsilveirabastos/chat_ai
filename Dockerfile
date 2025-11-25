FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

ARG DOPPLER_PROJECT
ARG DOPPLER_CONFIG
ARG DOPPLER_TOKEN

WORKDIR /ai-agent-ocr

ENV HOST="0.0.0.0"

ENV DOPPLER_PROJECT="${DOPPLER_PROJECT}"
ENV DOPPLER_CONFIG="${DOPPLER_CONFIG}"
ENV DOPPLER_TOKEN="${DOPPLER_TOKEN}"

COPY ./requirements.txt /ai-agent-ocr/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /ai-agent-ocr/requirements.txt

COPY ./app /ai-agent-ocr/app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]