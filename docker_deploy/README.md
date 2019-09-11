## PTW Docker walkthrough

### Step 1. Generate certificates for client and server.

Server may use any certificate trusted by client, including issued by public CA. And vice versa, client should use certificate trusted by CA specified to server as `ca.pem` file.

For easiest deployment let's use client and server certificates issued by single local CA. There exists many certificate management solutions, but most hassle-free is [quickcerts](https://github.com/Snawoot/quickcerts). Since we are using Docker, we can generate certificates right away with `quickcerts` in single command like this:

```sh
docker run -it --rm -v "$(pwd)/certs:/certs" \
    yarmak/quickcerts -D server -C client1 -C client2 -C client3
```

`./certs` directory will contain CA, certificates and private keys.

Client certificates can be used right away with `ptw`. Server certificate has to be concatenated with it's private key into single file and placed into file `./ptw-server/certs/server.combined.pem`, along with `ca.pem`.

### Step 2. Spin up server.

Place server combined certificate bundle `server.combined.pem` and `ca.pem` into `ptw-server/certs` directory. Here is how you can build `server.combined.pem`:

```sh
cat certs/server.pem certs/server.key > certs/server.combined.pem
```

Run following command in `ptw-server` directory:

```sh
docker-compose up -d
```

It will bring up two containers: one with haproxy instance and another with Dante SOCKS proxy. haproxy will start accepting TLS-wrapped connections on port 443, exposing decoy HTTP-server to unauthenticated users. Legitimate TLS-authenticated connections will be passed to Dante SOCKS-proxy or routed directly by haproxy, if they contain PROXY protocol prologue, added by `ptw` in transparent proxy mode.

### Step 3. Setup client-side wrapper.

It's not mandatory to use docker to run client (`ptw`), probably you'd better install it using just `pip`. But if you prefer Docker way, there are two options.

#### Option A. Run `ptw` directly with docker.

Run docker `ptw` image just like conventional application, passing command line arguments with `ptw` CLI options:

```sh
docker run -it --rm -p 57800:57800 -v "$(pwd)"/certs:/certs yarmak/ptw -c /certs/client.pem -k /certs/client.key -C /certs/ca.pem --tls-servername server server-address.tld 443
```

#### Option B. Use `docker-compose`.

Place client certificates and `ca.pem` into `ptw-client/certs` directory.

Adjust last 3 lines in `ptw-client/docker-compose.yml` to your actual server address, port and certificate CN (or do not specify it, if it is same as hostname).

Run following command in `ptw-client` directory:

```sh
docker-compose up -d
```

### Done

SOCKS proxy at port 57800 will be ready to accept connections.
