FROM alpine:3.22.0

LABEL org.opencontainers.image.source=https://github.com/Lerentis/bitwarden-crd-operator
LABEL org.opencontainers.image.description="Kubernetes Operator to create k8s secrets from bitwarden"
LABEL org.opencontainers.image.licenses=MIT

ARG PYTHON_VERSION=3.12.11-r0
ARG PIP_VERSION=25.1.1-r0
ARG GCOMPAT_VERSION=1.1.0-r4
ARG LIBCRYPTO_VERSION=3.5.0-r0
ARG BW_VERSION=2025.5.0
ARG NODE_VERSION=22.16.0-r2

COPY requirements.txt /requirements.txt

RUN set -eux; \
    apk update; \
    apk del nodejs-current; \
    apk add nodejs=${NODE_VERSION} npm; \
    npm install -g @bitwarden/cli@${BW_VERSION} semver; \
    addgroup -S -g 1000 bw-operator; \
    adduser -S -D -u 1000 -G bw-operator bw-operator; \
    mkdir -p /home/bw-operator; \
    chown -R bw-operator /home/bw-operator; \
    apk add gcc musl-dev libstdc++ gcompat=${GCOMPAT_VERSION} python3=${PYTHON_VERSION} py3-pip=${PIP_VERSION} libcrypto3=${LIBCRYPTO_VERSION}; \
    pip install -r /requirements.txt --no-warn-script-location --break-system-packages; \
    rm /requirements.txt; \
    apk del --purge gcc musl-dev libstdc++;

COPY --chown=bw-operator:bw-operator src /home/bw-operator

USER bw-operator

ENTRYPOINT [ "kopf", "run", "--log-format=json", "--all-namespaces", "--liveness=http://0.0.0.0:8080/healthz" ]
CMD [ "/home/bw-operator/bitwardenCrdOperator.py", "/home/bw-operator/kv.py", "/home/bw-operator/dockerlogin.py", "/home/bw-operator/template.py"]
