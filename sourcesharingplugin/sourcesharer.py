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
from email.utils import formataddr, COMMASPACE, formatdate
from email.mime.multipart import MIMEMultipart
from trac.mimeview.api import Mimeview
import os
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText

try:
    # Prefer announcer interface
    from announcer.distributors.mail import EmailDistributor as Distributor
    from announcer.util.mail import set_header
    using_announcer = True
except ImportError:
    from trac.notification import NotificationSystem as Distributor
    from trac.notification import MAXHEADERLEN
    from email.header import Header
    using_announcer = False
    # copy set_header from announcer plugin
    def set_header(message, key, value, charset=None):
        if not charset:
            charset = message.get_charset() or 'ascii'
        value = Header(value, charset, MAXHEADERLEN-(len(key)+2))
        if message.has_key(key):
            message.replace_header(key, value)
        else:
            message[key] = value
        return message
try:
    from autocompleteplugin.api import IAutoCompleteUser
except:
    IAutoCompleteUser = None

__all__ = ['SharingSystem', 'Distributor','using_announcer']




class SharingSystem(Component):
    
    implements(ITemplateStreamFilter, ITemplateProvider, IRequestHandler,
               IPermissionRequestor, IAutoCompleteUser)
    
    distributor = Distributor
    
    def send_as_email(self, sender, recipients, subject, text, *files):
        """
        `sender` Tuple of (real name, email address)
        `recipients` List of (real name, email address) recipient address tuples
        `subject` The e-mail subject
        `text` The text body of the e-mail
        `files` List of paths to the files to send
        """
        assert len(files) > 0, 'No files to send!'
        mailsys = self.distributor(self.env)
        from_addr = formataddr(sender)
        root = MIMEMultipart('related')
        root.set_charset('utf-8')
        headers = {}
        headers['Subject'] = subject
        headers['To'] = ', '.join(['%s <%s>' % (x[0], x[1]) for x in recipients])
        headers['From'] = from_addr
        headers['Date'] = formatdate()
        mimeview = Mimeview(self.env)
        root.attach(MIMEText(text, _charset='utf-8'))
        for f in files:
            if not os.path.isfile(f):
                self.log.debug('Not a file: %s', f)
                continue
            content = open(f, 'rb').read()
            mtype = mimeview.get_mimetype(f, content)
            if not mtype:
                mtype = 'application/octet-stream'
            if '; charset=' in mtype:
                mtype, encoding = mtype.split('; charset=', 1)
            maintype, subtype = mtype.split('/', 1)
            part = MIMEBase(maintype, subtype)
            part.set_payload(content)
            part.add_header('content-disposition', 'attachment',
                            filename=os.path.basename(f))
            encoders.encode_base64(part)
            root.attach(part)
        for k, v in headers.items():
            set_header(root, k, v, 'utf-8')
        del root['Content-Transfer-Encoding']
        email = (from_addr, recipients, root.as_string())
        if using_announcer:
            if mailsys.use_threaded_delivery:
                mailsys.get_delivery_queue().put(email)
            else:
                mailsys.send(*email)
        else:
            mailsys.send_email(*email)
        return email # for testing/debugging purposes

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
