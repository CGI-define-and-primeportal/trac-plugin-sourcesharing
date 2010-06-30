# encoding: utf-8
'''
Created on 29 Jun 2010

@author: Pontus Enmark <pontus.enmark@logica.com>
'''

from trac.test import TestCaseSetup
from sourcesharingplugin.sourcesharer import SharingSystem
from pkg_resources import resource_listdir, resource_filename
from trac.tests.notification import parse_smtp_message
import sourcesharingplugin
import unittest
import os
from sourcesharingplugin.tests import SmtpTestSuite

class SharingSystemTest(TestCaseSetup):
    
    def setFixture(self, fixture):
        # Load data set in SmtpTestSuite fixture
        self.env, self.server = fixture
    
    def setUp(self):
        self.sharingsys = SharingSystem(self.env)
        dir = resource_filename(sourcesharingplugin.__name__, 'htdocs')
        self.files = [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))] 
    
    def tearDown(self):
        self.env = None
        self.server.stop()
        
    def test_01_send_mail(self):
        subject = 'Sending söme files'
        body = 'Here you go (Här får du)'
        b64body = body.encode('base64').strip() 
        mail = self.sharingsys.send_as_email(('Pöntus Enmärk', 
                                              'pontus.enmark@logica.com'), 
                                              [('Pontus Enmark', 
                                                'pontus.enmark@logica.com'),
                                               ('Pöntus Enmärk',
                                                'pontus.enmark@gmail.com')], 
                                                subject,
                                                body,
                                                *self.files)
        headers, sent_body = parse_smtp_message(self.server.store.message)
        assert  b64body in sent_body, (b64body, sent_body)
        assert 'söme'.decode('utf-8') in headers['Subject'], headers

def suite():
    return unittest.makeSuite(SharingSystemTest, suiteClass=SmtpTestSuite)

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
