FROM python:3.12-alpine as base

ARG VERSION

RUN pip --no-cache-dir install brewtils==$VERSION

WORKDIR /
VOLUME /src

CMD ["python", "-m", "src"]
