FROM python:3.7-alpine as base

ARG VERSION

RUN pip --no-cache-dir install brewtils==$VERSION

WORKDIR /
VOLUME /src

COPY docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "-m", "src"]
