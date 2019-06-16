import sys
import argparse
import asyncio
import logging
import ssl
import signal
from functools import partial
from urllib.parse import urlparse

from sdnotify import SystemdNotifier

from .listener import Listener
from .constants import LogLevel
from . import utils
from .connpool import ConnPool


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pooling TLS wrapper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("dst_address",
                        help="target hostname")
    parser.add_argument("dst_port",
                        type=utils.check_port,
                        help="target port")
    parser.add_argument("-v", "--verbosity",
                        help="logging verbosity",
                        type=utils.check_loglevel,
                        choices=LogLevel,
                        default=LogLevel.info)
    parser.add_argument("-l", "--logfile",
                        help="log file location",
                        metavar="FILE")
    parser.add_argument("--disable-uvloop",
                        help="do not use uvloop even if it is available",
                        action="store_true")

    listen_group = parser.add_argument_group('listen options')
    listen_group.add_argument("-a", "--bind-address",
                              default="127.0.0.1",
                              help="bind address")
    listen_group.add_argument("-p", "--bind-port",
                              default=57800,
                              type=utils.check_port,
                              help="bind port")

    pool_group = parser.add_argument_group('pool options')
    pool_group.add_argument("-n", "--pool-size",
                            default=25,
                            type=utils.check_positive_int,
                            help="connection pool size")
    pool_group.add_argument("-B", "--backoff",
                            default=5,
                            type=utils.check_positive_float,
                            help="delay after connection attempt failure in seconds")
    pool_group.add_argument("-T", "--ttl",
                            default=30,
                            type=utils.check_positive_float,
                            help="lifetime of idle pool connection in seconds")
    pool_group.add_argument("-w", "--timeout",
                            default=4,
                            type=utils.check_positive_float,
                            help="server connect timeout")

    tls_group = parser.add_argument_group('TLS options')
    tls_group.add_argument("-c", "--cert",
                           help="use certificate for client TLS auth")
    tls_group.add_argument("-k", "--key",
                           help="key for TLS certificate")
    tls_group.add_argument("-C", "--cafile",
                           help="override default CA certs "
                           "by set specified in file")
    tls_group.add_argument("--no-hostname-check",
                           action="store_true",
                           help="do not check hostname in cert subject. "
                           "This option is useful for private PKI and "
                           "available only together with \"--cafile\"")
    return parser.parse_args()


async def amain(args, loop):  # pragma: no cover
    logger = logging.getLogger('MAIN')

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    if args.cafile:
        context.load_verify_locations(cafile=args.cafile)
    if args.no_hostname_check:
        if not args.cafile:
            logger.fatal("CAfile option is required when hostname check "
                         "is disabled. Terminating program.")
            sys.exit(2)
        context.check_hostname = False
    if args.cert:
        context.load_cert_chain(certfile=args.cert, keyfile=args.key)


    pool = ConnPool(dst_address=args.dst_address,
                    dst_port=args.dst_port,
                    ssl_context=context,
                    timeout=args.timeout,
                    backoff=args.backoff,
                    ttl=args.ttl,
                    size=args.pool_size,
                    loop=loop)
    await pool.start()
    server = Listener(listen_address=args.bind_address,
                      listen_port=args.bind_port,
                      timeout=args.timeout,
                      pool=pool,
                      loop=loop)
    await server.start()
    logger.info("Server started.")

    exit_event = asyncio.Event()
    beat = asyncio.ensure_future(utils.heartbeat())
    sig_handler = partial(utils.exit_handler, exit_event)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    notifier = await loop.run_in_executor(None, SystemdNotifier)
    await loop.run_in_executor(None, notifier.notify, "READY=1")
    await exit_event.wait()

    logger.debug("Eventloop interrupted. Shutting down server...")
    await loop.run_in_executor(None, notifier.notify, "STOPPING=1")
    beat.cancel()
    await server.stop()
    await pool.stop()


def main():  # pragma: no cover
    args = parse_args()
    with utils.AsyncLoggingHandler(args.logfile) as log_handler:
        logger = utils.setup_logger('MAIN', args.verbosity, log_handler)
        utils.setup_logger('Listener', args.verbosity, log_handler)
        utils.setup_logger('ConnPool', args.verbosity, log_handler)

        logger.info("Starting eventloop...")
        if not args.disable_uvloop:
            if utils.enable_uvloop():
                logger.info("uvloop enabled.")
            else:
                logger.info("uvloop is not available. "
                            "Falling back to built-in event loop.")

        loop = asyncio.get_event_loop()
        # workaround for Python bug on pending writes to SSL connections
        utils.ignore_ssl_error(loop)
        loop.run_until_complete(amain(args, loop))
        loop.close()
        logger.info("Server finished its work.")
