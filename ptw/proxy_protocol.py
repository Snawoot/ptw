from abc import ABC, abstractmethod
import string
import enum
import socket

from .utils import detect_af


af_map = {
    socket.AF_INET: "TCP4",
    socket.AF_INET6: "TCP6",
}


class BaseProxyProtocol(ABC):
    @abstractmethod
    def prologue(self, src, dst):
        """ Returns bytes with prologue data. Accepts original
        source and destination of TCP connection. 
        Params: src, dst
        Each of them is a pair of host (IP as str) and port (int) """


class ProxyProtocolV1(BaseProxyProtocol):
    def prologue(self, src, dst):
        src_ip, src_port = src
        dst_ip, dst_port = dst
        src_af = detect_af(src_ip)
        dst_af = detect_af(src_ip)
        if src_af != dst_af:
            raise ValueError("Protocol AF mismatch!")
        if src_af not in af_map:
            return b"PROXY UNKNOWN\r\n"
        else:
            res= ("PROXY " + af_map[src_af] + " " + 
                  src_ip + " " + dst_ip + " " +
                  str(src_port) + " " + str(dst_port) + "\r\n").encode('ascii')
            if len(res) >= 108:
                raise RuntimeError("Produced string is too long for proxy-protocol")
            return res


class ProxyProtocol(enum.Enum):
    none = None
    v1 = ProxyProtocolV1

    def __str__(self):
        return self.name


def check_proxyprotocol(arg):
    try:
        return ProxyProtocol[arg]
    except (IndexError, KeyError):
        raise argparse.ArgumentTypeError("%s is not valid proxy-protocol" % (repr(arg),))
