FROM python:3
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install ca-certificates && apt-get clean

ADD certs/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

ADD pyproject.toml /
ADD rose.py /
RUN uv sync --no-dev

ENTRYPOINT [ "uv", "run", "rose.py" ]
