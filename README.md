# futaba
![picture of futaba](images/futaba-portrait.png)

A Discord bot for the [Programming server](https://discord.gg/010z0Kw1A9ql5c1Qe).

Requires Python 3.6 or later. There is a sample configuration file at `misc/config.toml`.

## Running locally
Setup:
```
$ pip3 install --user -r requirements.txt
$ docker run -e POSTGRES_PASSWORD=password -p 5432:5432 postgres
$ cp misc/config.toml config.toml
# set database.url to "postgresql://postgres:password@localhost"
```

To run:
```
$ python3 -m futaba <config.toml>
```

## Development
More setup:
```
$ pip3 install --user -r requirements-dev.txt
```

Formatting and linting code:
```
$ black futaba
$ pylint futaba
```

## Deployment
You can have a production system, complete with a systemd service file, you can use the provided
`deploy.sh` script. If there is a `futaba.service` file in the repository root, that service is installed, otherwise the one in `misc/` is used.

Usage:
```
$ ./deploy.sh <config.toml>
```

Installs dependencies, installs the service and configuration files, then restarts the unit.
