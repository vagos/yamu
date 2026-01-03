Configuration
=============

yamu uses a YAML configuration file located at:

- ``~/.config/yamu/config.yaml`` on Unix-like systems.

The config file merges with the defaults shipped with yamu. A minimal example:

::

    library: ~/.local/share/yamu/library.db
    plugins:
      - steam
      - web
      - fetchart
      - completion
    steam:
      api_key: "YOUR_STEAM_KEY"
      steam_ids:
        - 76561198074847543

Top-level options
-----------------

library
~~~~~~~

Path to the SQLite database file. You can also provide ``library: {path: ...}``.

plugins
~~~~~~~

A list of plugin names to load. Available plugins are in Plugins_.

import
~~~~~~

Importer settings:

- ``threads``: number of background fetch threads. Default: ``2``.

ui
~~

User interface settings:

- ``columns``: default columns for ``yamu list``.
- ``color``: enable colored output.
- ``date_format``: format string for dates. Default: ``$year``.
- ``colors``: mapping of named style tokens.

web
~~~

Web UI settings:

- ``host``: bind address. Default: ``127.0.0.1``.
- ``port``: HTTP port. Default: ``8337``.

fetchart
~~~~~~~~

Artwork settings:

- ``dir``: directory to store downloaded art.

steam
~~~~~

Steam integration settings:

- ``api_key``: Steam Web API key.
- ``steam_ids``: list of Steam IDs used by ``yamu import``.
- ``fetch_details``: fetch per-game metadata. Default: ``true``.
- ``fetch_achievements``: fetch achievements during import. Default: ``true``.
- ``delay``: seconds between Steam requests.
- ``retries``: retry count for Steam requests.
- ``backoff``: backoff multiplier for retries.
- ``cache_ttl``: cache TTL, in seconds.
- ``cache_path``: override cache path base.

igdb
~~~~

IGDB metadata settings:

- ``client_id``: Twitch/IGDB client ID.
- ``client_secret``: Twitch/IGDB client secret.
- ``access_token``: optional access token override.
- ``search_limit``: number of search results to return. Default: ``5``.
- ``token_cache_path``: override cache path for tokens.
