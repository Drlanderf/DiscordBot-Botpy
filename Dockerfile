FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Version et commit transmis par GitHub Actions au moment du build
ARG BOT_VERSION=dev
ARG BOT_COMMIT=
ENV BOT_VERSION=$BOT_VERSION \
    BOT_COMMIT=$BOT_COMMIT
VOLUME /data
CMD ["python", "bot.py"]
