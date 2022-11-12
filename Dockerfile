FROM alpine:latest as builder

ARG BW_VERSION=2022.8.0

RUN apk add wget unzip

RUN cd /tmp && wget https://github.com/bitwarden/clients/releases/download/cli-v${BW_VERSION}/bw-linux-${BW_VERSION}.zip && \
    unzip /tmp/bw-linux-${BW_VERSION}.zip

#FROM alpine:3.18 as run
#
#RUN set -eux; \
#    groupadd -r bw-operator ; \
#    useradd -r -g bw-operator -s /sbin/nologin bw-operator; \
#    mkdir -p /home/bw-operator; \
#    chown -R bw-operator /home/bw-operator; \
#    chmod +x /usr/local/bin/bw; \
#    apk add libstdc++ python3 py-pip
#COPY --chown=bw-operator:bw-operator bitwarden-crd-operator.py /home/bw-operator/bitwarden-crd-operator.py
#
#USER bw-operator
#
#RUN set -eux; \
#    pip install -r requirements.txt --no-warn-script-location
#
#ENTRYPOINT [ "/home/bw-operator/.local/bin/kopf", "run", "--all-namespaces", "--liveness=http://0.0.0.0:8080/healthz" ]
#CMD [ "/home/bw-operator/bitwarden-crd-operator.py" ]

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
    apt-get upgrade -y; \
    apt-get install -y --no-install-recommends python3 python3-pip; \
    apt-get clean; \
    apt-get -y autoremove; \
    pip install -r requirements.txt; \
    rm requirements.txt; \
    pip cache purge; \
    rm -rf /root/.cache;

COPY --chown=bw-operator:bw-operator src /home/bw-operator

USER bw-operator

ENTRYPOINT [ "kopf", "run", "--all-namespaces", "--liveness=http://0.0.0.0:8080/healthz" ]
CMD [ "/home/bw-operator/bitwardenCrdOperator.py", "/home/bw-operator/kv.py", "/home/bw-operator/dockerlogin.py" ]
