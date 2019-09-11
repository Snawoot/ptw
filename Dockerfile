FROM docker.io/python:3.7-alpine
LABEL maintainer="Vladislav Yarmak <vladislav-ex-src@vm-0.com>"

COPY . /build
WORKDIR /build
RUN true \
   && apk add --no-cache --virtual .build-deps alpine-sdk libffi-dev \
   && apk add --no-cache libffi \
   && pip3 install --no-cache-dir .[uvloop] \
   && apk del .build-deps \
   && true

VOLUME [ "/certs" ]
EXPOSE 57800/tcp
ENTRYPOINT [ "ptw", "-a", "0.0.0.0" ]
