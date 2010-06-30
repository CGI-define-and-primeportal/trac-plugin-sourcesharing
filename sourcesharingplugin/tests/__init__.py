from trac.test import TestSetup, EnvironmentStub
from trac.tests.notification import SMTPThreadedServer
import sourcesharingplugin
import unittest

class SmtpTestSuite(TestSetup):
    
    def setUp(self):
        # Set up test smtpserver
        smtp_port = 2525
        server = SMTPThreadedServer(port=smtp_port)
        server.start()
        # Set up environment
        env = EnvironmentStub(enable=['trac.*', 'announcer.*', 'sourcesharingplugin.*'])
        if sourcesharingplugin.sourcesharer.using_announcer:
            env.config.set('smtp', 'port', smtp_port)
        else:
            env.config.set('notifications', 'smtp_port', smtp_port)
        self.fixture = env, server
         
    def tearDown(self):
        env, server = self.fixture
        server.stop()
        env.destroy_db()
        env.shutdown()

def suite():
    suite = unittest.TestSuite()
    from sourcesharingplugin.tests import sourcesharer
    suite.addTest(sourcesharer.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')