# yamu

> A game library manager for geeks.

Yamu provides a simple way to manage game collections across multiple platforms (Steam, GOG, itch.io, etc).
The tool is is extensible to support new platforms and features via plugins, and is composable with other UNIX tools and cli utilities.

## Installation

Run `pipx install yamu` to install via pipx.

## Quick start

Run `yamu --help` to see commands.

```
yamu import                           # Import games from configured platforms
yamu list platform:steam genre:action # List all Steam games in the action genre
yamu completion                       # Mark games as completed, interaactively
yamu fetchart                         # Fetch cover art games
yamu web                              # Open the web interface to view your library
```

For `yamu import`, configure plugins in `~/.config/yamu/config.yaml`:

```yaml
library: "~/.local/share/yamu/library.db"
plugins:
  - web 
  - steam
  - fetchart
  - igdb

steam:
  api_key: "your_key"
  steam_ids:
    - "steam64_id"

igdb:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
```

## Development

Create a virtual environment, install dev dependencies, and run tests:

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

## Acknowledgements

- [The beets project for inspiring yamu's design.](https://beets.io/)
- [Icon by Ehtisham Abid](https://www.flaticon.com/free-icon/yam_5687397)
