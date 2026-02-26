FROM python:3.13-slim-bookworm
WORKDIR /weaver

COPY docker/backend/requirements.txt /weaver/docker/backend/requirements.txt
RUN pip install --no-cache-dir -r /weaver/docker/backend/requirements.txt
COPY . /weaver/

EXPOSE 8000
CMD ["uvicorn", "weaver:app", "--host", "0.0.0.0", "--port", "8000"]
