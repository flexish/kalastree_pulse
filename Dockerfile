# Kalastree Pulse — container image for Cloud Run (or any Docker host).
#
# Runs the app exactly as it runs locally (`uvicorn app.main:app`) — no
# code changes needed to deploy here, unlike a serverless-functions
# platform. Secrets (SECRET_KEY, ADMIN_PASSWORD, the Google service
# account JSON, ...) are supplied at runtime via Cloud Run env vars /
# Secret Manager, never baked into this image — see the README's
# "Deploying to Google Cloud Run" section.

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached across builds that
# only change application code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/ ./config/

# Cloud Run sets $PORT (defaults to 8080) and requires the container to
# listen on it — must stay a shell-form CMD so the variable expands.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
