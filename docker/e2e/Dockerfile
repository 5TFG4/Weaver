FROM python:3.13-slim-bookworm
WORKDIR /app

# Reuse the same dependency files as backend — zero sync cost
COPY docker/backend/requirements.txt docker/backend/requirements.dev.txt /tmp/deps/
RUN pip install --no-cache-dir -r /tmp/deps/requirements.dev.txt \
    && rm -rf /tmp/deps

# Install Playwright + Chromium browser binary
RUN pip install --no-cache-dir playwright>=1.40.0 pytest-playwright>=0.5.0 \
    && playwright install chromium --with-deps

# Copy project source (tests + src needed for imports)
COPY . /app

# Default: run all E2E tests
CMD ["pytest", "tests/e2e/", "-v", "--timeout=60"]
