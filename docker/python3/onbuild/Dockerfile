ARG VERSION

FROM bgio/plugins:python3-$VERSION

ONBUILD COPY install-prereqs*.sh requirements*.txt /tmp/
ONBUILD RUN bash -c " \
    if [ -f '/tmp/install-prereqs.sh' ]; then \
            bash /tmp/install-prereqs.sh; \
    fi && \
    if [ -f '/tmp/requirements.txt' ]; then \
        python -m pip install -r /tmp/requirements.txt; \
    fi"