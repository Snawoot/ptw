import asyncio
import argparse
import logging
import ssl
import os

from . import constants


def ignore_ssl_error(loop):
    """Ignore aiohttp #3535 issue with SSL data after close

    There appears to be an issue on Python 3.7 and aiohttp SSL that throws a
    ssl.SSLError fatal error (ssl.SSLError: [SSL: KRB5_S_INIT] application data
    after close notify (_ssl.c:2609)) after we are already done with the
    connection. See GitHub issue aio-libs/aiohttp#3535

    Given a loop, this sets up a exception handler that ignores this specific
    exception, but passes everything else on to the previous exception handler
    this one replaces.

    """
    orig_handler = loop.get_exception_handler()

    def ignore_ssl_error(loop, context):
        if context.get('message') == 'SSL error in data received':
            # validate we have the right exception, transport and protocol
            exception = context.get('exception')
            protocol = context.get('protocol')
            if (
                isinstance(exception, ssl.SSLError) and exception.reason == 'KRB5_S_INIT' and
                isinstance(protocol, asyncio.sslproto.SSLProtocol) and
                'application data after close notify' in exception.strerror
            ):
                if loop.get_debug():
                    asyncio.log.logger.debug('Ignoring aiohttp SSL KRB5_S_INIT error')
                return
        if orig_handler is not None:
            orig_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(ignore_ssl_error)


def setup_logger(name, verbosity):
    logger = logging.getLogger(name)
    logger.setLevel(verbosity)
    handler = logging.StreamHandler()
    handler.setLevel(verbosity)
    handler.setFormatter(logging.Formatter('%(asctime)s '
                                           '%(levelname)-8s '
                                           '%(name)s: %(message)s',
                                           '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    return logger


def check_port(value):
    def fail():
        raise argparse.ArgumentTypeError(
            "%s is not a valid port number" % value)
    try:
        ivalue = int(value)
    except ValueError:
        fail()
    if not 0 < ivalue < 65536:
        fail()
    return ivalue


def check_positive_float(value):
    def fail():
        raise argparse.ArgumentTypeError(
            "%s is not a valid value" % value)
    try:
        fvalue = float(value)
    except ValueError:
        fail()
    if fvalue <= 0:
        fail()
    return fvalue


def check_positive_int(value):
    def fail():
        raise argparse.ArgumentTypeError(
            "%s is not a valid value" % value)
    try:
        fvalue = int(value)
    except ValueError:
        fail()
    if fvalue <= 0:
        fail()
    return fvalue


def check_loglevel(arg):
    try:
        return constants.LogLevel[arg]
    except (IndexError, KeyError):
        raise argparse.ArgumentTypeError("%s is not valid loglevel" % (repr(arg),))


def enable_uvloop():  # pragma: no cover
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        return False
    else:
        return True


def exit_handler(exit_event, signum, frame):  # pragma: no cover pylint: disable=unused-argument
    logger = logging.getLogger('MAIN')
    if exit_event.is_set():
        logger.warning("Got second exit signal! Terminating hard.")
        os._exit(1)  # pylint: disable=protected-access
    else:
        logger.warning("Got first exit signal! Terminating gracefully.")
        exit_event.set()


async def heartbeat():
    """ Hacky coroutine which keeps event loop spinning with some interval
    even if no events are coming. This is required to handle Futures and
    Events state change when no events are occuring."""
    while True:
        await asyncio.sleep(.5)
