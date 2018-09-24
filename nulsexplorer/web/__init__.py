from aiohttp import web
import aiohttp_cors
import aiohttp_jinja2
import jinja2

from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

#from bottle import Jinja2Template, url

import pkg_resources

import time
import json
from bson import json_util
import pprint

import configparser
from datetime import date, datetime, timedelta

from nulsexplorer import TRANSACTION_TYPES


#bottle.install(bottle.JSONPlugin(json_dumps=json_util.dumps))

app = web.Application()
auth = None

# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
            allow_methods=["GET"],
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
})

tpl_path = pkg_resources.resource_filename('nulsexplorer.web', 'templates')
JINJA_LOADER = jinja2.ChoiceLoader([jinja2.FileSystemLoader(tpl_path),])
aiohttp_jinja2.setup(app,
    loader=JINJA_LOADER)
env = aiohttp_jinja2.get_env(app)
env.globals.update({
    'app': app,
    'date': date,
    'datetime': datetime,
    'time': time,
    'timedelta': timedelta,
    'int': int,
    'float': float,
    'len': len,
    'TRANSACTION_TYPES': TRANSACTION_TYPES,
    'pprint': pprint
})

#bottle.TEMPLATE_PATH.insert(0,tpl_path)
"""
Jinja2Template.defaults = {
    'url': url,
    'site_name': 'My blog',
    'app': app,
    'enumerate': enumerate
}"""


def init_cors():
    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)
