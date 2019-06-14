import asyncio
import weakref
import logging
import collections
from functools import partial

from .constants import BUFSIZE

class ConnPool:
    def __init__(self, *,
                 dst_address,
                 dst_port,
                 ssl_context=True,
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
        self._timeout = timeout
        self._ttl = ttl
        self._conn_debt = size
        self._backoff = backoff
        self._waiters = collections.deque()
        self._reserve = collections.deque()
        self._respawn_required = asyncio.Event()
        self._respawn_required.set()
        self._respawn_coro = None
        self._conn_builders = set()

    async def start(self):
        self._respawn_coro = self._loop.create_task(self._pool_stabilizer())

    async def stop(self):
        self._respawn_coro.cancel()
        while self._conn_builders:
            tasks = list(self._conn_builders)
            self._conn_builders.clear()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        tasks = []
        for (reader, writer), _ in self._reserve:
            writer.close()
            tasks.append(writer.wait_closed())
        await asyncio.gather(*tasks, return_exceptions=True)

    def _spend_conn(self):
        self._conn_debt += 1
        self._respawn_required.set()

    async def _build_conn(self):
        async def fail():
            self._logger._debug("Failed upstream connection. Backoff for %d "
                                "seconds", self._backoff)
            await asyncio.sleep(self._backoff)
            self._spend_conn()

        try:
            conn = await asyncio.wait_for(
                asyncio.open_connection(self._dst_address,
                                        self._dst_port,
                                        ssl=self._ssl_context),
                self._timeout)
        except asyncio.TimeoutError:
            self._logger.error("Connection to upstream timed out.")
            await fail()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._logger.error("Got exception during upstream connection: %s", str(exc))
            await fail()
        else:
            self._logger.debug("Successfully built upstream connection.")
            if self._waiters:
                self._logger.warning("Dispatching connection directly to waiter!")
                fut = self._waiters.popleft()
                fut.set_result(conn)
            else:
                grabbed = asyncio.Event()
                elem = (conn, grabbed)
                self._reserve.append(elem)
                try:
                    await asyncio.wait_for(grabbed.wait(), self._ttl)
                except asyncio.TimeoutError:
                    try:
                        self._reserve.remove(elem)
                    except ValueError:
                        self._logger.debug("Not found expired connection "
                                           "in reserve. This should not happen.")
                    else:
                        self._spend_conn()
                        conn[1].close()
                    

    async def _pool_stabilizer(self):
        def _builder_done_cb(t, fut):
            self._conn_builders.discard(t)

        while True:
            await self._respawn_required.wait()
            self._logger.debug("_pool_stabilizer kicks in: got %d connections "
                               "to make", self._conn_debt)
            for _ in range(self._conn_debt):
                t = self._loop.create_task(self._build_conn())
                self._conn_builders.add(t)
                t.add_done_callback(partial(_builder_done_cb, t))
            self._respawn_required.clear()
            self._conn_debt = 0

    async def get(self):
        self._spend_conn()
        if self._reserve:
            conn, event = self._reserve.popleft()
            event.set()
            return conn
        else:
            fut = self._loop.create_future()
            self._waiters.append(fut)
            return await fut


class Listener:  # pylint: disable=too-many-instance-attributes
    def __init__(self, *,
                 listen_address,
                 listen_port,
                 dst_address,
                 dst_port,
                 ssl_context,
                 timeout=None,
                 loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._listen_address = listen_address
        self._listen_port = listen_port
        self._children = weakref.WeakSet()
        self._server = None
        self._conn_pool = ConnPool(dst_address=dst_address,
                                   dst_port=dst_port,
                                   ssl_context=ssl_context,
                                   timeout=timeout,
                                   backoff=5,
                                   ttl=30,
                                   size=10,
                                   loop=self._loop)

    async def stop(self):
        await self._conn_pool.stop()
        self._server.close()
        await self._server.wait_closed()
        while self._children:
            children = list(self._children)
            self._children.clear()
            self._logger.debug("Cancelling %d client handlers...",
                               len(children))
            for task in children:
                task.cancel()
            await asyncio.wait(children)
            # workaround for TCP server keeps spawning handlers for a while
            # after wait_closed() completed
            await asyncio.sleep(.5)

    async def _pump(self, writer, reader):
        try:
            while True:
                data = await reader.read(BUFSIZE)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        finally:
            writer.close()

    async def handler(self, reader, writer):
        peer_addr = writer.transport.get_extra_info('peername')
        self._logger.info("Client %s connected", str(peer_addr))
        try:
            dst_reader, dst_writer = await self._conn_pool.get() 
            await asyncio.gather(self._pump(writer, dst_reader),
                                 self._pump(dst_writer, reader))
        except asyncio.CancelledError:  # pylint: disable=try-except-raise
            raise
        except Exception as exc:  # pragma: no cover
            self._logger.exception("Connection handler stopped with exception:"
                                   " %s", str(exc))
        finally:
            self._logger.info("Client %s disconnected", str(peer_addr))
            writer.close()

    async def start(self):
        await self._conn_pool.start()
        def _spawn(reader, writer):
            self._children.add(
                self._loop.create_task(self.handler(reader, writer)))

        self._server = await asyncio.start_server(_spawn,
                                                  self._listen_address,
                                                  self._listen_port)
        self._logger.info("Server ready.")
