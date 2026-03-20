FROM python:3.12-slim
WORKDIR /app
COPY . .
ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["yousee-epg-mcp-http"]
