import struct
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any


class DataType(ABC):
    def __init__(self, value: bytes | Any):
        if isinstance(value, bytes):
            self.value = self.unpack(BytesIO(value))
            self.packed = value
        else:
            self.value = value
            self.packed = self.pack(value)

    @staticmethod
    @abstractmethod
    def pack(value):
        pass

    @staticmethod
    @abstractmethod
    def unpack(value):
        pass


class VarInt(DataType):
    def __repr__(self) -> str:
        return str(self.value)

    # https://gist.github.com/nickelpro/7312782
    @staticmethod
    def pack(value: int) -> bytes:
        total = b""
        val = (1 << 32) + value if value < 0 else value

        while val >= 0x80:
            bits = val & 0x7F
            val >>= 7
            total += struct.pack("B", (0x80 | bits))

        bits = val & 0x7F
        total += struct.pack("B", bits)
        return total

    @staticmethod
    def unpack(buff: BytesIO) -> int:
        total = 0
        shift = 0
        val = 0x80

        while val & 0x80:
            val = struct.unpack("B", buff.read(1))[0]
            total |= (val & 0x7F) << shift
            shift += 7

        return total - (1 << 32) if total & (1 << 31) else total

    @staticmethod
    async def unpack_stream(stream) -> int:
        total = 0
        shift = 0
        val = 0x80

        while (val & 0x80) and (data := await stream.read(1)):
            val = struct.unpack("B", data)[0]
            total |= (val & 0x7F) << shift
            shift += 7

        return total - (1 << 32) if total & (1 << 31) else total


class String(DataType):
    @staticmethod
    def pack(value: str) -> bytes:
        return VarInt(len(value)).packed + value.encode("utf-8")

    @staticmethod
    def unpack(buff: BytesIO) -> str:
        length = VarInt.unpack(buff)
        return buff.read(length).decode("utf-8")


class UnsignedShort(DataType):
    @staticmethod
    def pack(value: int) -> bytes:
        return struct.pack(">H", value)

    @staticmethod
    def unpack(buff: BytesIO) -> int:
        return struct.unpack(">H", buff.read(2))[0]


class Short(DataType):
    @staticmethod
    def pack(value: int) -> bytes:
        return struct.pack(">h", value)

    @staticmethod
    def unpack(buff: BytesIO) -> int:
        return struct.unpack(">h", buff.read(2))[0]


class Long(DataType):
    @staticmethod
    def pack(value: int) -> bytes:
        return struct.pack(">q", value)

    @staticmethod
    def unpack(buff: BytesIO) -> int:
        return struct.unpack(">q", buff.read(8))[0]


class ByteArray(DataType):
    @staticmethod
    def pack(value: bytes) -> bytes:
        return VarInt.pack(len(value)) + value

    @staticmethod
    def unpack(buff: BytesIO) -> bytes:
        length = VarInt.unpack(buff)
        return buff.read(length)


class BuffIO(BytesIO):
    def unpack(self, kind: DataType):
        return kind.unpack(self)
