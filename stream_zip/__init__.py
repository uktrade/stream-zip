from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from struct import Struct
import asyncio
import secrets
import zlib
from typing import Any, Iterable, Generator, Tuple, Optional, Deque, Type, AsyncIterable, Callable

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA1
from Crypto.Util import Counter
from Crypto.Protocol.KDF import PBKDF2


################################
# Private sentinel objects/types

_NO_COMPRESSION_BUFFERED_32 = object()
_NO_COMPRESSION_BUFFERED_64 = object()
_NO_COMPRESSION_STREAMED_32 = object()
_NO_COMPRESSION_STREAMED_64 = object()
_ZIP_32 = object()
_ZIP_64 = object()

_AUTO_UPGRADE_CENTRAL_DIRECTORY = object()
_NO_AUTO_UPGRADE_CENTRAL_DIRECTORY = object()

# Used internally to fetch the (default) zlib Compress object
_CompressObjGetter = Callable[[], 'zlib._Compress']

# Used by the internals of stream_zip - a "public" Method is a tuple of 5 things that controls the
# format/process of making each member of the ZIP file.
_MethodTuple = Tuple[
    object,              # Sentinel of the methods above
    object,              # Sentinel of auto upgrade central directory or not
    _CompressObjGetter,  # Function to get the zlib Compress object for
    int,                 # The uncompressed size of the file for NO_COMPRESSION_STREAMED_* types
    int,                 # The CRC32 of the file for NO_COMPRESSION_STREAMED_* types
]

# A "Method" is an instance of a class that has a _get function that returns a _MethodTuple
class Method(ABC):
    @abstractmethod
    def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
        pass

class _ZIP_64_TYPE(Method):
    def _get(self, offset: int, default_get_compressobj: _CompressObjGetter)  -> _MethodTuple:
        return _ZIP_64, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, 0, 0

class _ZIP_32_TYPE(Method):
    def _get(self, offset: int, default_get_compressobj: _CompressObjGetter)  -> _MethodTuple:
        return _ZIP_32, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, 0, 0

class _NO_COMPRESSION_32_TYPE(Method):
    def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
        return _NO_COMPRESSION_BUFFERED_32, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, 0, 0

    def __call__(self, uncompressed_size: int, crc_32: int) -> Method:
        class _NO_COMPRESSION_32_TYPE_STREAMED_TYPE(Method):
            def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
                return _NO_COMPRESSION_STREAMED_32, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, uncompressed_size, crc_32

        return _NO_COMPRESSION_32_TYPE_STREAMED_TYPE()

class _NO_COMPRESSION_64_TYPE(Method):
    def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
        return _NO_COMPRESSION_BUFFERED_64, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, 0, 0

    def __call__(self, uncompressed_size: int, crc_32: int) -> Method:
        class _NO_COMPRESSION_64_TYPE_STREAMED_TYPE(Method):
            def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
                return _NO_COMPRESSION_STREAMED_64, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj, uncompressed_size, crc_32
        return _NO_COMPRESSION_64_TYPE_STREAMED_TYPE()

class _ZIP_AUTO_TYPE():
    def __call__(self, uncompressed_size: int, level: int=9) -> Method:
        # The limit of 4293656841 is calculated using the logic from a zlib function
        # https://github.com/madler/zlib/blob/04f42ceca40f73e2978b50e93806c2a18c1281fc/deflate.c#L696
        # Specifically, worked out by assuming the compressed size of a stream cannot be bigger than
        #
        # uncompressed_size + (uncompressed_size >> 12) + (uncompressed_size >> 14) + (uncompressed_size >> 25) + 7
        #
        # This is the 0.03% deflate bound for memLevel of 8 default abs(wbits) = MAX_WBITS
        #
        # Note that Python's interaction with zlib is not consistent between versions of Python
        # https://stackoverflow.com/q/76371334/1319998
        # so Python could be causing extra deflate-chunks output which could break the limit. However, couldn't
        # get output of sized 4293656841 to break the Zip32 bound of 0xffffffff here for any level, including 0

        class _ZIP_AUTO_TYPE_INNER(Method):
            def _get(self, offset: int, default_get_compressobj: _CompressObjGetter) -> _MethodTuple:
                method = _ZIP_64 if uncompressed_size > 4293656841 or offset > 0xffffffff else _ZIP_32
                return (method, _AUTO_UPGRADE_CENTRAL_DIRECTORY, lambda: zlib.compressobj(level=level, memLevel=8, wbits=-zlib.MAX_WBITS), 0, 0)

        return _ZIP_AUTO_TYPE_INNER()


###############################
# Public sentinel objects/types

# Methods / objects that return Methods (some of these are both)
ZIP_64 = _ZIP_64_TYPE()
ZIP_32 = _ZIP_32_TYPE()
NO_COMPRESSION_32 = _NO_COMPRESSION_32_TYPE()
NO_COMPRESSION_64 = _NO_COMPRESSION_64_TYPE()
ZIP_AUTO = _ZIP_AUTO_TYPE()

# Each member file is a tuple of its name, last modified date, file mode, Method, and its bytes
MemberFile = Tuple[str, datetime, int, Method, Iterable[bytes]]
AsyncMemberFile = Tuple[str, datetime, int, Method, AsyncIterable[bytes]]


def stream_zip(files: Iterable[MemberFile], chunk_size: int=65536,
               get_compressobj: _CompressObjGetter=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9),
               extended_timestamps: bool=True,
               password: Optional[str]=None,
               get_crypto_random: Callable[[int], bytes]=lambda num_bytes: secrets.token_bytes(num_bytes),
) -> Iterable[bytes]:

    def evenly_sized(chunks: Iterable[bytes]) -> Iterable[bytes]:
        chunk = b''
        offset = 0
        it = iter(chunks)

        def up_to(num: int) -> Iterable[bytes]:
            nonlocal chunk, offset

            while num:
                if offset == len(chunk):
                    try:
                        chunk = next(it)
                    except StopIteration:
                        break
                    else:
                        offset = 0
                to_yield = min(num, len(chunk) - offset)
                offset = offset + to_yield
                num -= to_yield
                yield chunk[offset - to_yield:offset]

        while True:
            block = b''.join(up_to(chunk_size))
            if not block:
                break
            yield block

    def get_zipped_chunks_uneven() -> Iterable[bytes]:
        local_header_signature = b'PK\x03\x04'
        local_header_struct = Struct('<HHH4sIIIHH')

        data_descriptor_signature = b'PK\x07\x08'
        data_descriptor_zip_64_struct = Struct('<IQQ')
        data_descriptor_zip_32_struct = Struct('<III')

        central_directory_header_signature = b'PK\x01\x02'
        central_directory_header_struct = Struct('<BBBBHH4sIIIHHHHHII')

        zip_64_end_of_central_directory_signature = b'PK\x06\x06'
        zip_64_end_of_central_directory_struct = Struct('<QHHIIQQQQ')

        zip_64_end_of_central_directory_locator_signature= b'PK\x06\x07'
        zip_64_end_of_central_directory_locator_struct = Struct('<IQI')

        end_of_central_directory_signature = b'PK\x05\x06'
        end_of_central_directory_struct = Struct('<HHHHIIH')
        
        zip_64_extra_signature = b'\x01\x00'
        zip_64_local_extra_struct = Struct('<2sHQQ')
        zip_64_central_directory_extra_struct = Struct('<2sHQQQ')

        mod_at_unix_extra_signature = b'UT'
        mod_at_unix_extra_struct = Struct('<2sH1sl')

        aes_extra_signature = b'\x01\x99'
        aes_extra_struct = Struct('<2sHH2sBH')

        modified_at_struct = Struct('<HH')

        aes_flag = 0b0000000000000001
        data_descriptor_flag = 0b0000000000001000
        utf8_flag = 0b0000100000000000

        central_directory: Deque[Tuple[bytes, bytes, bytes]] = deque()
        central_directory_size = 0
        central_directory_start_offset = 0
        zip_64_central_directory = False
        offset = 0

        def _(chunk: bytes) -> Iterable[bytes]:
            nonlocal offset
            offset += len(chunk)
            yield chunk

        def _raise_if_beyond(offset: int, maximum: int, exception_class: Type[Exception]) -> None:
            if offset > maximum:
                raise exception_class()

        def _with_returned(gen: Generator[bytes, None, Any]) -> Tuple[Callable[[], Any], Iterable[bytes]]:
            # We leverage the not-often used "return value" of generators. Here, we want to iterate
            # over chunks (to encrypt them), but still return the same "return value". So we use a
            # bit of a trick to extract the return value but still have access to the chunks as
            # we iterate over them

            return_value = None
            def with_return_value() -> Iterable[bytes]:
                nonlocal return_value
                return_value = yield from gen

            return ((lambda: return_value), with_return_value())

        def _encrypt_dummy(chunks: Generator[bytes, None, Any]) -> Generator[bytes, None, Any]:
            get_return_value, chunks_with_return = _with_returned(chunks)
            for chunk in chunks_with_return:
                yield from _(chunk)
            return get_return_value()

        # This slightly complex getter allows mypy to work out that the _encrypt_aes function is
        # only called when we have a non-None password, which then passes type checking for the
        # PBKDF2 function that the password is passed into
        def _get_encrypt_aes(password: str) -> Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]]:
            def _encrypt_aes(chunks: Generator[bytes, None, Any]) -> Generator[bytes, None, Any]:
                key_length = 32
                salt_length = 16
                password_verification_length = 2

                salt = get_crypto_random(salt_length)
                yield from _(salt)

                keys = PBKDF2(password, salt, 2 * key_length + password_verification_length, 1000)
                yield from _(keys[-password_verification_length:])

                encrypter = AES.new(
                    keys[:key_length], AES.MODE_CTR,
                    counter=Counter.new(nbits=128, little_endian=True),
                )
                hmac = HMAC.new(keys[key_length:key_length*2], digestmod=SHA1)

                get_return_value, chunks_with_return = _with_returned(chunks)
                for chunk in chunks_with_return:
                    encrypted_chunk = encrypter.encrypt(chunk)
                    hmac.update(encrypted_chunk)
                    yield from _(encrypted_chunk)

                yield from _(hmac.digest()[:10])

                return get_return_value()
            return _encrypt_aes

        def _zip_64_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

            extra = zip_64_local_extra_struct.pack(
                zip_64_extra_signature,
                16,  # Size of extra
                0,   # Uncompressed size - since data descriptor
                0,   # Compressed size - since data descriptor
            ) + mod_at_unix_extra + aes_extra
            flags = aes_flags | data_descriptor_flag | utf8_flag

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                flags,
                compression,
                mod_at_ms_dos,
                0,            # CRC32 - 0 since data descriptor
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            uncompressed_size, raw_compressed_size, crc_32 = yield from encryption_func(_zip_data(
                chunks,
                _get_compress_obj,
                max_uncompressed_size=0xffffffffffffffff,
                max_compressed_size=0xffffffffffffffff,
            ))
            compressed_size = raw_compressed_size + aes_size_increase
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip_64_struct.pack(masked_crc_32, compressed_size, uncompressed_size))

            extra = zip_64_central_directory_extra_struct.pack(
                zip_64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            ) + mod_at_unix_extra + aes_extra
            return central_directory_header_struct.pack(
                45,           # Version made by
                3,            # System made by (UNIX)
                45,           # Version required
                0,            # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
                0,            # File comment length
                0,            # Disk number
                0,            # Internal file attributes - is binary
                external_attr,
                0xffffffff,   # Offset of local header - since zip64
            ), name_encoded, extra

        def _zip_32_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffff, exception_class=OffsetOverflowError)

            extra = mod_at_unix_extra + aes_extra
            flags = aes_flags | data_descriptor_flag | utf8_flag

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,           # Version
                flags,
                compression,
                mod_at_ms_dos,
                0,            # CRC32 - 0 since data descriptor
                0,            # Compressed size - 0 since data descriptor
                0,            # Uncompressed size - 0 since data descriptor
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            uncompressed_size, raw_compressed_size, crc_32 = yield from encryption_func(_zip_data(
                chunks,
                _get_compress_obj,
                max_uncompressed_size=0xffffffff,
                max_compressed_size=0xffffffff,
            ))
            compressed_size = raw_compressed_size + aes_size_increase
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip_32_struct.pack(masked_crc_32, compressed_size, uncompressed_size))

            return central_directory_header_struct.pack(
                20,           # Version made by
                3,            # System made by (UNIX)
                20,           # Version required
                0,            # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
                0,            # File comment length
                0,            # Disk number
                0,            # Internal file attributes - is binary
                external_attr,
                file_offset,
            ), name_encoded, extra

        def _zip_data(chunks: Iterable[bytes], _get_compress_obj: _CompressObjGetter,
                      max_uncompressed_size: int, max_compressed_size: int) -> Generator[bytes, None, Tuple[int, int, int]]:
            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            compress_obj = _get_compress_obj()
            for chunk in chunks:
                uncompressed_size += len(chunk)

                _raise_if_beyond(uncompressed_size, maximum=max_uncompressed_size, exception_class=UncompressedSizeOverflowError)

                crc_32 = zlib.crc32(chunk, crc_32)
                compressed_chunk = compress_obj.compress(chunk)
                compressed_size += len(compressed_chunk)

                _raise_if_beyond(compressed_size, maximum=max_compressed_size, exception_class=CompressedSizeOverflowError)

                yield compressed_chunk

            compressed_chunk = compress_obj.flush()
            compressed_size += len(compressed_chunk)

            _raise_if_beyond(compressed_size, maximum=max_compressed_size, exception_class=CompressedSizeOverflowError)

            yield compressed_chunk

            return uncompressed_size, compressed_size, crc_32

        def _no_compression_64_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

            chunks, uncompressed_size, crc_32 = _no_compression_buffered_data_size_crc_32(chunks, maximum_size=0xffffffffffffffff)

            compressed_size = uncompressed_size + aes_size_increase
            extra = zip_64_local_extra_struct.pack(
                zip_64_extra_signature,
                16,    # Size of extra
                uncompressed_size,
                compressed_size,
            ) + mod_at_unix_extra + aes_extra
            flags = aes_flags | utf8_flag
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            yield from encryption_func((chunk for chunk in chunks))

            extra = zip_64_central_directory_extra_struct.pack(
                zip_64_extra_signature,
                24,    # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            ) + mod_at_unix_extra + aes_extra
            return central_directory_header_struct.pack(
               45,           # Version made by
               3,            # System made by (UNIX)
               45,           # Version required
               0,            # Reserved
               flags,
               compression,
               mod_at_ms_dos,
               masked_crc_32,
               0xffffffff,   # Compressed size - since zip64
               0xffffffff,   # Uncompressed size - since zip64
               len(name_encoded),
               len(extra),
               0,            # File comment length
               0,            # Disk number
               0,            # Internal file attributes - is binary
               external_attr,
               0xffffffff,   # File offset - since zip64
            ), name_encoded, extra


        def _no_compression_32_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffff, exception_class=OffsetOverflowError)

            chunks, uncompressed_size, crc_32 = _no_compression_buffered_data_size_crc_32(chunks, maximum_size=0xffffffff)

            compressed_size = uncompressed_size + aes_size_increase
            extra = mod_at_unix_extra + aes_extra
            flags = aes_flags | utf8_flag
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,           # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            yield from encryption_func((chunk for chunk in chunks))

            return central_directory_header_struct.pack(
               20,           # Version made by
               3,            # System made by (UNIX)
               20,           # Version required
               0,            # Reserved
               flags,
               compression,
               mod_at_ms_dos,
               masked_crc_32,
               compressed_size,
               uncompressed_size,
               len(name_encoded),
               len(extra),
               0,            # File comment length
               0,            # Disk number
               0,            # Internal file attributes - is binary
               external_attr,
               file_offset,
            ), name_encoded, extra

        def _no_compression_buffered_data_size_crc_32(chunks: Iterable[bytes], maximum_size: int) -> Tuple[Iterable[bytes], int, int]:
            # We cannot have a data descriptor, and so have to be able to determine the total
            # length and CRC32 before output ofchunks to client code

            size = 0
            crc_32 = zlib.crc32(b'')

            def _chunks() -> Generator[bytes, None, Any]:
                nonlocal size, crc_32
                for chunk in chunks:
                    size += len(chunk)
                    _raise_if_beyond(size, maximum=maximum_size, exception_class=UncompressedSizeOverflowError)
                    crc_32 = zlib.crc32(chunk, crc_32)
                    yield chunk

            __chunks = tuple(_chunks())

            return __chunks, size, crc_32

        def _no_compression_streamed_64_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

            compressed_size = uncompressed_size + aes_size_increase
            extra = zip_64_local_extra_struct.pack(
                zip_64_extra_signature,
                16,                 # Size of extra
                uncompressed_size,
                compressed_size,
            ) + mod_at_unix_extra + aes_extra
            flags = aes_flags | utf8_flag
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            yield from encryption_func(_no_compression_streamed_data(chunks, uncompressed_size, crc_32, 0xffffffffffffffff))

            extra = zip_64_central_directory_extra_struct.pack(
                zip_64_extra_signature,
                24,                 # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            ) + mod_at_unix_extra + aes_extra
            return central_directory_header_struct.pack(
               45,           # Version made by
               3,            # System made by (UNIX)
               45,           # Version required
               0,            # Reserved
               flags,
               compression,
               mod_at_ms_dos,
               masked_crc_32,
               0xffffffff,   # Compressed size - since zip64
               0xffffffff,   # Uncompressed size - since zip64
               len(name_encoded),
               len(extra),
               0,            # File comment length
               0,            # Disk number
               0,            # Internal file attributes - is binary
               external_attr,
               0xffffffff,   # File offset - since zip64
            ), name_encoded, extra


        def _no_compression_streamed_32_local_header_and_data(
                compression: int, aes_size_increase: int, aes_flags: int, name_encoded: bytes, mod_at_ms_dos: bytes,
                mod_at_unix_extra: bytes, aes_extra: bytes, external_attr: int, uncompressed_size: int, crc_32: int,
                crc_32_mask: int, _get_compress_obj: _CompressObjGetter, encryption_func: Callable[[Generator[bytes, None, Any]], Generator[bytes, None, Any]],
                chunks: Iterable[bytes],
        ) -> Generator[bytes, None, Any]:
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffff, exception_class=OffsetOverflowError)

            compressed_size = uncompressed_size + aes_size_increase
            extra = mod_at_unix_extra + aes_extra
            flags = aes_flags | utf8_flag
            masked_crc_32 = crc_32 & crc_32_mask

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,                 # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            yield from encryption_func(_no_compression_streamed_data(chunks, uncompressed_size, crc_32, 0xffffffff))

            return central_directory_header_struct.pack(
               20,                 # Version made by
               3,                  # System made by (UNIX)
               20,                 # Version required
               0,                  # Reserved
               flags,
               compression,
               mod_at_ms_dos,
               masked_crc_32,
               compressed_size,
               uncompressed_size,
               len(name_encoded),
               len(extra),
               0,                  # File comment length
               0,                  # Disk number
               0,                  # Internal file attributes - is binary
               external_attr,
               file_offset,
            ), name_encoded, extra

        def _no_compression_streamed_data(chunks: Iterable[bytes], uncompressed_size: int, crc_32: int, maximum_size: int) -> Generator[bytes, None, Any]:
            actual_crc_32 = zlib.crc32(b'')
            size = 0
            for chunk in chunks:
                actual_crc_32 = zlib.crc32(chunk, actual_crc_32)
                size += len(chunk)
                _raise_if_beyond(size, maximum=maximum_size, exception_class=UncompressedSizeOverflowError)
                yield chunk

            if actual_crc_32 != crc_32:
                raise CRC32IntegrityError()

            if size != uncompressed_size:
                raise UncompressedSizeIntegrityError()

        for name, modified_at, mode, method, chunks in files:
            _method, _auto_upgrade_central_directory, _get_compress_obj, uncompressed_size, crc_32 = method._get(offset, get_compressobj)

            name_encoded = name.encode('utf-8')
            _raise_if_beyond(len(name_encoded), maximum=0xffff, exception_class=NameLengthOverflowError)

            mod_at_ms_dos = modified_at_struct.pack(
                int(modified_at.second / 2) | \
                (modified_at.minute << 5) | \
                (modified_at.hour << 11),
                modified_at.day | \
                (modified_at.month << 5) | \
                (modified_at.year - 1980) << 9,
            )
            mod_at_unix_extra = mod_at_unix_extra_struct.pack(
                mod_at_unix_extra_signature,
                5,        # Size of extra
                b'\x01',  # Only modification time (as opposed to also other times)
                int(modified_at.timestamp()),
            ) if extended_timestamps else b''
            external_attr = \
                (mode << 16) | \
                (0x10 if name_encoded[-1:] == b'/' else 0x0)  # MS-DOS directory

            data_func, raw_compression = \
                (_zip_64_local_header_and_data, 8) if _method is _ZIP_64 else \
                (_zip_32_local_header_and_data, 8) if _method is _ZIP_32 else \
                (_no_compression_64_local_header_and_data, 0) if _method is _NO_COMPRESSION_BUFFERED_64 else \
                (_no_compression_32_local_header_and_data, 0) if _method is _NO_COMPRESSION_BUFFERED_32 else \
                (_no_compression_streamed_64_local_header_and_data, 0) if _method is _NO_COMPRESSION_STREAMED_64 else \
                (_no_compression_streamed_32_local_header_and_data, 0)

            compression, aes_size_increase, aes_flags, aes_extra, crc_32_mask, encryption_func = \
                (99, 28, aes_flag, aes_extra_struct.pack(aes_extra_signature, 7, 2, b'AE', 3, raw_compression), 0, _get_encrypt_aes(password)) if password is not None else \
                (raw_compression, 0, 0, b'', 0xffffffff, _encrypt_dummy)

            central_directory_header_entry, name_encoded, extra = yield from data_func(compression, aes_size_increase, aes_flags, name_encoded, mod_at_ms_dos, mod_at_unix_extra, aes_extra, external_attr, uncompressed_size, crc_32, crc_32_mask, _get_compress_obj, encryption_func, evenly_sized(chunks))
            central_directory_size += len(central_directory_header_signature) + len(central_directory_header_entry) + len(name_encoded) + len(extra)
            central_directory.append((central_directory_header_entry, name_encoded, extra))

            zip_64_central_directory = zip_64_central_directory \
                or (_auto_upgrade_central_directory is _AUTO_UPGRADE_CENTRAL_DIRECTORY and offset > 0xffffffff) \
                or (_auto_upgrade_central_directory is _AUTO_UPGRADE_CENTRAL_DIRECTORY and len(central_directory) > 0xffff) \
                or _method in (_ZIP_64, _NO_COMPRESSION_BUFFERED_64, _NO_COMPRESSION_STREAMED_64)

            max_central_directory_length, max_central_directory_start_offset, max_central_directory_size = \
                (0xffffffffffffffff, 0xffffffffffffffff, 0xffffffffffffffff) if zip_64_central_directory else \
                (0xffff, 0xffffffff, 0xffffffff)

            central_directory_start_offset = offset
            central_directory_end_offset = offset + central_directory_size

            _raise_if_beyond(central_directory_start_offset, maximum=max_central_directory_start_offset, exception_class=OffsetOverflowError)
            _raise_if_beyond(len(central_directory), maximum=max_central_directory_length, exception_class=CentralDirectoryNumberOfEntriesOverflowError)
            _raise_if_beyond(central_directory_size, maximum=max_central_directory_size, exception_class=CentralDirectorySizeOverflowError)
            _raise_if_beyond(central_directory_end_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

        for central_directory_header_entry, name_encoded, extra in central_directory:
            yield from _(central_directory_header_signature)
            yield from _(central_directory_header_entry)
            yield from _(name_encoded)
            yield from _(extra)

        if zip_64_central_directory:
            yield from _(zip_64_end_of_central_directory_signature)
            yield from _(zip_64_end_of_central_directory_struct.pack(
                44,  # Size of zip_64 end of central directory record
                45,  # Version made by
                45,  # Version required
                0,   # Disk number
                0,   # Disk number with central directory
                len(central_directory),  # On this disk
                len(central_directory),  # In total
                central_directory_size,
                central_directory_start_offset,
            ))

            yield from _(zip_64_end_of_central_directory_locator_signature)
            yield from _(zip_64_end_of_central_directory_locator_struct.pack(
                0,  # Disk number with zip_64 end of central directory record
                central_directory_end_offset,
                1   # Total number of disks
            ))

            yield from _(end_of_central_directory_signature)
            yield from _(end_of_central_directory_struct.pack(
                0xffff,      # Disk number - since zip64
                0xffff,      # Disk number with central directory - since zip64
                0xffff,      # Number of central directory entries on this disk - since zip64
                0xffff,      # Number of central directory entries in total - since zip64
                0xffffffff,  # Central directory size - since zip64
                0xffffffff,  # Central directory offset - since zip64
                0,           # ZIP_32 file comment length
            ))
        else:
            yield from _(end_of_central_directory_signature)
            yield from _(end_of_central_directory_struct.pack(
                0,  # Disk number
                0,  # Disk number with central directory
                len(central_directory),  # On this disk
                len(central_directory),  # In total
                central_directory_size,
                central_directory_start_offset,
                0, # ZIP_32 file comment length
            ))

    zipped_chunks = get_zipped_chunks_uneven()
    yield from evenly_sized(zipped_chunks)


async def async_stream_zip(
    files: AsyncIterable[AsyncMemberFile], chunk_size: int=65536,
    get_compressobj: _CompressObjGetter=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9),
    extended_timestamps: bool=True,
    password: Optional[str]=None,
    get_crypto_random: Callable[[int], bytes]=lambda num_bytes: secrets.token_bytes(num_bytes),
) -> AsyncIterable[bytes]:

    async def to_async_iterable(sync_iterable: Iterable[Any]) -> AsyncIterable[Any]:
        # asyncio.to_thread is not available until Python 3.9, and StopIteration doesn't get
        # propagated by run_in_executor, so we use a sentinel to detect the end of the iterable
        done = object()
        it = iter(sync_iterable)

        # contextvars are not available until Python 3.7
        try:
            import contextvars
        except ImportError:
            get_func_args: Callable[[], Tuple[Callable[..., Any], Tuple[Any, ...]]] = lambda: (next, (it, done))
        else:
            get_func_args = lambda: (contextvars.copy_context().run, (next, it, done))

        while True:
            func, args = get_func_args()
            value = await loop.run_in_executor(None, func, *args)
            if value is done:
                break
            yield value

    def to_sync_iterable(async_iterable: AsyncIterable[Any]) -> Iterable[Any]:
        # The built-in aiter and anext functions are not available until Python 3.10
        async_it = async_iterable.__aiter__()
        while True:
            try:
                value = asyncio.run_coroutine_threadsafe(async_it.__anext__(), loop).result()
            except StopAsyncIteration:
                break
            yield value

    loop = asyncio.get_event_loop()
    sync_member_files = (
        member_file[0:4] + (to_sync_iterable(member_file[4],),)
        for member_file in to_sync_iterable(files)
    )

    async for chunk in to_async_iterable(stream_zip(
            files=sync_member_files, chunk_size=chunk_size,
            get_compressobj=get_compressobj,
            extended_timestamps=extended_timestamps,
            password=password,
            get_crypto_random=get_crypto_random,
    )):
        yield chunk


class ZipError(Exception):
    pass


class ZipValueError(ZipError, ValueError):
    pass


class ZipIntegrityError(ZipValueError):
    pass


class CRC32IntegrityError(ZipIntegrityError):
    pass


class UncompressedSizeIntegrityError(ZipIntegrityError):
    pass


class ZipOverflowError(ZipValueError, OverflowError):
    pass


class UncompressedSizeOverflowError(ZipOverflowError):
    pass


class CompressedSizeOverflowError(ZipOverflowError):
    pass


class CentralDirectorySizeOverflowError(ZipOverflowError):
    pass


class OffsetOverflowError(ZipOverflowError):
    pass


class CentralDirectoryNumberOfEntriesOverflowError(ZipOverflowError):
    pass


class NameLengthOverflowError(ZipOverflowError):
    pass
