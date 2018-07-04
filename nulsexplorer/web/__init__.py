from aiohttp import web
import aiohttp_jinja2
import jinja2

from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

#from bottle import Jinja2Template, url

import pkg_resources

import json
from bson import json_util

import configparser
from datetime import date, datetime, timedelta


#bottle.install(bottle.JSONPlugin(json_dumps=json_util.dumps))

app = web.Application()
auth = None

tpl_path = pkg_resources.resource_filename('nulsexplorer.web', 'templates')
aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader(tpl_path))
env = aiohttp_jinja2.get_env(app)
env.globals.update({
    'app': app,
    'date': date,
    'datetime': datetime,
    'timedelta': timedelta,
    'int': int,
    'float': float
})

#bottle.TEMPLATE_PATH.insert(0,tpl_path)
"""
Jinja2Template.defaults = {
    'url': url,
    'site_name': 'My blog',
    'app': app,
    'enumerate': enumerate
}"""


import nulsexplorer.web.controllers
