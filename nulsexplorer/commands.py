import argparse
import configparser
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from nulsexplorer.web import app
from nulsexplorer import model
from nulsexplorer.jobs import start_jobs
from nulsexplorer.config import get_defaults
from nulsexplorer.main import start_connector
import logging
import asyncio
import base64

from configmanager import Config

LOGGER = logging.getLogger('explorer')

def launch_explorer():
    global app
    parser = argparse.ArgumentParser(prog="nulsexplorer",
                                     description="Launches a Nuls Explorer")
    parser.add_argument('-c', '--config', action="store", dest="config_file")
    parser.add_argument('-p', '--port', action="store", type=int, dest="port", default=8080)
    parser.add_argument('--host', action="store", type=str, dest="host", default="127.0.0.1")
    parser.add_argument('--debug', action="store_true", dest="debug", default=False)
    args = parser.parse_args()
    config = Config(schema=get_defaults())

    app['config'] = config
    app.config = config

    if args.config_file is not None:
        app['config'].yaml.load(args.config_file)

    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    LOGGER.info("Starting up.")

    app['config'].explorer.port.value = args.port
    app['config'].explorer.host.value = args.host

    model.init_db(ensure_indexes=(not args.debug))
    LOGGER.info("Database initialized.")


    # session_opts = {
    #     'session.cookie_expires': True,
    #     'session.encrypt_key': app['config']['fleeter'].get('secret', "CHOOSE A SECRET DAMNIT"),
    #     'session.httponly': True,
    #     'session.timeout': 3600 * 24,  # 1 day
    #     'session.type': 'cookie',
    #     'session.validate_key': True,
    # }
    host=app['config'].explorer.host.value
    port=app['config'].explorer.port.value
    session_secret = app['config'].explorer.secret.get("CHOOSE A SECRET DAMNIT")
    session_secret = '{0:<32.32}'.format(session_secret)
    session_setup(app, EncryptedCookieStorage(session_secret.encode('utf-8')))
    #app.middlewares.append(auth_middleware_factory)
    #app = SessionMiddleware(app, session_opts)

    #prepare_server()
    start_connector()
    start_jobs()

    #if args.debug:
    #    debug(True)

    LOGGER.info("Starting main loop.")

    loop = asyncio.get_event_loop()
    handler = app.make_handler()
    f = loop.create_server(handler, host, port)
    srv = loop.run_until_complete(f)
    LOGGER.info('serving on %s', srv.sockets[0].getsockname())
    loop.run_forever()
    #run(app=app, quiet=False, server = 'aiobottle:AsyncServer',
    #    host=host, port=port)


if __name__ == "__main__":
    launch_explorer()
