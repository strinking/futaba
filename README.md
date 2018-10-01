# futaba
A Discord bot for the [Programming server](https://discord.gg/010z0Kw1A9ql5c1Qe).

![futaba looking at the camera](https://cdn.discordapp.com/avatars/130012001236811776/855aec7be21b28afda86e1a2d4f7cc7e.png)

Requires Python 3.5 or later. There is a sample configuration file at `misc/config.toml`.

## Running locally
Setup:
```
pip3 install --user -r requirements.txt
```

To run:
```
python3 -m futaba <config.toml>
```

## Deployment
You can set up a production system, complete with a systemd service file, you can use the provided
`deploy.sh` script. If there is a `futaba.service` file in the repository root, that service is installed, otherwise the one in `misc/` is used.

Usage:
```
./deploy.sh <config.toml>
```

Installs dependencies, installs the service and configuration files, then restarts the unit.
