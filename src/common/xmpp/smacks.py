from protocol import Acks
from protocol import NS_STREAM_MGMT
import logging
log = logging.getLogger('gajim.c.x.smacks')

class Smacks():
    '''
    This is Smacks is the Stream Management class. It takes care of requesting
    and sending acks. Also, it keeps track of the unhandled outgoing stanzas.
    
    The dispatcher has to be able to access this class to increment the 
    number of handled stanzas
    '''


    def __init__(self, owner):
        self._owner = owner
        self.out_h = 0 # Outgoing stanzas handled
        self.in_h = 0  # Incoming stanzas handled
        self.uqueue = [] # Unhandled stanzas queue
        self.sesion_id = None
        self.supports_resume = False # If server supports resume
        # Max number of stanzas in queue before making a request
        self.max_queue = 5  
        # Register handlers 
        owner.Dispatcher.RegisterNamespace(NS_STREAM_MGMT)
        owner.Dispatcher.RegisterHandler('enabled', self._neg_response
                                         ,xmlns=NS_STREAM_MGMT)
        owner.Dispatcher.RegisterHandler('r', self.send_ack
                                         ,xmlns=NS_STREAM_MGMT)
        owner.Dispatcher.RegisterHandler('a', self.check_ack
                                         ,xmlns=NS_STREAM_MGMT)

        
    def negociate(self):
        stanza = Acks()
        stanza.buildEnable(resume=True)
        self._owner.Connection.send(stanza, now=True)
        
    def _neg_response(self, disp, stanza):
        r = stanza.getAttr('resume')
        if r == 'true':
            self.supports_resume = True
            self.sesion_id = stanza.getAttr(id)
            
    
    def send_ack(self, disp, stanza):
        ack = Acks()
        ack.buildAnswer(self.in_h)
        self._owner.Connection.send(ack, False)
        
    def request_ack(self):
        r = Acks()
        r.buildRequest()
        self._owner.Connection.send(r, False)
        
    def check_ack(self, disp, stanza):
        ''' Checks if the number of stanzas sent are the same as the
            number of stanzas received by the server. Pops stanzas that were
            handled by the server from the queue.
        '''
        h = int(stanza.getAttr('h'))
        diff = self.out_h - h
        

        if len(self.uqueue) < diff or diff < 0:
            log.error('Server and client number of stanzas handled mismatch ')
            return
        
        while (len(self.uqueue) > diff):
            self.uqueue.pop(0)
        

        
