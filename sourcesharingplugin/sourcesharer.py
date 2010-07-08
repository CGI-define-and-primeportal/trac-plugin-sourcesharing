'''
Created on 17 Jun 2010

@author: enmarkp
'''
from trac.core import Component, implements, TracError
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_javascript
from trac.mimeview.api import Mimeview, Context
from trac.perm import IPermissionRequestor
from trac.web.session import DetachedSession
from trac.resource import Resource
from trac.versioncontrol.api import RepositoryManager
from trac.util.translation import _
from trac.util.presentation import to_json
from trac.util.text import to_unicode
from pkg_resources import resource_filename
from genshi.template.loader import TemplateLoader
from genshi.filters.transform import Transformer
from genshi.builder import tag
try:
    from email.utils import formataddr, formatdate
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.encoders import encode_base64
    from email.charset import Charset, QP, BASE64, SHORTEST
except ImportError:
    # Python 2.4
    from email.Utils import formataddr, formatdate
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email.Encoders import encode_base64
    from email.MIMEText import MIMEText
    from email.Charset import Charset, QP, BASE64, SHORTEST
import os

try:
    # Prefer announcer interface
    from announcer.distributors.mail import EmailDistributor as Distributor
    from announcer.util.mail import set_header
    using_announcer = True
except ImportError:
    from trac.notification import NotificationSystem as Distributor
    from trac.notification import MAXHEADERLEN
    from email.Header import Header
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
    
    def send_as_email(self, sender, recipients, subject, text, *resources):
        """
        `sender` Tuple of (real name, email address)
        `recipients` List of (real name, email address) recipient address tuples
        `subject` The e-mail subject
        `text` The text body of the e-mail
        `files` List of paths to the files to send
        """
        assert len(resources) > 0, 'Nothing to send!'
        mailsys = self.distributor(self.env)
        from_addr = formataddr(sender)
        root = MIMEMultipart('related')
        root.set_charset('utf-8')
        headers = {}
        recp = [formataddr(r) for r in recipients]
        headers['Subject'] = subject
        headers['To'] = ', '.join(recp)
        headers['From'] = from_addr
        headers['Date'] = formatdate()
        msg = MIMEText(to_unicode(text).encode('utf-8'), 'plain', 'utf-8')
        root.attach(msg)
        mimeview = Mimeview(self.env)
        for r in resources:
            if hasattr(r, 'realm'):
                if r.realm == 'source':
                    repo = RepositoryManager(self.env).get_repository(r.parent.id)
                    n = repo.get_node(r.id, rev=r.version)
                    content = n.get_content().read()
                    f = os.path.join(repo.repos.path, n.path)
                    mtype = n.get_content_type() or mimeview.get_mimetype(f, content)
            else:
                if isinstance(r, basestring):
                    if not os.path.isfile(r):
                        self.log.warn('Not a valid path: %s', r)
                        continue
                    f = r
                    content = open(f, 'rb').read()
                elif isinstance(r, file):
                    f = r.name
                    content = r.read()
                mtype = mimeview.get_mimetype(f, content)
            if not mtype:
                mtype = 'application/octet-stream'
            if '; charset=' in mtype:
                # What to use encoding for?
                mtype, encoding = mtype.split('; charset=', 1)
            maintype, subtype = mtype.split('/', 1)
            part = MIMEBase(maintype, subtype)
            part.set_payload(content)
            part.add_header('content-disposition', 'attachment',
                            filename=os.path.basename(f))
            encode_base64(part)
            root.attach(part)
        del root['Content-Transfer-Encoding']
        for k, v in headers.items():
            set_header(root, k, v, 'utf-8')
        email = (from_addr, recp, root.as_string())
        self.log.debug('Sending mail from %s to %s', from_addr, recp)
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
            add_javascript(req, 'sourcesharer/share.js')
            # Render the filebox template for stream insertion
            tmpl = TemplateLoader(self.get_templates_dirs()).load('filebox.html')
            filebox = tmpl.generate(href=req.href, reponame=data['reponame'] or '', files=[])
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
            files =   req.args.get('filebox-files')
            if not isinstance(files, list):
                files = [files]
            users =   req.args.get('user')
            if not isinstance(users, list):
                users = [users]
            subject = req.args.get('subject')
            message = req.args.get('message')
            reponame = req.args.get('repository')
            repo = RepositoryManager(self.env).get_repository(reponame)
            recipients = []
            to_send = []
            failures = []
            for u in users:
                try:
                    # TODO: handle manually typed addresses ((.*?)? <?xx@yyy.zz>?)
                    address = self._get_address_info(u)
                except Exception, e:
                    failures.append(e.message)
                    continue
                recipients.append(address)
            for f in files:
                # TODO: add ?rev=xxx and select correct version
                try:
                    file_res = self._get_file_resource(req, realm='source',
                                                       parent=repo.resource,
                                                       path=f)
                except Exception, e:
                    failures.append(e.message)
                    continue
                to_send.append(file_res)
            sender = self._get_address_info(req.authname)
            self.send_as_email(sender, recipients, subject, message, *to_send)
            if failures != []:
                req.send(to_json(failures), 'text/json', 400)
            req.send('')
        req.redirect(req.href.browser())
    
    def match_request(self, req):
        if req.path_info == '/share':
            return True
    
    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['BROWSER_VIEW', 'FILE_VIEW']

    #IAutoCompleteUser
    
    def get_templates(self):
        return {'browser.html': ['#user-select']}

    # Other
    
    def _get_address_info(self, authname):
        "TODO: check env.get_known_users"
        sess = DetachedSession(self.env, authname)
        real_name = sess.get('name') or sess.sid
        address = sess.get('email')
        if not address:
            raise ValueError(_('User %s(user) has no email address set', 
                              user=sess.sid))
        return real_name, address

    def _get_file_resource(self, req, realm, parent, path):
        """Should raise if path doesn't exist or user has insufficient perms
        TODO: handle attachments and other sendable resources
        """
        file_res = Resource(realm, path, parent=parent)
        ctx = Context.from_request(req, file_res)
        ctx.perm.require('FILE_VIEW')
        return file_res
