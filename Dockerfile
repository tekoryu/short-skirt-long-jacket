# Use Python 3.11 slim image
FROM python:3.12.3-alpine3.19

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements-dev.txt /tmp/requirements-dev.txt
COPY ./scripts /scripts
COPY ./app /app
WORKDIR /app
EXPOSE 8000

# Install system dependencies
ARG DEV=false
ARG USE_PROXY=false
ARG HTTP_PROXY_URL=http://10.1.101.101:8080
RUN if [ "$USE_PROXY" = "true" ]; then \
        export HTTP_PROXY=$HTTP_PROXY_URL && \
        export HTTPS_PROXY=$HTTP_PROXY_URL && \
        export http_proxy=$HTTP_PROXY_URL && \
        export https_proxy=$HTTP_PROXY_URL; \
    fi && \
    python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client jpeg-dev dos2unix && \
    apk add --update --no-cache --virtual .tmp-build-deps \
    build-base postgresql-dev musl-dev zlib zlib-dev linux-headers && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ $DEV = "true" ]; \
    then /py/bin/pip install -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp && \
    apk del .tmp-build-deps && \
    adduser \
        --disabled-password \
        --no-create-home \
        django-user && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    mkdir -p /vol/web/logs && \
    chown -R django-user:django-user /vol && \
    chown -R django-user:django-user /app && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts && \
    dos2unix /scripts/*.sh && \
    apk add --no-cache curl


ENV PATH="/scripts:/py/bin:$PATH"

USER django-user

# Run the application
CMD ["/scripts/run.sh"] 