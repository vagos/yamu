# yamu

A game library manager.

I needed a simple way to manage my game collection across multiple platforms (Steam, GOG, itch.io, etc).
Existing tools covered different subsets of my needs, so I created `yamu` to fill in the gaps and provide an interface that allows for extremely fast categorization and searching of my game library.
This tool is built to be highly extensible via plugins, so you can add support for new platforms or features as needed.

## Installation

Run `pipx install yamu` to install via pipx.

## Quick start

Run `yamu --help` to see commands.

```
yamu add --title "Doom" --platform pc --genre shooter # Add a new game
yamu add # Add a new game interactively
yamu list platform:pc # List games that match a query
yamu update 1 --genre "fps"
yamu remove 1
yamu import # Import games from configured platforms
yamu list platform:steam
yamu completion # Mark games as completed
yamu fetchart platform:steam # Fetch cover art for Steam games
yamu web # Open the web interface to view your library
```

For `yamu import`, configure plugins in `~/.config/yamu/config.yaml`:

```yaml
library: "~/.local/share/yamu/library.db"
plugins:
  - steam

steam:
  api_key: "your_key"
  steam_ids:
    - "steam64_id"
```

## Acknowledgements

- [The beets project for inspiring the design of this tool.](https://beets.io/)
- [Yamu icon created by Ehtisham Abid](https://www.flaticon.com/free-icons/yamu)
