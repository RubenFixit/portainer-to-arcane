FROM python:3.13-alpine
LABEL org.opencontainers.image.source="https://github.com/RubenFixit/portainer-to-arcane"
LABEL org.opencontainers.image.description="Prepare Portrieve exports as Arcane Compose projects"
LABEL org.opencontainers.image.licenses="MIT"
WORKDIR /tool
COPY prepare.py .
ENTRYPOINT ["python", "/tool/prepare.py"]
