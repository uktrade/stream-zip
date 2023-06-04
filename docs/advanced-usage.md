## Custom zlib options

For the `ZIP_32` or `ZIP_64` modes, you can customise the compression object by overriding the default `get_compressobj` parameter, which is shown below.

```python
for zipped_chunk in stream_zip(unzipped_files(), get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)):
    print(zipped_chunk)
```

If you wish to disable compression entirely for these modes, you can pass `level=0` in the above. There is no way to customize the zlib object for `ZIP_AUTO` mode, other than passing `level` into it. See [Modes](modes.md) for details and other ways to not compress member files.


## Custom chunk size

The default `bytes` instance size is 65536 bytes. To customise this, you can override the `chunk_size` parameter.

```python
for zipped_chunk in stream_zip(unzipped_files(), chunk_size=65536):
    print(zipped_chunk)
```

This one size is used both for input - splitting or gathering any uncompressed data into `chunk_size` bytes before attempting to compress it, and in output - splitting or gathering any compressed data into `chunk_size` bytes before returning it to client code.

There may be performance differences with a different `chunk_size` values. The default chunk_size may not be optimal for your use case.
