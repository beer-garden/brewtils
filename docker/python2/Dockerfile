FROM python:2.7-alpine

ARG VERSION

RUN pip --no-cache-dir install brewtils==$VERSION

WORKDIR /
VOLUME /src

CMD ["python", "-m", "src"]
