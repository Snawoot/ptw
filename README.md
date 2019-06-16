# ptw

Pooling TLS Wrapper

Accepts TCP connections on listen port and forwards them, wrapped in TLS, to destination port. `ptw` maintains pool of fresh established TLS connections effectively cancelling delay caused by TLS handshake.

ptw may serve as drop-in replacement for stunnel or haproxy for purpose secure tunneling of TCP connections. Thus, it is intended for use with stunnel or haproxy on server side, accepting TLS connections and forwarding them, for example, to SOCKS proxy. In such configuration make sure your server timeouts long enough to allow fit lifetime of idle client TLS sessions (`-T` option).

`ptw` can be used with custom CAs and/or mutual TLS auth with certificates.

## Requirements

* Python 3.5.3+

## Installation

```
pip3 install ptw
```

## Example

```
ptw -n 50 -T 300 example.com 1443
```

This command will accept TCP connections on port 57800, wrap them in TLS and forward them to port 1443 of example.com host, maintaining pool of at least 50 TLS connections no older than 300 seconds. For client TLS authentication see also `-c` and `-k` options.



## Synopsis

```
$ ptw --help
usage: ptw [-h] [-v {debug,info,warn,error,fatal}] [-l FILE]
           [--disable-uvloop] [-a BIND_ADDRESS] [-p BIND_PORT] [-n POOL_SIZE]
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
