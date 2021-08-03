# futaba

A Discord bot for the [Programming server](https://discord.gg/010z0Kw1A9ql5c1Qe).

Requires Python 3.9 or later. There is a sample configuration file at `misc/config.toml`.

## Building
```
$ docker build --tag futaba .
```

## Running locally
Setup:
```
$ docker create -v <log folder>:/logs -v <config folder>:/config --name futaba futaba <config file>
```

Running:
```
$ docker start futaba
```

## Development
More setup:
```
$ pip3 install -r requirements.txt
$ pip3 install -r requirements-dev.txt
```

Formatting and linting code:
```
$ black --line-length 120 futaba
$ flake8 --max-line-length=120 futaba
```
