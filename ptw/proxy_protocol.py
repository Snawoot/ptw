from abc import ABC, abstractmethod
import string
import enum
import socket
import struct

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


PPV2SIG = b'\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A'
PPV2StructIPv4 = struct.Struct("!12sBBH" "4s4sHH")
PPV2StructIPv6 = struct.Struct("!12sBBH" "16s16sHH")
PPV2StructUNKNOWN = struct.Struct("!12sBBH")
PPV2VER = 2
PPV2PROXYCMD = 1
PPV2VERCMD = ((PPV2VER << 4) | PPV2PROXYCMD)
PPV2TCPOVERIPV4 = 0x11
PPV2TCPOVERIPV6 = 0x21
PPV2UNKNOWNAF = 0x0
PPV2UNKNOWNAF_ADDRLEN = 0x0
PPV2TCPOVERIPV4_ADDRLEN = 12
PPV2TCPOVERIPV6_ADDRLEN = 36


class ProxyProtocolV2(BaseProxyProtocol):
    def prologue(self, src, dst):
        src_ip, src_port = src
        dst_ip, dst_port = dst
        src_af = detect_af(src_ip)
        dst_af = detect_af(src_ip)
        if src_af != dst_af:
            raise ValueError("Protocol AF mismatch!")
        src_addr_packed = socket.inet_pton(src_af, src_ip)
        dst_addr_packed = socket.inet_pton(dst_af, dst_ip)
        if src_af == socket.AF_INET:
            # IPv4
            res = PPV2StructIPv4.pack(PPV2SIG, PPV2VERCMD, PPV2TCPOVERIPV4,
                                      PPV2TCPOVERIPV4_ADDRLEN,
                                      src_addr_packed,
                                      dst_addr_packed,
                                      src_port,
                                      dst_port)
        elif src_af == socket.AF_INET6:
            # IPv6
            res = PPV2StructIPv6.pack(PPV2SIG, PPV2VERCMD, PPV2TCPOVERIPV6,
                                      PPV2TCPOVERIPV6_ADDRLEN,
                                      src_addr_packed,
                                      dst_addr_packed,
                                      src_port,
                                      dst_port)
        else:
            res = PPV2StructUNKNOWN.pack(PPV2SIG, PPV2VERCMD, PPV2UNKNOWNAF,
                                      PPV2UNKNOWNAF_ADDRLEN)
        return res


class ProxyProtocol(enum.Enum):
    none = None
    v1 = ProxyProtocolV1
    v2 = ProxyProtocolV2

    def __str__(self):
        return self.name


def check_proxyprotocol(arg):
    try:
        return ProxyProtocol[arg]
    except (IndexError, KeyError):
        raise argparse.ArgumentTypeError("%s is not valid proxy-protocol" % (repr(arg),))
