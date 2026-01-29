FROM python:3.13-slim-bookworm
WORKDIR /weaver
COPY requirements.txt /weaver/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /weaver/
CMD ["tail", "-f", "/dev/null"]
