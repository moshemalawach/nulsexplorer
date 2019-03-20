from hashlib import sha256
from binascii import hexlify, unhexlify
try:
    from secp256k1 import PrivateKey, PublicKey
except ImportError:
    print("Can't import secp256k1, can't verify and sign tx.")
import six
import time
import struct
import hashlib

PLACE_HOLDER = b"\xFF\xFF\xFF\xFF"
ADDRESS_LENGTH = 23
HASH_LENGTH = 34

B58_DIGITS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
MESSAGE_TEMPLATE = "\x18NULS Signed Data:\n%b"

COIN_UNIT = 100000000
CHEAP_UNIT_FEE = 100000
UNIT_FEE = 1000000
KB = 1024

def getxor(body):
    xor = 0
    for c in body:
        xor ^= c
    return xor

def b58_encode(b):
    """Encode bytes to a base58-encoded string"""

    # Convert big-endian bytes to integer
    n = int('0x0' + hexlify(b).decode('utf8'), 16)

    # Divide that integer into bas58
    res = []
    while n > 0:
        n, r = divmod (n, 58)
        res.append(B58_DIGITS[r])
    res = ''.join(res[::-1])

    # Encode leading zeros as base58 zeros
    czero = 0
    pad = 0
    for c in b:
        if c == czero: pad += 1
        else: break

    return B58_DIGITS[0] * pad + res

def b58_decode(s):
    """Decode a base58-encoding string, returning bytes"""
    if not s:
        return b''

    # Convert the string to an integer
    n = 0
    for c in s:
        n *= 58
        if c not in B58_DIGITS:
            raise ValueError('Character %r is not a valid base58 character' % c)
        digit = B58_DIGITS.index(c)
        n += digit

    # Convert the integer to bytes
    h = '%x' % n
    if len(h) % 2:
        h = '0' + h
    res = unhexlify(h.encode('utf8'))

    # Add padding back.
    pad = 0
    for c in s[:-1]:
        if c == B58_DIGITS[0]: pad += 1
        else: break

    return b'\x00' * pad + res

def address_from_hash(addr):
    return b58_encode(addr+bytes((getxor(addr), )))

def hash_from_address(hash):
    return b58_decode(hash)[:-1]

def public_key_to_hash(pub_key, chain_id=8964, address_type=1):
    sha256_digest = hashlib.sha256(pub_key).digest()
    md160_digest = hashlib.new('ripemd160', sha256_digest).digest()
    computed_address = bytes(struct.pack("h", chain_id)) + \
                       bytes([address_type]) + md160_digest
    return computed_address

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

class NulsSignature(BaseNulsData):
    ALG_TYPE = 0 # only one for now...

    def __init__(self, data=None):
        self.pub_key = None
        self.digest_bytes = None
        self.sig_ser = None
        if data is not None:
            self.parse(data)

    def parse(self, buffer, cursor=0):
        pos, self.pub_key = read_by_length(buffer, cursor)
        cursor += pos
        self.ecc_type = buffer[cursor]
        cursor += 1
        pos, self.sig_ser = read_by_length(buffer, cursor)
        cursor += pos
        return cursor

    @classmethod
    def sign_data(cls, pri_key, digest_bytes):
        privkey = PrivateKey(pri_key, raw=True) # we expect to have a private key as bytes. unhexlify it before passing.
        item = cls()
        item.pub_key = privkey.pubkey.serialize()
        item.digest_bytes = digest_bytes
        sig_check = privkey.ecdsa_sign(digest_bytes, raw=True)
        item.sig_ser = privkey.ecdsa_serialize(sig_check)
        return item

    @classmethod
    def sign_message(cls, pri_key, message):
        # we expect to have a private key as bytes. unhexlify it before passing
        privkey = PrivateKey(pri_key, raw=True)
        item = cls()
        message = VarInt(len(message)).encode() + message
        item.pub_key = privkey.pubkey.serialize()
        # item.digest_bytes = digest_bytes
        sig_check = privkey.ecdsa_sign(MESSAGE_TEMPLATE % message)
        item.sig_ser = privkey.ecdsa_serialize(sig_check)
        return item

    def serialize(self, with_length=False):
        output = b''
        output += write_with_length(self.pub_key)
        output += bytes([0])  # alg ecc type
        output += write_with_length(self.sig_ser)
        if with_length:
            return write_with_length(output)
        else:
            return output

    def verify(self, message):
        pub = PublicKey(self.pub_key, raw=True)
        message = VarInt(len(message)).encode() + message
        try:
            sig_raw = pub.ecdsa_deserialize(self.sig_ser)
            good = pub.ecdsa_verify(MESSAGE_TEMPLATE % message, sig_raw)
        except Exception:
            good = False
        return good


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

    def parse(self, buffer, cursor=0):
        self.alg_type = buffer[cursor]
        pos, self.digest_bytes = read_by_length(buffer, cursor=cursor+1)

    def serialize(self):
        return bytes([self.alg_type, len(self.digest_bytes)]) + self.digest_bytes

    def __str__(self):
        return self.serialize().hex()

def read_by_length(buffer, cursor=0, check_size=True):
    if check_size:
        fc = VarInt()
        fc.parse(buffer, cursor)
        length = fc.value
        size = fc.originallyEncodedSize
    else:
        length = buffer[cursor]
        size = 1

    value = buffer[cursor+size:cursor+size+length]
    return (size+length, value)

def write_with_length(buffer):
    if len(buffer) < 253:
        return bytes([len(buffer)]) + buffer
    else:
        return VarInt(len(buffer)).encode() + buffer

def timestamp_from_time(timedata):
    return int(time.mktime(timedata.timetuple())*1000)

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

def parse_varint(buffer, cursor):
    fc = VarInt()
    fc.parse(buffer, cursor)
    return (fc.originallyEncodedSize+cursor, fc.value)

def write_varint(value):
    return VarInt(value).encode()

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
            #value = SerializeUtils.readUint32LE(buf, offset + 1)
            self.value = struct.unpack("<I", buf[offset+1:offset+5])[0]
            # 1 marker + 4 data bytes (32 bits)
            self.originallyEncodedSize = 5

        else:
            #value = SerializeUtils.readInt64LE(buf, offset + 1)
            self.value = struct.unpack("<Q", buf[offset+1:offset+9])[0]
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
            return bytes((253, self.value&255, self.value >> 8))
        elif size == 5:
            return bytes((254, )) + writeUint32(self.value)
        else:
            return bytes((255, )) + writeUint64(self.value)

def sign_message(pri_key, message):
    privkey = PrivateKey(pri_key, raw=True) # we expect to have a private key as bytes. unhexlify it before passing.

    sig_check = privkey.ecdsa_sign(MESSAGE_TEMPLATE.format(message))
    sig_ser, recid = privkey.ecdsa_recoverable_serialize(sig_check)

    return (sig_ser, recid)

def sign_recoverable_message(pri_key, message):
    privkey = PrivateKey(pri_key, raw=True) # we expect to have a private key as bytes. unhexlify it before passing.

    sig_check = privkey.ecdsa_sign_recoverable(MESSAGE_TEMPLATE.format(message))
    sig_ser, recid = privkey.ecdsa_recoverable_serialize(sig_check)

    return (sig_ser, recid)

def verify_recoverable_message(signature, message, recid):
    """ Verifies a signature of a hash and returns the address that signed it.
    If no address is returned, signature is bad.
    """
    empty = PublicKey(flags=ALL_FLAGS)
    sig = empty.ecdsa_recoverable_deserialize(signature, args.recid)
    msg = MESSAGE_TEMPLATE.format(message)
    pubkey = empty.ecdsa_recover(msg, sig)
    addr_hash = public_key_to_hash(pubkey.serialize())
    address = address_from_hash(address)

    try:
        sig_raw = pub.ecdsa_deserialize(signature)
        good = pub.ecdsa_verify(message, sig_raw)
    except:
        good = False

    if good:
        return address
    else:
        return None
