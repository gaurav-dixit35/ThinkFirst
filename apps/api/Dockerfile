FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.lock.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api /app/apps/api
COPY apps/__init__.py /app/apps/__init__.py
COPY analytics /app/analytics
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
