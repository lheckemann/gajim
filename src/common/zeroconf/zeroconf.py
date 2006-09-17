##      common/zeroconf/zeroconf.py
##
## Copyright (C) 2006 Stefan Bethge <stefan@lanpartei.de>
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

import os
import sys
import socket
from common import gajim
from common import xmpp

try:
	import avahi, gobject, dbus
except ImportError:
	gajim.log.debug("Error: python-avahi and python-dbus need to be installed. No zeroconf support.")

try:
	import dbus.glib
except ImportError, e:
	pass


C_NAME, C_DOMAIN, C_INTERFACE, C_PROTOCOL, C_HOST, \
C_ADDRESS, C_PORT, C_BARE_NAME, C_TXT = range(9)

class Zeroconf:
	def __init__(self, new_serviceCB, remove_serviceCB, name, host, port):
		self.domain = None   # specific domain to browse
		self.stype = '_presence._tcp'	
		self.port = port  # listening port that gets announced	
		self.username = name
		self.host = host
		self.name = self.username+'@'+ self.host # service name
		self.txt = {}		# service data
		
		self.new_serviceCB = new_serviceCB
		self.remove_serviceCB = remove_serviceCB
		
		self.service_browsers = {}
		self.contacts = {}    # all current local contacts with data
		self.entrygroup = None
		self.connected = False
		self.announced = False

	## handlers for dbus callbacks

	# error handler - maybe replace with gui version/gajim facilities
	def print_error_callback(self, err):
		print "Error:", str(err)

	def new_service_callback(self, interface, protocol, name, stype, domain, flags):
		# we don't want to see ourselves in the list
		if name != self.name:
			# print "Found service '%s' in domain '%s' on %i.%i." % (name, domain, interface, protocol)
		
			#synchronous resolving
			self.server.ResolveService( int(interface), int(protocol), name, stype, \
						domain, avahi.PROTO_UNSPEC, dbus.UInt32(0), \
						reply_handler=self.service_resolved_callback, error_handler=self.print_error_callback)

	def remove_service_callback(self, interface, protocol, name, stype, domain, flags):
		# print "Service '%s' in domain '%s' on %i.%i disappeared." % (name, domain, interface, protocol)
		if name != self.name:
			for key in self.contacts.keys():
				if self.contacts[key][C_BARE_NAME] == name:
					del self.contacts[key]
					self.remove_serviceCB(key)
					return

	def new_service_type(self, interface, protocol, stype, domain, flags):
		# Are we already browsing this domain for this type? 
		if self.service_browsers.has_key((interface, protocol, stype, domain)):
			return

		# print "Browsing for services of type '%s' in domain '%s' on %i.%i ..." % (stype, domain, interface, protocol)

		b = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, \
				self.server.ServiceBrowserNew(interface, protocol, \
				stype, domain, dbus.UInt32(0))),avahi.DBUS_INTERFACE_SERVICE_BROWSER)
		b.connect_to_signal('ItemNew', self.new_service_callback)
		b.connect_to_signal('ItemRemove', self.remove_service_callback)

		self.service_browsers[(interface, protocol, stype, domain)] = b

	def new_domain_callback(self,interface, protocol, domain, flags):
		if domain != "local":
			self.browse_domain(interface, protocol, domain)

	def txt_array_to_dict(self,txt_array):
		items = {}

		for byte_array in txt_array:
			# 'str' is used for string type in python
			value = avahi.byte_array_to_string(byte_array)
			poseq = value.find('=')
			items[value[:poseq]] = value[poseq+1:]
		return items
	
	def service_resolved_callback(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):	
		print "Service data for service '%s' in domain '%s' on %i.%i:" % (name, domain, interface, protocol)
		print "\tHost %s (%s), port %i, TXT data: %s" % (host, address, port, avahi.txt_array_to_string_array(txt))
		bare_name = name
		if name.find('@') == -1:
			name = name + '@' + name
		
		self.contacts[name] = (name, domain, interface, protocol, host, address, port, 
					bare_name, txt)
		self.new_serviceCB(name)

	# different handler when resolving all contacts
	def service_resolved_all_callback(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		#print "Service data for service '%s' in domain '%s' on %i.%i:" % (name, domain, interface, protocol)
		#print "\tHost %s (%s), port %i, TXT data: %s" % (host, address, port, str(avahi.txt_array_to_string_array(txt)))
		bare_name = name
		if name.find('@') == -1:
			name = name + '@' + name
		self.contacts[name] = (name, domain, interface, protocol, host, address, port, bare_name, txt)

	def service_added_callback(self):
		# print 'Service successfully added'
		pass

	def service_committed_callback(self):
		# print 'Service successfully committed'
		pass

	def service_updated_callback(self):
		# print 'Service successfully updated'
		pass

	def service_add_fail_callback(self, err):
		print 'Error while adding service:', str(err)
		self.name = self.server.GetAlternativeServiceName(self.name)
		self.create_service()

	def server_state_changed_callback(self, state, error):
		print 'server.state %s' % state
		if state == avahi.SERVER_RUNNING:
			self.create_service()
		elif state == avahi.SERVER_COLLISION:
			self.entrygroup.Reset()
#		elif state == avahi.CLIENT_FAILURE:           # TODO: add error handling (avahi daemon dies...?)

	def entrygroup_state_changed_callback(self, state, error):
		# the name is already present, so recreate
		if state == avahi.ENTRY_GROUP_COLLISION:
			self.service_add_fail_callback('Local name collision, recreating.')
		elif state == avahi.ENTRY_GROUP_FAILURE:
			print 'zeroconf.py: ENTRY_GROUP_FAILURE reached(that should not happen)'

	# make zeroconf-valid names
	def replace_show(self, show):
		if show == 'chat' or show == 'online' or show == '':
			show = 'avail'
		elif show == 'xa':
			show = 'away'
		return show

	def create_service(self):
		try:
			if not self.entrygroup:
				# create an EntryGroup for publishing
				self.entrygroup = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)
				self.entrygroup.connect_to_signal('StateChanged', self.entrygroup_state_changed_callback)

			self.txt['port.p2pj'] = self.port
			self.txt['version'] = 1
			self.txt['txtvers'] = 1
			
			# replace gajim's show messages with compatible ones
			if self.txt.has_key('status'):
					self.txt['status'] = self.replace_show(self.txt['status'])

			# print "Publishing service '%s' of type %s" % (self.name, self.stype)
			self.entrygroup.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), self.name, self.stype, '', '', self.port, avahi.dict_to_txt_array(self.txt), reply_handler=self.service_added_callback, error_handler=self.service_add_fail_callback)
			self.entrygroup.Commit(reply_handler=self.service_committed_callback, error_handler=self.print_error_callback)

			return True
		
		except dbus.dbus_bindings.DBusException, e:
			gajim.log.debug(str(e))
			return False
			
	def announce(self):
		if self.connected:
			state = self.server.GetState()

			if state == avahi.SERVER_RUNNING:
				self.create_service()
				self.announced = True
				return True
		else:
			return False

	def remove_announce(self):
		if self.announced == False:
			return False
		try:
			if self.entrygroup.GetState() != avahi.ENTRY_GROUP_FAILURE:
				self.entrygroup.Reset()
				self.entrygroup.Free()
				self.entrygroup = None
				self.announced = False
				return True
			else:
				return False
		except dbus.dbus_bindings.DBusException, e:
			print "zeroconf.py: Can't remove service, avahi daemon not running?"

	def browse_domain(self, interface, protocol, domain):
		self.new_service_type(interface, protocol, self.stype, domain, '')

	# connect to dbus
	def connect(self):
		try:
			self.bus = dbus.SystemBus()
			# is there any way to check, if a dbus name exists?
			# that might make the Introspect Error go away...
			self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, \
			avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
			
			self.server.connect_to_signal('StateChanged', self.server_state_changed_callback)
		except dbus.dbus_bindings.DBusException, e:
			# Avahi service is not present
			gajim.log.debug(str(e))
			return False

		self.connected = True
		
		# start browsing
		if self.domain is None:
			# Explicitly browse .local
			self.browse_domain(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, "local")

			# Browse for other browsable domains
			db = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, \
					self.server.DomainBrowserNew(avahi.IF_UNSPEC, \
					avahi.PROTO_UNSPEC, '', avahi.DOMAIN_BROWSER_BROWSE,\
					dbus.UInt32(0))), avahi.DBUS_INTERFACE_DOMAIN_BROWSER)
			db.connect_to_signal('ItemNew', self.new_domain_callback)
		else:
			self.browse_domain(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, domain)

		return True

	def disconnect(self):
		if self.connected:
			self.connected = False
			self.remove_announce()

	# refresh txt data of all contacts manually (no callback available)
	def resolve_all(self):
		for val in self.contacts.values():
			self.server.ResolveService(int(val[C_INTERFACE]), int(val[C_PROTOCOL]), val[C_BARE_NAME], \
				self.stype, val[C_DOMAIN], avahi.PROTO_UNSPEC, dbus.UInt32(0),\
				reply_handler=self.service_resolved_all_callback, error_handler=self.print_error_callback)

	def get_contacts(self):
		return self.contacts

	def get_contact(self, jid):
		return self.contacts[jid]
		
	def update_txt(self, txt):
		# update only given keys
		for key in txt.keys():
			self.txt[key]=txt[key]

		if txt.has_key('status'):
			self.txt['status'] = self.replace_show(txt['status'])

		txt = avahi.dict_to_txt_array(self.txt)
		if self.entrygroup:
			self.entrygroup.UpdateServiceTxt(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), self.name, self.stype,'', txt, reply_handler=self.service_updated_callback, error_handler=self.print_error_callback)
			return True
		else:
			return False

	def send (self, msg, sock):
		print 'send:'+msg
		totalsent = 0
		while totalsent < len(msg):
			sent = sock.send(msg[totalsent:])
			if sent == 0:
				raise RuntimeError, "socket connection broken"
			totalsent = totalsent + sent

	def send_message(self, jid, msg, type = 'chat'):
		print 'zeroconf.py: send_message:'+ msg
		
		sock = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
		#sock.setblocking(False)
		sock.connect ( ( self.contacts[jid][C_ADDRESS], self.contacts[jid][C_PORT] ) )
		
		#print (self.txt_array_to_dict(self.contacts[jid][C_TXT]))['port.p2pj']

		#was for adium which uses the txt record
		#sock.connect ( ( self.contacts[jid][5], int((self.txt_array_to_dict(self.contacts[jid][7]))['port.p2pj']) ) )
		
		self.send("<?xml version='1.0' encoding='UTF-8'?><stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams'>", sock)
	
		try: recvd = sock.recv(16384)
		except: recvd = ''
		print 'receive:' + recvd
		
		message = xmpp.Message(typ=type, to=jid, frm=self.name)
		message.setBody(msg)
#		no html for now, necessary for anything else but adium?
#		html = message.getTag('html', namespace = 'html://www.w3.org/1999/xhtml')
#		html.addChild(...
		message.addChild(name = 'x', namespace = xmpp.NS_EVENT).addChild(name = 'composing')

		self.send(str(message),sock)

		#adium requires the html parts
		#self.send("<message to='" + jid + "' from='" + self.name + "' type='" + type + "'><body>" + msg + "</body><html xmlns='html://www.w3.org/1999/xhtml'><body ichatballoncolor='#5598d7' ichattextcolor='#000000'><font face='Courier' ABSZ='3'>" + msg +"</font></body></html><x xmlns='jabber:x:event'><composing /></x></message>", sock)

		self.send('</stream>', sock)
		sock.close()

# END Zeroconf

'''
# how to use
		
	zeroconf = Zeroconf()
	zeroconf.connect()				
	zeroconf.txt['1st'] = 'foo'
	zeroconf.txt['last'] = 'bar'
	zeroconf.txt['email'] = foo@bar.org
	zeroconf.announce()

	# updating after announcing
	txt = {}
	txt['status'] = 'avail'
	txt['msg'] = 'Here I am'
	zeroconf.update_txt(txt)
'''
