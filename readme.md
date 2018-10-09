# NULS Explorer

This is an alternative Explorer for the NULS blockchain written in Python with
AsyncIO and MongoDB bindings (using Motor).

## Installation

You need to install the requirements, ideally in an empty virtualenv (I let
that part to you):

`$ python setup.py develop`

You need a mongodb instance, either on localhost or elsewhere. A simple way to
spawn up one is using docker:

`$ docker run --name mongo -p 127.0.0.1:27017:27017 -d mongo`

(using your distribution tools is perfectly fine too, like `apt install mongodb mongodb-server`)

Then, once it's installed, you need to copy the sample-config.yaml file elsewhere,
and edit it to your liking (see configuration section).

To run NULSExplorer, run this command:

`$ nulsexplorer -c config.yaml` (where config.yaml is your configuration file you
edited earlier)

Then, open your browser on http://localhost:8080 (assuming you didn't change
the port), and you will have a basic explorer ready.

## Configuration

The configuration file is a yaml formatted file, with those sections:

### `explorer`

Defaults:

```yaml
explorer:
  host: 127.0.0.1
  port: 8080
  secret: "CHOOSE A SECRET DAMMIT"
```

You need to set a secret for the cookies. If you want to listen to the world,
change `127.0.0.1` to `0.0.0.0`.
You can also change the port the HTTP server is listening to.

### `nuls`

Defaults:

```yaml
nuls:
  host: 127.0.0.1
  port: 6001
  path: /api/
  base_uri: "http://127.0.0.1:6001/api/"
  chain_id: 8964
```

This part is about your connection to the nuls client to retrieve the blocks
and other informations about the nuls blockchain.
Most of the arguments there are self-explaining, except chain_id.

`chain_id` is the chain you are addressing, NULS mainnet is 8964 for the Ns prefix.
Other networks (like testnets or side chains) might have other chain_id.
This will define the address that will be generated from a public key.

### `mongodb`

```yaml
mongodb:
  uri: "mongodb://127.0.0.1"
  database: nulsmain
```

This section explains to the mongodb driver how to access the database.
The mongo db uri is in a standard format and supports usernames, password and
ports (as well as other options, but please check the PyMongo doc for more
information).

## API Endpoints

There is a lot of API endpoints. Most of them not yet documented, I wil be happy
to accept pull-request for that :-)

Basically, you can take any url you see navigating on the http interface
and add .json at the end to get a JSON API endpoint.
