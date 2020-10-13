FROM python:2.7-alpine

ARG VERSION

RUN pip --no-cache-dir install brewtils==$VERSION

WORKDIR /
VOLUME /src

COPY docker-entrypoint.sh /

CMD ["python", "-m", "src"]
