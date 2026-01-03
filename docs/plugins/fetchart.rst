Fetchart
========

The ``fetchart`` plugin downloads game artwork (Steam header images) and stores
paths in the library.

Enable it in your config:

::

    plugins:
      - fetchart
    fetchart:
      dir: "~/.local/share/yamu/art"

Usage
-----

::

    yamu fetchart
    yamu fetchart --threads 4

Games must have a Steam app ID in their path (``steam://appid``) for art to be fetched.
This is provided by the :doc:`steam` plugin.
This limitation may be removed in future versions.
