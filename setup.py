import setuptools


def long_description():
    with open('README.md', 'r') as file:
        return file.read()


setuptools.setup(
    name='stream-zip',
    version='0.0.41',
    author='Department for International Trade',
    author_email='sre@digital.trade.gov.uk',
    description='Python function to construct a ZIP archive with stream processing - without having to store the entire ZIP in memory or disk',
    long_description=long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/uktrade/stream-zip',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Archiving :: Compression',
    ],
    python_requires='>=3.7.4',
    py_modules=[
        'stream_zip',
    ],
)
