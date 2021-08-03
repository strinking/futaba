# Create base OS image
FROM python:3.9 AS base

# Create Volumes
VOLUME /logs
VOLUME /config

# Install python requirements
FROM base AS requirements

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

# Install and run futaba
FROM requirements AS futaba

COPY ./futaba ./futaba/

ENTRYPOINT ["python3", "-m", "futaba"]

CMD ["config.toml"]