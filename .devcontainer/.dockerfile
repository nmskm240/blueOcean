FROM python:3.13-bullseye

RUN pip install --no-cache-dir uv

WORKDIR /workspace
