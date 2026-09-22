FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.lock.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api /app/apps/api
COPY apps/__init__.py /app/apps/__init__.py
COPY analytics /app/analytics
RUN useradd --create-home --uid 10001 thinkfirst
USER thinkfirst
HEALTHCHECK --interval=30s --timeout=6s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health', timeout=5)"
CMD ["python", "-m", "apps.api.serve"]
