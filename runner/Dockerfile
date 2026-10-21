FROM python:3.12-slim

RUN useradd --create-home --uid 10001 runner

WORKDIR /workspace

COPY run_code.py /workspace/run_code.py

USER 10001:10001

CMD ["python", "-I", "/workspace/run_code.py"]
