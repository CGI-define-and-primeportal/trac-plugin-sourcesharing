# coding: utf-8
#
# Copyright (c) 2010, Logica
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

'''
Created on 17 Jun 2010

@author: enmarkp
'''
from tempfile import mkstemp
from autocompleteplugin.api import IAutoCompleteUser
from trac.config import Option
from trac.web.chrome import Chrome, add_ctxtnav
from trac.core import Component, implements, TracError
from trac.test import Mock, MockPerm
from trac.web.href import Href
from trac.mimeview import Context
from trac.wiki.formatter import HtmlFormatter
from genshi.template import MarkupTemplate
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_javascript,\
    add_warning, add_notice
from trac.mimeview.api import Mimeview
from trac.perm import IPermissionRequestor
from trac.web.session import DetachedSession
from trac.resource import Resource
from trac.versioncontrol.api import RepositoryManager
from trac.util.translation import _
from trac.util.presentation import to_json
from trac.util.text import to_unicode, exception_to_unicode
from pkg_resources import resource_filename
from genshi.template.loader import TemplateLoader
from genshi.filters.transform import Transformer
from genshi.builder import tag
from trac.notification import EMAIL_LOOKALIKE_PATTERN
from trac.versioncontrol.svn_fs import SvnCachedRepository, SubversionRepository
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
import os
import re

__all__ = ['SharingSystem', 'Distributor','using_announcer']


class SharingSystem(Component):

    implements(ITemplateStreamFilter, ITemplateProvider, IRequestHandler,
               IPermissionRequestor, IAutoCompleteUser)

    distributor = Distributor
    mime_encoding = Option('announcer', 'mime_encoding', 'base64',
        """Specifies the MIME encoding scheme for emails.

        Valid options are 'base64' for Base64 encoding, 'qp' for
        Quoted-Printable, and 'none' for no encoding. Note that the no encoding
        means that non-ASCII characters in text are going to cause problems
        with notifications.
        """)
    #settings for tranfer mode of email
    LINKS_ONLY = 1
    ATTACHMENTS_ONLY = 2
    LINKS_ATTACHMENTS = 3

    html_template_name = Option('sourcesharer',
                                'email_html_template_name',
                                'sourcesharer_email.html',
                                doc="""Filename of genshi template to use for HTML mails with file attachments.""")

    def send_as_email(self, req, sender, recipients, subject, text, mode,  *resources):
        """
        `authname` Trac username of sender
        `sender` Tuple of (real name, email address)
        `recipients` List of (real name, email address) recipient address tuples
        `subject` The e-mail subject
        `text` The text body of the e-mail
        `files` List of paths to the files to send
        """
        assert len(resources) > 0, 'Nothing to send!'
        mailsys = self.distributor(self.env)
        from_addr = sender[1]
        root = MIMEMultipart('related')
        root.set_charset(self._make_charset())
        root.preamble = 'This is a multi-part message in MIME format.'
        headers = {}
        recp = [r[1] for r in recipients]
        headers['Subject'] = subject
        headers['To'] = ', '.join(recp)
        headers['From'] = from_addr
        headers['Date'] = formatdate()
        authname = req.authname
        files = []
        links = []
        attachments = []
        mimeview = Mimeview(self.env)
        for r in resources:
            repo = RepositoryManager(self.env).get_repository(r.parent.id)
            n = repo.get_node(r.id, rev=r.version)
            files.append(n.path)
            f = os.path.join(repo.repos.path, n.path)
            if mode in (self.LINKS_ONLY, self.LINKS_ATTACHMENTS):
                links.append((req.abs_href.browser(repo.reponame or None, n.path, format='raw'), os.path.basename(f)))
            if mode in (self.ATTACHMENTS_ONLY, self.LINKS_ATTACHMENTS):
                content = n.get_content().read()                
                mtype = n.get_content_type() or mimeview.get_mimetype(f, content)
                if not mtype:
                    mtype = 'application/octet-stream'
                if '; charset=' in mtype:
                    # What to use encoding for?
                    mtype, encoding = mtype.split('; charset=', 1)
                attachments.append(os.path.basename(f))
                maintype, subtype = mtype.split('/', 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                part.add_header('content-disposition', 'attachment', filename=os.path.basename(f))
                encode_base64(part)
                root.attach(part)
        body = self._format_email(authname, sender, recipients, subject, text, mode, links, attachments)
        msg = MIMEText(body, 'html', 'utf-8')
        root.attach(msg)
        del root['Content-Transfer-Encoding']
        for k, v in headers.items():
            set_header(root, k, v)
        email = (from_addr, recp, root.as_string())
        # Write mail to /tmp
        #import logging
        #if self.log.isEnabledFor(logging.DEBUG):
        #   (fd, tmpname) = mkstemp()
        #   os.write(fd, email[2])
        #   os.close(fd)
        #   self.log.debug('Wrote mail from %s to %s to %s', email[0], email[1], tmpname)
        self.log.info('Sending mail with items %s from %s to %s', resources, from_addr, recp)
        try:
            if using_announcer:
                if mailsys.use_threaded_delivery:
                    mailsys.get_delivery_queue().put(email)
                else:
                    mailsys.send(*email)
            else:
                mailsys.send_email(*email)
        except Exception, e:
            raise TracError(e.message)
        return files

    def _format_email(self, authname, sender, recipients, subject, text, mode, links=[], attachments=[]):

        if text:
            req = Mock(
                href=Href(self.env.abs_href()),
                abs_href=self.env.abs_href,
                authname=authname,
                perm=MockPerm(),
                chrome=dict(
                    warnings=[],
                    notices=[]
                    ),
                args={}
                )
            context = Context.from_request(req)
            formatter = HtmlFormatter(self.env, context, text)
            try:
                htmlmessage = formatter.generate(True)
            except Exception, e:
                self.log.error("Failed to render %s", repr(text))
                self.log.error(exception_to_unicode(e, traceback=True))
                htmlmessage = text
        else:
            htmlmessage = "No message supplied."
        data = {'sendername': sender[0],
                'senderaddress': sender[1],
                'comment': htmlmessage,
                'links' : links,
                'mode': mode,
                'attachments': attachments,
                'project_name': self.env.project_name,
                'project_desc': self.env.project_description,
                'project_link': self.env.project_url or self.env.abs_href()}
        chrome = Chrome(self.env)
        template = chrome.load_template(self.html_template_name)
        if template:
            stream = template.generate(**data)
            output = stream.render()
        return output

    def _make_charset(self):
        charset = Charset()
        charset.input_charset = 'utf-8'
        pref = self.mime_encoding.lower()
        if pref == 'base64':
            charset.header_encoding = BASE64
            charset.body_encoding = BASE64
            charset.output_charset = 'utf-8'
            charset.input_codec = 'utf-8'
            charset.output_codec = 'utf-8'
        elif pref in ['qp', 'quoted-printable']:
            charset.header_encoding = QP
            charset.body_encoding = QP
            charset.output_charset = 'utf-8'
            charset.input_codec = 'utf-8'
            charset.output_codec = 'utf-8'
        elif pref == 'none':
            charset.header_encoding = None
            charset.body_encoding = None
            charset.input_codec = None
            charset.output_charset = 'ascii'
        else:
            raise TracError(_('Invalid email encoding setting: %s' % pref))
        return charset

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        if filename == 'browser.html' and req.method == 'GET':

            # we can only work from the 'dir' view at the moment
            if data.get('file'):
                return stream

            # TODO check that contextmenu's InternalNameHolder is enabled, as our js needs it?
            add_stylesheet(req, 'sourcesharer/filebox.css')
            add_javascript(req, 'sourcesharer/filebox.js')
            # Render the filebox template for stream insertion

            # TODO introduce a new interface to allow putting extra buttons into this filebox?
            tmpl = TemplateLoader(self.get_templates_dirs()).load('filebox.html')
            filebox = tmpl.generate(href=req.href, reponame=data['reponame'] or '', rev=data['rev'], files=[])
            # Wrap and float dirlist table, add filebox div
            # TODO change the id names, left/right seems a bit generic to assume we can have to ourselves
            stream |= Transformer('//table[@id="dirlist"]').wrap(tag.div(id="outer",style="clear:both")).wrap(tag.div(id="left"))
            stream |= Transformer('//div[@id="outer"]').append(tag.div(filebox, id="right"))

            is_svn_repo = False
            if 'repos' in data:
                is_svn_repo = isinstance(data.get('repos'), 
                                    (SvnCachedRepository, 
                                    SubversionRepository)) or False
            if is_svn_repo:
                add_ctxtnav(req, tag.a(_(tag.i(class_="fa fa-envelope-o")), " Send", href="", title=_("Send selected files"), id='share-files', class_='alt-button share-files-multiple'),
                    category='ctxtnav', order=10)

        return stream

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        return [('sourcesharer', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]

    # IRequestHandler methods

    def process_request(self, req):
        if req.method != 'POST':
            raise TracError(_("Only POST is supported"))

        files =   req.args.get('filebox-files')
        if not isinstance(files, list):
            files = [files]
        users =   req.args.get('user')
        if not isinstance(users, list):
            users = [users]
        subject = req.args.get('subject')
        message = req.args.get('message')
        reponame = req.args.get('repository')
        mode = int(req.args.get('mode', self.LINKS_ONLY))
        rev = req.args.get('rev', None)
        if rev:
            rev = int(rev)
        repo = RepositoryManager(self.env).get_repository(reponame)
        recipients = []
        to_send = []
        failures = []
        
        sender = self._get_address_info(req.authname)
        for u in users:
            try:
                address = self._get_address_info(u)
            except Exception, e:
                failures.append(str(e))
                continue
            recipients.append(address)
        for f in files:
            # TODO: add ?rev=xxx and select correct version
            try:
                file_res = self._get_file_resource(req, realm='source',
                                                   parent=repo.resource,
                                                   path=f)
                # req.perm(file_res).require('BROWSER_VIEW') for the perm check maybe?
            except Exception, e:
                failures.append(str(e))
                continue
            if not hasattr(file_res, 'realm') or file_res.realm != 'source':
                failures.append("Resources must have the 'realm' attribute")
                continue
            repo = RepositoryManager(self.env).get_repository(file_res.parent.id)
            n = repo.get_node(file_res.id, rev=file_res.version)
            if not n.isfile:
                failures.append("Resources must be files")
                continue
            to_send.append(file_res)
        if not failures:
            try:
                files = self.send_as_email(req, sender, recipients, subject, message, mode, *to_send)
            except Exception, e:
                files = []
                failures.append(str(e))
        else:
            files = []
        response = dict(files=files, recipients=[x[1] for x in recipients],
                        failures=failures)
        if failures != []:
            msg = ", ".join(failures)
            add_warning(req, msg)
            self.log.error('Failures in source sharing: %s', msg)
        if 'XMLHttpRequest' == req.get_header('X-Requested-With'):
            req.send(to_json(response), 'text/json')
        else:
            add_notice(req, _("Sent %(files)s to %(recipients)s",
                         files=', '.join(files),
                         recipients=', '.join([x[1] for x in recipients])))
            req.redirect()

    def match_request(self, req):
        return req.path_info == '/share'

    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['BROWSER_VIEW', 'FILE_VIEW']

    #IAutoCompleteUser

    def get_templates(self):
        return {'browser.html': [('#user-select', 'select', {})]}

    # Other

    def _get_address_info(self, authname):
        "TODO: check env.get_known_users"
        # First check if it's a #define user
        sess = DetachedSession(self.env, authname)
        address = sess.get('email')
        real_name = None
        if not address:
            # Otherwise check if it's a valid email address
            real_name, address = self.parse_address(authname)
            if not address:
                if not sess.get('email'):
                    raise ValueError(_('User %(user)s has no email address set',
                                       user=authname))
                else:
                    raise ValueError(_('%(address)s is not a valid email address',
                                       address=address))
        if not real_name:
            real_name = sess.get('name')
        return real_name, address

    def _get_file_resource(self, req, realm, parent, path):
        """Should raise if path doesn't exist or user has insufficient perms
        TODO: handle attachments and other sendable resources
        """
        req.perm.require('FILE_VIEW')
        file_res = Resource(realm, path, parent=parent)
        return file_res

    _emailfmt = re.compile(r'^\s*(?:"?(.*?)"?\s+)?<?(%s)>?\s*$' % EMAIL_LOOKALIKE_PATTERN)

    def parse_address(self, s):
        if not s:
            return None, None
        m = self._emailfmt.search(s)
        if m:
            return m.group(1), m.group(2)
        return None, None
