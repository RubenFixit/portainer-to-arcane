FROM python:3.13-alpine
WORKDIR /tool
COPY prepare.py .
ENTRYPOINT ["python", "/tool/prepare.py"]
