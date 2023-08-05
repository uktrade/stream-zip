## Custom zlib options

For the `ZIP_32` or `ZIP_64` methods, you can customise the compression object by overriding the default `get_compressobj` parameter, which is shown below.

```python
for zipped_chunk in stream_zip(unzipped_files(), get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)):
    print(zipped_chunk)
```

If you wish to disable compression entirely for these methods, you can pass `level=0` in the above. There is no way to customize the zlib object for the `ZIP_AUTO` method, other than passing `level` into it. See [Methods](methods.md) for details and other ways to not compress member files.


## Custom chunk size

The default `bytes` instance size is 65536 bytes. To customise this, you can override the `chunk_size` parameter.

```python
for zipped_chunk in stream_zip(unzipped_files(), chunk_size=65536):
    print(zipped_chunk)
```

This one size is used both for input - splitting or gathering any uncompressed data into `chunk_size` bytes before attempting to compress it, and in output - splitting or gathering any compressed data into `chunk_size` bytes before returning it to client code.

There may be performance differences with a different `chunk_size` values. The default chunk_size may not be optimal for your use case.


## Extended timestamps

By default so-called extended timestamps are included in the ZIP, which store the modification time of member files more accurately than the original ZIP format allows. To omit the extended timestamps, you can pass `extended_timestamps=False` to `stream_zip`.

```python
for zipped_chunk in stream_zip(unzipped_files(), extended_timestamps=False):
    print(zipped_chunk)
```

This is useful to keep the total number of bytes down as much as possible. This is also useful when creating Open Document files using `stream_zip`. Open Document files cannot have extended timestamps in their member files if they are to pass validation.
