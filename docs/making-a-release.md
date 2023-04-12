# How to make a release

These instructions are for members of the uktrade organisation who wish to release the latest code of stream-zip to the [stream-zip PyPI package](https://pypi.org/project/stream-zip/) and to the [stream-zip GitHub releases page](https://github.com/uktrade/stream-zip/releases).

These instructions are concise, and assume you have a good working knowledge of Python, the command line, and git.

1. Ensure you have the latest version of main branch locally.

2. Increase the version in [setup.py](https://github.com/uktrade/stream-zip/blob/main/setup.py). You should follow [Semantic Versioning 2.0](https://semver.org/) (SemVer) when deciding on the new version. Specifically, the version must be in X.Y.Z format, where X is the major version, Y is the minor version, and Z is the patch version.

    For major version 0, according to anything may change at any time. This is compatible with the SemVer specification.

3. Commit this change with `build(release): vX.Y.Z` as the commit message, where `X.Y.Z` is the new version in setup.py. For example to commit version `0.0.0`:

    ```bash
    git commit -m "build(release): v0.0.1"
    ```

4. Tag this commit with the tag `vX.Y.Z` where `X.Y.Z` is the new version in setup.py. For example:

    ```bash
    git tag v0.0.1
    ```

5. Push this commit with the tag.

     ```bash
     git push origin main --tags
     ```

6. Build the package locally, and push it to PyPI.

    ```bash
    rm -r -f build dist && python -m build && python -m twine upload dist/*
    ```

7. Create a new release from [https://github.com/uktrade/stream-zip/releases](https://github.com/uktrade/stream-zip/releases), choosing the tag created above, and giving the release the same name as the tag.

    The "Generate release notes" feature should be used, but the results amended as appropriate.

    The GitHub releases feature is primarily used to show the latest version in the top right of the documentation at [https://stream-zip.docs.trade.gov.uk/](https://stream-zip.docs.trade.gov.uk/).
