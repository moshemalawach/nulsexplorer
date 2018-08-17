import aiohttp_jinja2
from aiohttp import web
from bson import json_util
from math import ceil
import json
PER_PAGE = 20
PER_PAGE_SUMMARY = 50

class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def cond_output(request, context, template):
    if request.rel_url.path.endswith('.json'):
        if 'pagination' in context:
            context.pop('pagination')
        response = web.json_response(context, dumps=lambda v: json.dumps(v, default=json_util.default))
    else:
        response = aiohttp_jinja2.render_template(template,
                                                  request,
                                                  context)
    
    response.enable_compression()
    
    return response
