'''
Created on 17 Jun 2010

@author: enmarkp
'''
from trac.core import Component, ExtensionPoint, implements
from api import ISharable
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_javascript,\
    add_warning, Chrome
from pkg_resources import resource_filename #@UnresolvedImport
from genshi.template.loader import TemplateLoader
from genshi.filters.transform import Transformer
from genshi.builder import tag
from genshi.core import Markup
import re
from trac.perm import IPermissionRequestor
try:
    from autocompleteplugin.api import IAutoCompleteUser
except:
    IAutoCompleteUser = None

__all__ = ['SharingSystem']

class SharingSystem(Component):
    
    implements(ITemplateStreamFilter, ITemplateProvider, IRequestHandler,
               IPermissionRequestor, IAutoCompleteUser)
    
    # ITemplateStreamFilter methods
    
    def filter_stream(self, req, method, filename, stream, data):
        if req.method == 'GET' and filename == 'browser.html':
            add_stylesheet(req, 'sourcesharer/filebox.css')
            add_javascript(req, 'sourcesharer/filebox.js')
            tmpl = TemplateLoader(self.get_templates_dirs()).load('filebox.html')
            filebox = tmpl.generate(href=req.href, files=[])
            # Wrap and float dirlist table, add filebox div 
            stream |= Transformer('//table[@id="dirlist"]').wrap(tag.div(id="outer",style="clear:both")).wrap(tag.div(id="left", style="float:left; width:79%"))
            stream |= Transformer('//div[@id="outer"]').append(tag.div(filebox, id="right", style="float:left; width:20%;margin-left:5px"))
        return stream
    
    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        return [('sourcesharer', resource_filename(__name__, 'htdocs'))]
    
    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]
    
    # IRequestHandler methods
    
    def process_request(self, req):
        if req.method == 'POST':
            files = req.args.get('filebox-files')
            if not files:
                add_warning('No files selected')
                req.redirect(req.href.browser())
            if not "send" in req.args:
                Chrome(self.env).add_wiki_toolbars(req)
                add_javascript(req, 'sourcesharer/share.js')
                return 'share.html', dict(req=req, files=files), None
        req.redirect(req.href.browser())
    
    def match_request(self, req):
        if req.path_info == '/share':
            return True
    
    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['BROWSER_VIEW', 'FILE_VIEW']

    #IAutoCompleteUser
    
    def get_templates(self):
        return {'share.html': ['#user']}
