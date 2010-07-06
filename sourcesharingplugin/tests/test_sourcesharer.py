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

# py.test
#smtp_port = 2525
#
#def start_server(smtp_port):
#    server = SMTPThreadedServer(port=smtp_port)
#    server.start()
#    return server
#
#def pytest_funcarg__server(request):
#    return request.cached_setup(
#        setup=lambda: start_server(smtp_port),
#        teardown=lambda server: server.stop(),
#        scope='module'
#    )
#
#def pytest_funcarg__sharesys(request):
#    # Set up environment
#    env = EnvironmentStub(enable=['trac.*', 'announcer.*', 'sourcesharingplugin.*'])
#    if sourcesharingplugin.sourcesharer.using_announcer:
#        env.config.set('smtp', 'port', smtp_port)
#    else:
#        env.config.set('notifications', 'smtp_port', smtp_port)
#    ss = SharingSystem(env)
#    return ss
#
#class TestSharingSystem:
#    def test_send_mail(self, server, sharesys):
#        dir = resource_filename(__name__, os.path.join('..', 'htdocs'))
#        files = [os.path.join(dir, f) for f in os.listdir(dir)]
#        subject = 'Sending söme files'
#        body = 'Here you go (Här får du)'
#        b64body = body.encode('base64').strip() 
#        mail = sharesys.send_as_email(('Pöntus Enmärk', 
#                                              'pontus.enmark@logica.com'), 
#                                              [('Pontus Enmark', 
#                                                'pontus.enmark@logica.com'),
#                                               ('Pöntus Enmärk',
#                                                'pontus.enmark@gmail.com')], 
#                                                subject,
#                                                body,
#                                                *files)
#        headers, sent_body = parse_smtp_message(server.store.message)
#        assert  b64body in sent_body, (b64body, sent_body)
#        assert 'söme'.decode('utf-8') in headers['Subject'], headers
#        assert os.path.basename(files[0]) in sent_body

# nose
class SharingSystemTestCase(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        cls.server = SMTPThreadedServer(port=2525)
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
    
    def test_get_resource(self):
        req = Request(perm=MockPerm(), href=Href)
        repo = Resource('repository', '')
        res = self.sharesys._get_file_resource(req, 'source', repo, 'trunk')
        assert res.id == 'trunk', res
        
    def test_send_mail(self):
        dir = resource_filename(__name__, os.path.join('..', 'htdocs'))
        files = [os.path.join(dir, f) for f in os.listdir(dir)]
        subject = 'Sending söme files'
        body = 'Here you go (Här får du)'
        b64body = body.encode('base64').strip() 
        mail = self.sharesys.send_as_email(('Pöntus Enmärk', 
                                              'pontus.enmark@logica.com'), 
                                              [('Pontus Enmark', 
                                                'pontus.enmark@logica.com'),
                                               ('Pöntus Enmärk',
                                                'pontus.enmark@gmail.com')], 
                                                subject,
                                                body,
                                                *files)
        headers, sent_body = parse_smtp_message(self.server.get_message())
        assert  b64body in sent_body, (b64body, sent_body)
        assert 'söme'.decode('utf-8') in headers['Subject'], headers
        assert os.path.basename(files[0]) in sent_body
