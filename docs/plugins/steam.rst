Steam
=====

The ``steam`` plugin imports your Steam library and optional metadata like
release dates and genres.
When ``fetch_achievements`` is enabled, achievements are fetched during import and stored alongside the game.

Enable it in your config:

::

    plugins:
      - steam
    steam:
      fetch_achievements: true
      api_key: "YOUR_STEAM_KEY"
      steam_ids:
        - 76561198074847543

To get your Steam API key, visit https://steamcommunity.com/dev/apikey.
To find your Steam ID, you can use a service like https://steamid.io/.

Importing
---------

Run ``yamu import`` to fetch owned games from the configured Steam IDs.
Existing games are skipped by default.

By default, the plugin fetches app details (genres, release date, developer, publisher).
This uses Steam's search API, which can be subject to rate limiting.
You can control rate limits and caching:

::

    steam:
      fetch_details: true
      delay: 0.2
      retries: 3
      backoff: 1.0
      cache_ttl: 604800
      cache_path: "~/.cache/yamu/steam_cache.json"
