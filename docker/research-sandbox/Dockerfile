# Research Sandbox: Python + numpy + scipy for report experiments.
# No network at runtime; used by research_sandbox.py.
FROM python:3.11.11-slim-bookworm

RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 \
 && useradd --create-home --uid 10001 sandbox

WORKDIR /app
USER sandbox
CMD ["python", "script.py"]
