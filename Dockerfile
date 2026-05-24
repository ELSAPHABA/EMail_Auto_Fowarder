FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY config.py forwarder.py imap_polling.py main.py state.py utils.py ./
COPY docker-entrypoint.sh ./

RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

RUN pip install --no-cache-dir .

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "main.py"]
