from hashlib import sha256
import six

PLACE_HOLDER = b"\xFF\xFF\xFF\xFF"
ADDRESS_LENGTH = 23
HASH_LENGTH = 34

class BaseNulsData:
    def _pre_parse(buffer, cursor=None, length=None):
        if cursor is not None:
            buffer = buffer[cursor:]
        if length is not None:
            buffer = buffer[:length]

        if (bytes is None) or (len(bytes) == 0) or (len(bytes) == 4) or (bytes == PLACE_HOLDER):
            return

    def _prepare(self, item):
        if item is None:
            return PLACE_HOLDER
        else:
            return item.serialize()

class NulsDigestData(BaseNulsData):
    HASH_LENGTH = 34
    DIGEST_ALG_SHA256 = 0
    DIGEST_ALG_SHA160 = 1

    def __init__(self, data=None, alg_type=None):
        self.digest_bytes = None
        self.alg_type = None

        if data is not None and alg_type is None:
            self.parse(data)

        elif data is not None and alg_type is not None:
            self.digest_bytes = data
            self.alg_type = alg_type

    @property
    def size(self):
        return self.HASH_LENGTH

    def parse(self, buffer):
        self.alg_type = buffer[0]
        self.digest_bytes = read_by_length(buffer, cursor=1)

    def serialize(self):
        return bytes([self.alg_type, len(self.digest_bytes)]) + self.digest_bytes

    def __str__(self):
        return self.serialize().hex()

def read_by_length(buffer, cursor=None):
    if cursor is not None:
        buffer = buffer[cursor:]

    length = buffer[0]
    value = buffer[1:length+1]
    return value

def write_with_length(buffer):
    return bytes([len(buffer)]) + buffer

def readUint48(buffer, cursor=0):
    """ wtf...
    """
    value = (buffer[cursor + 0] & 0xff) | \
            ((buffer[cursor + 1] & 0xff) << 8) | \
            ((buffer[cursor + 2] & 0xff) << 16) | \
            ((buffer[cursor + 3] & 0xff) << 24) | \
            ((buffer[cursor + 4] & 0xff) << 32) | \
            ((buffer[cursor + 5] & 0xff) << 40)

    # "todo" here, why ?
    cursor += 6;
    if (value == 281474976710655):
        return -1

    return value

def writeUint48(val):
    nval = bytes([(0xFF & val),
                   (0xFF & (val >> 8)),
                   (0xFF & (val >> 16)),
                   (0xFF & (val >> 24)),
                   (0xFF & (val >> 32)),
                   (0xFF & (val >> 40))])
    return nval

def _byte(b):
    return bytes((b, ))

def writeVarInt(number):
    """Pack `number` into varint bytes"""
    buf = b''
    while True:
        towrite = number & 0x7f
        number >>= 7
        if number:
            buf += _byte(towrite | 0x80)
        else:
            buf += _byte(towrite)
            break
    return buf

def hash_twice(buffer):
    return sha256(sha256(buffer).digest()).digest()


def writeUint32(val):
    return bytes([(0xFF & val),
                  (0xFF & (val >> 8)),
                  (0xFF & (val >> 16)),
                  (0xFF & (val >> 24))])

def writeUint64(val):
    return bytes([(0xFF & val),
                  (0xFF & (val >> 8)),
                  (0xFF & (val >> 16)),
                  (0xFF & (val >> 24)),
                  (0xFF & (val >> 32)),
                  (0xFF & (val >> 40)),
                  (0xFF & (val >> 48)),
                  (0xFF & (val >> 56))])

class VarInt:
    # public final long value;
    # private final int originallyEncodedSize;

    def __init__(self, value=None):
        self.value = value
        self.originallyEncodedSize = 1
        if value is not None:
            self.originallyEncodedSize = self.getSizeInBytes()

    def parse(self, buf, offset):
        first = 0xFF & buf[offset]
        if (first < 253):
            self.value = first
            # 1 data byte (8 bits)
            self.originallyEncodedSize = 1

        elif (first == 253):
            self.value = (0xFF & buf[offset + 1]) | ((0xFF & buf[offset + 2]) << 8)
            # 1 marker + 2 data bytes (16 bits)
            self.originallyEncodedSize = 3

        elif (first == 254):
            value = SerializeUtils.readUint32LE(buf, offset + 1)
            # 1 marker + 4 data bytes (32 bits)
            self.originallyEncodedSize = 5

        else:
            value = SerializeUtils.readInt64LE(buf, offset + 1)
            # 1 marker + 8 data bytes (64 bits)
            self.originallyEncodedSize = 9

    def getOriginalSizeInBytes(self):
        return self.originallyEncodedSize

    def getSizeInBytes(self):
        return self.sizeOf(self.value)

    @classmethod
    def sizeOf(cls, value):
        # if negative, it's actually a very large unsigned long value
        if (value < 0):
            # 1 marker + 8 data bytes
            return 9

        if (value < 253):
            # 1 data byte
            return 1

        if (value <= 0xFFFF):
            # 1 marker + 2 data bytes
            return 3

        if (value <= 0xFFFFFFFF):
            # 1 marker + 4 data bytes
            return 5

        # 1 marker + 8 data bytes
        return 9

# //    /**
# //     * Encodes the value into its minimal representation.
# //     *
# //     * @return the minimal encoded bytes of the value
# //     */
    def encode(self):
        ob = bytes()
        size = self.sizeOf(self.value)

        if size == 1:
            return bytes((self.value, ))
        elif size == 3:
            return bytes((253, self.value, self.value >> 8))
        elif size == 5:
            return bytes((254, )) + writeUint32(self.value)
        else:
            return bytes((255, )) + writeUint64(self.value)
