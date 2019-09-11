import asyncio
import logging
import collections
from functools import partial

from .constants import BUFSIZE
from .utils import wall_clock_sleep


class InappropriateRead(Exception):
    pass


class SuccessError(Exception):
    pass


class TTLExpired(Exception):
    pass


class ConnPool:
    def __init__(self, *,
                 dst_address,
                 dst_port,
                 ssl_context=True,
                 ssl_hostname=None,
                 timeout=5,
                 backoff=5,
                 ttl=30,
                 size=10,
                 loop=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._dst_address = dst_address
        self._dst_port = dst_port
        self._ssl_context = ssl_context
        self._ssl_hostname = ssl_hostname
        self._timeout = timeout
        self._ttl = ttl
        self._size = size
        self._backoff = backoff
        self._waiters = collections.deque()
        self._reserve = collections.deque()
        self._conn_builders = set()

    async def start(self):
        self._conn_builders = set(self._loop.create_task(self._build_conn())
                                  for _ in range(self._size))

    async def stop(self):
        while self._conn_builders:
            tasks = list(self._conn_builders)
            self._conn_builders.clear()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        for (reader, writer), _ in self._reserve:
            writer.close()

    async def _build_conn(self):
        async def fail():
            self._logger.debug("Failed upstream connection. Backoff for %d "
                               "seconds", self._backoff)
            await wall_clock_sleep(self._backoff)

        async def fail_corrupted():
            self._logger.warning("Upstream connection corrupted. Backoff for"
                                 " %d seconds", self._backoff)
            await wall_clock_sleep(self._backoff)

        async def reader_guard(reader):
            try:
                await reader.read(1)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.debug("reader_guard catched exception on "
                                   "reader.read(): %s", str(exc))
            raise InappropriateRead()

        async def waiter_guard(event):
            await event.wait()
            raise SuccessError()

        async def timeout_guard(timeout):
            await wall_clock_sleep(timeout)
            raise TTLExpired()

        async def taker(grabbed, read_task):
            grabbed.set()
            if read_task.done():
                raise InapproptiateRead()
            else:
                try:
                    await read_task
                except asyncio.CancelledError:
                    pass
                else:
                    raise InappropriateRead()

        def try_remove_from_queue(elem):
            try:
                self._reserve.remove(elem)
            except ValueError:
                self._logger.debug("Not found expired connection "
                                   "in reserve. This should not happen.")
            else:
                elem[0][1].close()

        while True:
            try:
                try:
                    conn = await asyncio.wait_for(
                        asyncio.open_connection(self._dst_address,
                                                self._dst_port,
                                                ssl=self._ssl_context,
                                                server_hostname=self._ssl_hostname),
                        self._timeout)
                except asyncio.TimeoutError:
                    self._logger.error("Connection to upstream timed out.")
                    await fail()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._logger.exception("Got exception while connecting to upstream: %s", str(exc))
                    await fail()
                else:
                    self._logger.debug("Successfully built upstream connection.")
                    while self._waiters:
                        fut = self._waiters.popleft()
                        if not fut.cancelled():
                            self._logger.warning("Pool exhausted. Dispatching connection directly to waiter!")
                            fut.set_result(conn)
                            break
                    else:
                        grabbed = asyncio.Event()

                        read_task = asyncio.ensure_future(reader_guard(conn[0]))
                        tasks = [
                            asyncio.ensure_future(waiter_guard(grabbed)),
                            asyncio.ensure_future(timeout_guard(self._ttl)),
                            read_task,
                        ]

                        elem = (conn, partial(taker, grabbed, read_task))
                        self._reserve.append(elem)

                        try:
                            await asyncio.gather(*tasks)
                        except InappropriateRead:
                            if not grabbed.is_set():
                                try_remove_from_queue(elem)
                            await fail_corrupted()
                        except TTLExpired:
                            if not grabbed.is_set():
                                try_remove_from_queue(elem)
                        except SuccessError:
                            pass
                        finally:
                            for task in tasks:
                                if not task.done():
                                    task.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.exception("_build_conn crashed with exception: %s",
                                       str(exc))
                    
    async def get(self):
        while True:
            if self._reserve:
                conn, take = self._reserve.popleft()
                try:
                    await take()
                except InappropriateRead:
                    pass
                else:
                    self._logger.debug("Obtained connection from pool.")
                    return conn
            else:
                fut = self._loop.create_future()
                self._waiters.append(fut)
                self._logger.debug("Awaiting for free connection.")
                return await fut
