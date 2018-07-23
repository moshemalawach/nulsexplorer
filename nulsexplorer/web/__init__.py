from aiohttp import web
import aiohttp_jinja2
import jinja2

from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

#from bottle import Jinja2Template, url

import pkg_resources

import time
import json
from bson import json_util

import configparser
from datetime import date, datetime, timedelta

from nulsexplorer import TRANSACTION_TYPES


#bottle.install(bottle.JSONPlugin(json_dumps=json_util.dumps))

app = web.Application()
auth = None

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
    'TRANSACTION_TYPES': TRANSACTION_TYPES
})

#bottle.TEMPLATE_PATH.insert(0,tpl_path)
"""
Jinja2Template.defaults = {
    'url': url,
    'site_name': 'My blog',
    'app': app,
    'enumerate': enumerate
}"""
