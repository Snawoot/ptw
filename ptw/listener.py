import asyncio
import weakref
import logging
import collections
from functools import partial

from .constants import BUFSIZE


class Listener:  # pylint: disable=too-many-instance-attributes
    def __init__(self, *,
                 listen_address,
                 listen_port,
                 pool,
                 timeout=None,
                 loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._listen_address = listen_address
        self._listen_port = listen_port
        self._children = weakref.WeakSet()
        self._server = None
        self._conn_pool = pool

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

    async def _pump(self, writer, reader, halt):
        hlt_task = asyncio.ensure_future(halt.wait())
        try:
            while True:
                rd_task = asyncio.ensure_future(reader.read(BUFSIZE))
                try:
                    done, pending = await asyncio.wait((rd_task, hlt_task),
                                                       return_when=asyncio.FIRST_COMPLETED)
                except asyncio.CancelledError:
                    rd_task.cancel()
                    hlt_task.cancel()
                    raise
                if hlt_task in done:
                    rd_task.cancel()
                    break
                data = rd_task.result()
                if not data:
                    halt.set()
                    break
                writer.write(data)
                wr_task = asyncio.ensure_future(writer.drain())
                try:
                    done, pending = await asyncio.wait((wr_task, hlt_task),
                                                       return_when=asyncio.FIRST_COMPLETED)
                except asyncio.CancelledError:
                    wr_task.cancel()
                    hlt_task.cancel()
                if hlt_task in done:
                    wr_task.cancel()
                    break
        finally:
            halt.set()

    async def handler(self, reader, writer):
        peer_addr = writer.transport.get_extra_info('peername')
        self._logger.info("Client %s connected", str(peer_addr))
        try:
            halt = asyncio.Event()
            dst_reader, dst_writer = await self._conn_pool.get() 
            await asyncio.gather(self._pump(writer, dst_reader, halt),
                                 self._pump(dst_writer, reader, halt))
        except asyncio.CancelledError:  # pylint: disable=try-except-raise
            raise
        except Exception as exc:  # pragma: no cover
            self._logger.exception("Connection handler stopped with exception:"
                                   " %s", str(exc))
        finally:
            self._logger.info("Client %s disconnected", str(peer_addr))
            dst_writer.close()
            writer.close()

    async def start(self):
        def _spawn(reader, writer):
            self._children.add(
                self._loop.create_task(self.handler(reader, writer)))

        self._server = await asyncio.start_server(_spawn,
                                                  self._listen_address,
                                                  self._listen_port)
        self._logger.info("Server ready.")
