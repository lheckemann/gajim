##
## Copyright (C) 2006 Gajim Team
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##

"""
Handles Jingle contents (XEP 0166)
"""

import xmpp
from jingle_transport import JingleTransportIBB

contents = {}

def get_jingle_content(node):
    namespace = node.getNamespace()
    if namespace in contents:
        return contents[namespace](node)


class JingleContentSetupException(Exception):
    """
    Exception that should be raised when a content fails to setup.
    """


class JingleContent(object):
    """
    An abstraction of content in Jingle sessions
    """

    def __init__(self, session, transport):
        self.session = session
        self.transport = transport
        # will be filled by JingleSession.add_content()
        # don't uncomment these lines, we will catch more buggy code then
        # (a JingleContent not added to session shouldn't send anything)
        #self.creator = None
        #self.name = None
        self.accepted = False
        self.sent = False
        self.negotiated = False

        self.media = None

        self.senders = 'both' #FIXME
        self.allow_sending = True # Used for stream direction, attribute 'senders'

        self.callbacks = {
                # these are called when *we* get stanzas
                'content-accept': [self.__on_transport_info,
                        self.__on_content_accept],
                'content-add': [self.__on_transport_info],
                'content-modify': [],
                'content-reject': [],
                'content-remove': [],
                'description-info': [],
                'security-info': [],
                'session-accept': [self.__on_transport_info,
                        self.__on_content_accept],
                'session-info': [],
                'session-initiate': [self.__on_transport_info],
                'session-terminate': [],
                'transport-info': [self.__on_transport_info],
                'transport-replace': [self.__on_transport_replace],
                'transport-accept': [],
                'transport-reject': [],
                'iq-result': [],
                'iq-error': [],
                # these are called when *we* sent these stanzas
                'content-accept-sent': [self.__fill_jingle_stanza,
                        self.__on_content_accept],
                'content-add-sent': [self.__fill_jingle_stanza],
                'session-initiate-sent': [self.__fill_jingle_stanza],
                'session-accept-sent': [self.__fill_jingle_stanza,
                        self.__on_content_accept],
                'session-terminate-sent': [],
        }

    def is_ready(self):
        return self.accepted and not self.sent

    def __on_content_accept(self, stanza, content, error, action):
        self.on_negotiated()

    def on_negotiated(self):
        if self.accepted:
            self.negotiated = True
            self.session.content_negotiated(self.media)

    def add_remote_candidates(self, candidates):
        """
        Add a list of candidates to the list of remote candidates
        """
        self.transport.remote_candidates = candidates

    def on_stanza(self, stanza, content, error, action):
        """
        Called when something related to our content was sent by peer
        """
        if action in self.callbacks:
            for callback in self.callbacks[action]:
                callback(stanza, content, error, action)

    def __on_transport_replace(self, stanza, content, error, action):
        content.addChild(node=self.transport.make_transport())

    def __on_transport_info(self, stanza, content, error, action):
        """
        Got a new transport candidate
        """
        candidates = self.transport.parse_transport_stanza(
            content.getTag('transport'))
        if candidates:
            self.add_remote_candidates(candidates)

    def __content(self, payload=[]):
        """
        Build a XML content-wrapper for our data
        """
        return xmpp.Node('content',
                attrs={'name': self.name, 'creator': self.creator},
                payload=payload)

    def send_candidate(self, candidate):
        """
        Send a transport candidate for a previously defined transport.
        """
        content = self.__content()
        content.addChild(node=self.transport.make_transport([candidate]))
        self.session.send_transport_info(content)

    def send_error_candidate(self):
        """
        Sends a candidate-error when we can't connect to a candidate.
        """
        content = self.__content()
        tp = self.transport.make_transport(add_candidates=False)
        tp.addChild(name='candidate-error')
        content.addChild(node=tp)
        self.session.send_transport_info(content)


    def send_description_info(self):
        content = self.__content()
        self._fill_content(content)
        self.session.send_description_info(content)

    def __fill_jingle_stanza(self, stanza, content, error, action):
        """
        Add our things to session-initiate stanza
        """
        self._fill_content(content)
        self.sent = True
        content.addChild(node=self.transport.make_transport())

    def _fill_content(self, content):
        description_node = xmpp.simplexml.Node(
            tag=xmpp.NS_JINGLE_FILE_TRANSFER + ' description')
        if self.session.werequest:
            simode = xmpp.simplexml.Node(tag='request')
        else:
            simode = xmpp.simplexml.Node(tag='offer')
        file_tag = simode.setTag('file', namespace=xmpp.NS_FILE)
        if self.file_props.name:
            node = xmpp.simplexml.Node(tag='name')
            node.addData(self.file_props.name)
            file_tag.addChild(node=node)
        if self.file_props.size:
            node = xmpp.simplexml.Node(tag='size')
            node.addData(self.file_props.size)
            file_tag.addChild(node=node)
        if self.file_props.type_ == 'r':
            if self.file_props.hash_:
                h = file_tag.addChild('hash', attrs={
                    'algo': self.file_props.algo}, namespace=xmpp.NS_HASHES,
                    payload=self.file_props.hash_)
        else:
            # if the file is less than 10 mb, then it is small
            # lets calculate it right away
            if int(self.file_props.size) < 10000000 and not \
                                        self.file_props.hash_:
                h  = self._calcHash()
                file_tag.addChild(node=h)
                file_info = {'name' : self.file_props.name,
                             'hash' : self.file_props.hash_,
                             'size' : self.file_props.size,
                             'date' : self.file_props.date
                            }
                self.session.connection.set_files_info(file_info)
        desc = file_tag.setTag('desc')
        if self.file_props.desc:
            desc.setData(self.file_props.desc)
        description_node.addChild(node=simode)
        if self.use_security:
            security = xmpp.simplexml.Node(
                tag=xmpp.NS_JINGLE_XTLS + ' security')
            # TODO: add fingerprint element
            for m in ('x509', ): # supported authentication methods
                method = xmpp.simplexml.Node(tag='method')
                method.setAttr('name', m)
                security.addChild(node=method)
            content.addChild(node=security)
        content.addChild(node=description_node)

    def destroy(self):
        self.callbacks = None
        del self.session.contents[(self.creator, self.name)]


