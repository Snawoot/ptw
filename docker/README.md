## PTW Docker walkthrough

### Step 1

Generate certificates for client and server. Server may use any certificate trusted by client, including issued by public CA. And vice versa, client should use certificate trusted by CA specified to server as `ca.pem` file.

For easiest deployment let's use client and server certificates issued by single local CA. There exists many certificate management solutions, but most hassle-free is [quickcerts](https://github.com/Snawoot/quickcerts). Since we are using Docker, we can generate certificates right away with `quickcerts` in single command like this:

```sh
docker run -it --rm -v "$(pwd)/certs:/certs" \
    yarmak/quickcerts -D server -C client1 -C client2 -C client3
```

`./certs` directory will contain CA, certificates and private keys.

Client certificates can be used right away with `ptw`. Server certificate has to be concatenated with it's private key into single file and placed into file `./ptw-server/certs/server.combined.pem`, along with `ca.pem`.

### Step 2

Spin up server. Run following command in `ptw-server` directory:

```sh
docker-compose up -d
```

It will bring up two containers: one with haproxy instance and another with Dante SOCKS proxy. haproxy will start accepting TLS-wrapped connections on port 443, exposing decoy HTTP-server to unauthenticated users. Legitimate TLS-authenticated connections will be passed to Dante SOCKS-proxy or routed directly by haproxy, if they contain PROXY protocol prologue, added by `ptw` in transparent proxy mode.
