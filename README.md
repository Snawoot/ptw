# ptw

Pooling TLS Wrapper

Accepts TCP connections on listen port and forwards them, wrapped in TLS, to destination port. `ptw` maintains pool of fresh established TLS connections effectively cancelling delay caused by TLS handshake.

ptw may serve as drop-in replacement for stunnel or haproxy for purpose of secure tunneling of TCP connections. Thus, it is intended for use with stunnel or haproxy on server side, accepting TLS connections and forwarding them, for example, to SOCKS proxy. In such configuration make sure your server timeouts long enough to allow fit lifetime of idle client TLS sessions (`-T` option).

`ptw` can be used with custom CAs and/or mutual TLS auth with certificates.

## Features

* Based on proven TLS security and works with well-known server side daemons for TLS termination like haproxy and stunnel.
* Firewall- and DPI-proof: connections are indistinguishable from HTTPS traffic. See `haproxy.cfg` in [config\_examples](https://github.com/Snawoot/ptw/tree/master/config_examples) directory for complete example of webserver masquerading proxy.
* Greater practical performance comparing to other TCP traffic forwading solutions thanks to separate TLS session for each TCP connection.
* Hides TLS connection delay with connection pooling.
* Supports transparent proxy mode.
* Supports TLS SNI (server name indication) spoof - it may be useful to bypass SNI based filters in firewalls.
* Cross-plaform: runs on Linux, macOS, Windows and other Unix-like systems.

## Requirements

* Python 3.5.3+

## Installation

```
pip3 install ptw
```

## Deployment with Docker

ptw is also provided as docker image. You may run it like this:

```sh
docker run -it --rm yarmak/ptw --help
```

In addition, there are docker-compose recipes for deployment of client (ptw) and server suite (haproxy with mutual TLS auth, Dante SOCKS proxy and decoy HTTP-server). See [docker\_deploy](https://github.com/Snawoot/ptw/tree/master/docker_deploy) directory for complete docker deployment guide.

## Usage

See [quickcerts](https://pypi.org/project/quickcerts/) for easy TLS certificate generator.

#### Wrapper for SOCKS/HTTP proxy

```
ptw -c mycert.pem -k mykey.pem -C ca.pem -n 50 -T 300 example.com 1443
```

Corresponding minimal haproxy configuration on server:

```
...

defaults
    log       global
    mode      tcp
    option    tcplog
    option    dontlognull
    timeout connect 5000
    timeout check   5000
    timeout client  600000
    timeout server  600000
    timeout tunnel  600000

frontend socks-proxy
    bind *:1443 ssl crt /etc/haproxy/server.combined.pem ca-file /etc/haproxy/ca.pem verify required
    default_backend socks-proxy

backend socks-proxy
    server localsocks 127.0.0.1:1080

```

This command will accept TCP connections on port 57800, wrap them in TLS and forward them to port 1443 of example.com host, maintaining pool of at least 50 TLS connections no older than 300 seconds. For client TLS authentication see also `-c` and `-k` options.

See also [config\_examples](https://github.com/Snawoot/ptw/tree/master/config_examples) directory for full configuration files for haproxy and danted.

#### Transparent proxy for TCP connections

Run on your router:

```
ptw -a 0.0.0.0 -c mycert.pem -k mykey.pem -C ca.pem -n 50 -T 300 -P v1 example.com 2443
```

Add following rule to iptables:

```sh
iptables -I PREROUTING 1 -t nat -p tcp -s 192.168.0.0/16 '!' -d 192.168.0.0/16 -j REDIRECT --to 57800
```

Assuming your local network is covered by prefix `192.168.0.0/16`.

Corresponding haproxy config sections:

```
frontend tls-wrapper
    bind *:2443 ssl crt /etc/haproxy/server.combined.pem ca-file /etc/haproxy/ca.pem verify required
    default_backend strip-proxy

backend strip-proxy
    server strip-proxy 127.0.0.1:41718

frontend strip-proxy
    bind 127.0.0.1:41718 accept-proxy
    default_backend passthrough

backend passthrough
    server direct *
```

This setup will redirect all TCP connections in your network. If your server supports proxy protocol version 2, you may use it as well (option `-P v2`).

#### Universal haproxy configuration

Also you may share PROXY protocol, SOCKS protocol listener and decoy webserver on single external port. See `haproxy.cfg` in [config\_examples](https://github.com/Snawoot/ptw/tree/master/config_examples) directory.

## Synopsis

```
$ ptw --help
usage: ptw [-h] [-v {debug,info,warn,error,fatal}] [-l FILE]
           [--disable-uvloop] [-a BIND_ADDRESS] [-p BIND_PORT]
           [-W POOL_WAIT_TIMEOUT] [-P {none,v1,v2}] [-n POOL_SIZE]
           [-B BACKOFF] [-T TTL] [-w TIMEOUT] [-c CERT] [-k KEY] [-C CAFILE]
           [--no-hostname-check | --tls-servername TLS_SERVERNAME]
           dst_address dst_port

Pooling TLS wrapper

positional arguments:
  dst_address           target hostname
  dst_port              target port

optional arguments:
  -h, --help            show this help message and exit
  -v {debug,info,warn,error,fatal}, --verbosity {debug,info,warn,error,fatal}
                        logging verbosity (default: info)
  -l FILE, --logfile FILE
                        log file location (default: None)
  --disable-uvloop      do not use uvloop even if it is available (default:
                        False)

listen options:
  -a BIND_ADDRESS, --bind-address BIND_ADDRESS
                        bind address (default: 127.0.0.1)
  -p BIND_PORT, --bind-port BIND_PORT
                        bind port (default: 57800)
  -W POOL_WAIT_TIMEOUT, --pool-wait-timeout POOL_WAIT_TIMEOUT
                        timeout for pool await state of client connection
                        (default: 15)
  -P {none,v1,v2}, --proxy-protocol {none,v1,v2}
                        transparent mode: prepend all connections with proxy-
                        protocol data (default: none)

pool options:
  -n POOL_SIZE, --pool-size POOL_SIZE
                        connection pool size (default: 25)
  -B BACKOFF, --backoff BACKOFF
                        delay after connection attempt failure in seconds
                        (default: 5)
  -T TTL, --ttl TTL     lifetime of idle pool connection in seconds (default:
                        30)
  -w TIMEOUT, --timeout TIMEOUT
                        server connect timeout (default: 4)

TLS options:
  -c CERT, --cert CERT  use certificate for client TLS auth (default: None)
  -k KEY, --key KEY     key for TLS certificate (default: None)
  -C CAFILE, --cafile CAFILE
                        override default CA certs by set specified in file
                        (default: None)
  --no-hostname-check   do not check hostname in cert subject. This option is
                        useful for private PKI and available only together
                        with "--cafile" (default: False)
  --tls-servername TLS_SERVERNAME
                        specifies hostname to expect in server TLS certificate
                        (default: None)
```
