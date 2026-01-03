Completion
==========

The ``completion`` plugin helps track play status for your games.

Enable it in your config:

::

    plugins:
      - completion

Usage
-----

::

    yamu completion

For each game without a completion status, yamu prompts you to mark it as
``played``, ``beaten``, ``abandoned``, or ``completionist``.
Completion status is also inferred from achievements if they are available via one of the ``import`` plugins (e.g., :doc:`steam`).
