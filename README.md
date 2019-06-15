# ptw

Pooling TLS Wrapper

## Requirements

* Python 3.5.3+

## Installation

```
pip3 install -U .
```

## Synopsis

```
$ ptw --help
usage: ptw [-h] [-v {debug,info,warn,error,fatal}] [--disable-uvloop]
           [-a BIND_ADDRESS] [-p BIND_PORT] [-n POOL_SIZE] [-B BACKOFF]
           [-T TTL] [-w TIMEOUT] [-c CERT] [-k KEY] [-C CAFILE]
           [--no-hostname-check]
           dst_address dst_port

Pooling TLS wrapper

positional arguments:
  dst_address           target hostname
  dst_port              target port

optional arguments:
  -h, --help            show this help message and exit
  -v {debug,info,warn,error,fatal}, --verbosity {debug,info,warn,error,fatal}
                        logging verbosity (default: info)
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

timing options:
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
```
