# Input examples

This page contains examples to show how files from different sources can be compressed into a ZIP using stream-zip. It is likely they will have to be modified for your use case.

> At the moment only one example is available


## Named local files

```python
from datetime import datetime
from stat import S_IFREG
from stream_zip import ZIP_32, stream_zip

def local_files(names):
    now  = datetime.now()

    def contents(name):
        with open(name, 'rb') as f:
            while chunk := f.read(65536):
                yield chunk

    return (
        (name, now, S_IFREG | 0o600, ZIP_32, contents(name))
        for name in names
    )

names = ('file-1.txt', 'file-2.txt')
zipped_chunks = stream_zip(local_files(names))
```


## Submit your own

Pull requests (PRs) that propose changes to this page are especially welcome. PRs can be made at the [source of this page](https://github.com/uktrade/stream-zip/blob/main/docs/recipes.md). Submitting a PR requires a [GitHub account](https://github.com/join) and knowledge of the [GitHub fork and PR process](https://docs.github.com/en/pull-requests).
