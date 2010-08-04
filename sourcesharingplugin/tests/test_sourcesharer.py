# encoding: utf-8
'''
Created on 29 Jun 2010

@author: Pontus Enmark <pontus.enmark@logica.com>
'''
from trac.test import EnvironmentStub, MockPerm
from sourcesharingplugin.sourcesharer import SharingSystem
from pkg_resources import resource_listdir, resource_filename
from trac.tests.notification import parse_smtp_message, SMTPThreadedServer
import sourcesharingplugin
import os
import unittest
from trac.web.tests.chrome import Request
from trac.resource import Resource
from trac.web.href import Href
from trac.util.text import to_unicode

class SharingSystemTestCase(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        cls.server = SMTPThreadedServer(port=2526)
        cls.server.start()
        
        env = EnvironmentStub(enable=['trac.*', 'announcer.*', 'sourcesharingplugin.*'])
        if sourcesharingplugin.sourcesharer.using_announcer:
            env.config.set('smtp', 'port', cls.server.port)
        else:
            env.config.set('notifications', 'smtp_port', cls.server.port)
        cls.env = env
    @classmethod
    def teardownClass(cls):
        cls.server.stop()
    def setUp(self):
        self.sharesys = SharingSystem(self.env)
    def tearDown(self):
        self.sharesys = None
    
    def test_get_address(self):
        pass
    
    def test_parse_email(self):
        valid = ('john.doe@logica.com', 'Doe, John john.doe@logica.com', 
                 '"John Doe" <john.doe@logica.com ', 
                 ' "Doe, John"    <john.doe+label@logica.com> ',
                 '"Örjan Pärson" <orjan.persson@logica.com>')
        invalid = ('kallekula_at_gmail_com', '', None, )
        for v in valid:
            name, address = self.sharesys.parse_address(v)
            assert address, v
        for v in invalid:
            name, address = self.sharesys.parse_address(v)
            assert name is None and address is None, v
        
    def test_get_resource(self):
        req = Request(perm=MockPerm(), href=Href)
        repo = Resource('repository', '')
        res = self.sharesys._get_file_resource(req, 'source', repo, 'trunk')
        assert res.id == 'trunk', res
        
    def test_send_mail(self):
        dir = resource_filename(__name__, os.path.join('..', 'htdocs'))
        files = [os.path.join(dir, f) for f in os.listdir(dir)]
        subjects = ('Re: åäö', 
                    u'Re: åäö',
                    'Re: ascii',
                    )
        bodies = ('Here you gö (Här får du)',
                  u'Here you gö (Här får du)',
                  'Ascii body',
                  )
        for subject in subjects:
            subject = to_unicode(subject)
            for body in bodies:
                body = to_unicode(body)
                mail = self.sharesys.send_as_email("anonymous",
                                                   (u'Pöntus Enmärk', 
                                                    'pontus.enmark@logica.com'), 
                                                   [(u'Pontus Enmark', 
                                                     'pontus.enmark@logica.com'),
                                                    (u'Pöntus Enmärk',
                                                     'pontus.enmark@gmail.com')], 
                                                   subject,
                                                   body,
                                                   *files)
                headers, sent_body = parse_smtp_message(self.server.get_message())
                assert subject == headers['Subject'], headers
                assert os.path.basename(files[0]) in sent_body
