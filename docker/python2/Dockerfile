FROM alpine:3.9

ARG VERSION

RUN apk add --no-cache python2 py2-pip && \
    pip --no-cache-dir install -U pip && \
    pip --no-cache-dir install brewtils==$VERSION

WORKDIR /
VOLUME /src

COPY docker-entrypoint.sh /

CMD ["python", "-m", "src"]
