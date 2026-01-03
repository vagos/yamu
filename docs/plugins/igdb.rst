IGDB
====

The ``igdb`` plugin adds metadata search results during import. It uses the
IGDB API (via Twitch credentials) to supply release dates, genres, developers,
publishers, and platforms.

Enable it in your config:

::

    plugins:
      - igdb
    igdb:
      client_id: "YOUR_TWITCH_CLIENT_ID"
      client_secret: "YOUR_TWITCH_CLIENT_SECRET"
      search_limit: 5

Importing
---------------

When ``igdb`` is enabled, ``yamu import`` will show IGDB candidates under each
game during the interactive prompt. You can choose an IGDB candidate, then
apply or edit the resulting metadata before importing.
