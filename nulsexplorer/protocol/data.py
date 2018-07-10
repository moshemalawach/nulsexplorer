from hashlib import sha256

PLACE_HOLDER = b"\xFF\xFF\xFF\xFF"

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

def hash_twice(buffer):
    return sha256(sha256(buffer).digest()).digest()
