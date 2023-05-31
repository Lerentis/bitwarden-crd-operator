FROM alpine:3.18.0

LABEL org.opencontainers.image.source=https://github.com/Lerentis/bitwarden-crd-operator
LABEL org.opencontainers.image.description="Kubernetes Operator to create k8s secrets from bitwarden"
LABEL org.opencontainers.image.licenses=MIT

ARG PYTHON_VERSION=3.11.3-r11
ARG PIP_VERSION=23.1.2-r0
ARG GCOMPAT_VERSION=1.1.0-r1
ARG LIBCRYPTO_VERSION=3.1.0-r4
ARG BW_VERSION=2023.1.0

COPY requirements.txt /requirements.txt

RUN set -eux; \
    apk add --virtual build-dependencies wget unzip; \
    ARCH="$(apk --print-arch)"; \
    case "${ARCH}" in \
       aarch64|arm64) \
          apk add npm; \
          npm install -g @bitwarden/cli@${BW_VERSION}; \
         ;; \
       amd64|x86_64) \
          cd /tmp; \
          wget https://github.com/bitwarden/clients/releases/download/cli-v${BW_VERSION}/bw-linux-${BW_VERSION}.zip; \
          unzip /tmp/bw-linux-${BW_VERSION}.zip; \
         ;; \
       *) \
         echo "Unsupported arch: ${ARCH}"; \
         exit 1; \
         ;; \
    esac; \
    apk del --purge build-dependencies; \
    addgroup -S -g 1000 bw-operator; \
    adduser -S -D -u 1000 -G bw-operator bw-operator; \
    mkdir -p /home/bw-operator; \
    chown -R bw-operator /home/bw-operator; \
    apk add gcc musl-dev libstdc++ gcompat=${GCOMPAT_VERSION} python3=${PYTHON_VERSION} py3-pip=${PIP_VERSION} libcrypto3=${LIBCRYPTO_VERSION}; \
    pip install -r /requirements.txt --no-warn-script-location; \
    rm /requirements.txt; \
    apk del --purge gcc musl-dev libstdc++;

COPY --chown=bw-operator:bw-operator src /home/bw-operator

USER bw-operator

ENTRYPOINT [ "kopf", "run", "--log-format=json", "--all-namespaces", "--liveness=http://0.0.0.0:8080/healthz" ]
CMD [ "/home/bw-operator/bitwardenCrdOperator.py", "/home/bw-operator/kv.py", "/home/bw-operator/dockerlogin.py", "/home/bw-operator/template.py"]
