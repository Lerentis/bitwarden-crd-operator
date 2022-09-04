FROM alpine:latest as builder

ARG BW_VERSION=2022.8.0

RUN apk add wget unzip

RUN cd /tmp && wget https://github.com/bitwarden/clients/releases/download/cli-v${BW_VERSION}/bw-linux-${BW_VERSION}.zip && \
    unzip /tmp/bw-linux-${BW_VERSION}.zip

FROM ubuntu:jammy

COPY --from=builder /tmp/bw /usr/local/bin/bw
COPY requirements.txt requirements.txt

RUN set -eux; \
    groupadd -r bw-operator ; \
    useradd -r -g bw-operator -s /sbin/nologin bw-operator; \
    mkdir -p /home/bw-operator; \
    chown -R bw-operator /home/bw-operator; \
    chmod +x /usr/local/bin/bw; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3 python3-pip; \
    apt-get clean;

COPY --chown=bw-operator:bw-operator bitwarden-crd-operator.py /home/bw-operator/bitwarden-crd-operator.py

USER bw-operator

RUN set -eux; \
    pip install -r requirements.txt

ENTRYPOINT [ "/home/bw-operator/bitwarden-crd-operator.py" ]
CMD [ "--help" ]