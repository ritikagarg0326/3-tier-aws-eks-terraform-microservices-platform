# syntax=docker/dockerfile:1
# video-service - multi-stage build. Build context is the repository root:
#   docker build -f services/video/Dockerfile -t hotstar/video .
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY services/video/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY libs/common /build/common
RUN pip install /build/common

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH" SERVICE_NAME=video-service PORT=8004
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /srv --shell /usr/sbin/nologin app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /srv
COPY services/video/ /srv/
RUN sed -i 's/\r$//' /srv/entrypoint.sh && chmod +x /srv/entrypoint.sh && rm -rf /srv/tests /srv/requirements-dev.txt /srv/pytest.ini \
    && mkdir -p /data && chown -R app:app /srv /data
USER app
EXPOSE 8004
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8004')+'/health',timeout=3)" || exit 1
ENTRYPOINT ["/srv/entrypoint.sh"]
