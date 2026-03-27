FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY config.py forwarder.py imap_idle.py main.py state.py utils.py ./

RUN pip install --no-cache-dir .

CMD ["python", "main.py"]
