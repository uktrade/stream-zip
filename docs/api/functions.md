---
layout: sub-navigation
sectionKey: API reference
eleventyNavigation:
    parent: API reference
order: 1
caption: API reference
title: Functions
---


## stream_zip.stream_zip

### Signature

```python
MemberFile = Tuple[str, datetime, int, Method, Iterable[bytes]]

def stream_zip(
    files: Iterable[MemberFile],
    chunk_size: int=65536,
    get_compressobj: Callable[[], 'zlib._Compress'] lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9),
    extended_timestamps: bool=True,
    password: Optional[str]=None,
    get_crypto_random: Callable[[int], bytes]=lambda num_bytes: secrets.token_bytes(num_bytes),
) -> Iterable[bytes]:
```

<hr class="govuk-section-break govuk-section-break--l">

### Parameters

| Name                | Type                           | Description
| --------------------| -------------------------------| ------------------------------------------
| files               | Iterable[MemberFile]           | The member files of the ZIP
| chunk_size          | int                            | Maximum `bytes` instance length yielded to client code
| get_compressobj     | Callable[[], 'zlib._Compress'] | A function returning a [Python zlib compression object](https://docs.python.org/3/library/zlib.html#zlib.compressobj) |
| password            | Optional[str]                  | The password used to encrypt all the member files with AES-256 encryption adhering to the Winzip AE-2 specification - see [Password protection](/get-started/password-protection/)
| extended_timestamps | bool                           | Whether to save extended timestamps in the ZIP file
| get_crypto_random   | Callable[[int], bytes]         | A function returning cryptographically safe random bytes - typically only useful from inside tests for deterministic encryption


### Returns

#### Type

Iterable[bytes]

#### Description

The raw bytes of the ZIP file that contains all the files defined by `files` parameter.

<hr class="govuk-section-break govuk-section-break--l govuk-section-break--visible">

### Raises

See [Exception hierarchy](/api/exception-hierarchy/) for the possible exceptions that can be raised. Exceptions raised from iterating the data in the `files` iterable are passed through to client code unchanged.

<hr class="govuk-section-break govuk-section-break--l">

## stream_zip.async_stream_zip

### Signature

```python
AsyncMemberFile = Tuple[str, datetime, int, Method, AsyncIterable[bytes]]

async def async_stream_zip(
    files: AsyncIterable[AsyncMemberFile],
    chunk_size: int=65536,
    get_compressobj: Callable[[], 'zlib._Compress']=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9),
    extended_timestamps: bool=True,
    password: Optional[str]=None,
    get_crypto_random: Callable[[int], bytes]=lambda num_bytes: secrets.token_bytes(num_bytes),
) -> AsyncIterable[bytes]:
```

<hr class="govuk-section-break govuk-section-break--l">

### Parameters

| Name                | Type                           | Description
| --------------------| -------------------------------| ------------------------------------------
| files               | AsyncIterable[AsyncMemberFile] | The member files of the ZIP
| chunk_size          | int                            | Maximum `bytes` instance length yielded to client code
| get_compressobj     | Callable[[], 'zlib._Compress'] | A function returning a [Python zlib compression object](https://docs.python.org/3/library/zlib.html#zlib.compressobj) |
| password            | Optional[str]                  | The password used to encrypt all the member files with AES-256 encryption adhering to the Winzip AE-2 specification - see [Password protection](/get-started/password-protection/)
| extended_timestamps | bool                           | Whether to save extended timestamps in the ZIP file
| get_crypto_random   | Callable[[int], bytes]         | A function returning cryptographically safe random bytes - typically only useful from inside tests for deterministic encryption


### Returns

#### Type

AsyncIterable[bytes]

#### Description
The raw bytes of the ZIP file that contains all the files defined by `files` parameter.

<hr class="govuk-section-break govuk-section-break--l govuk-section-break--visible">

### Raises

See [Exception hierarchy](/api/exception-hierarchy/) for the possible exceptions that can be raised. Exceptions raised from iterating the data in the `files` iterable are passed through to client code unchanged.
