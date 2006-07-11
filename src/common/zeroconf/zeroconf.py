import os
import sys
import socket
from common import gajim
try:
	import avahi, gobject, dbus
except ImportError:
	print "Error: python-avahi and python-dbus need to be installed. No zeroconf support."

try:
	import dbus.glib
except ImportError, e:
	pass

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
		
	## handlers for dbus callbacks

	# error handler - maybe replace with gui version/gajim facilities
	def print_error_callback(self, err):
		print "Error:", str(err)

	def new_service_callback(self, interface, protocol, name, stype, domain, flags):
		if True:
		#XXX name != self.name
			# print "Found service '%s' in domain '%s' on %i.%i." % (name, domain, interface, protocol)
		
			#synchronous resolving
			self.server.ResolveService( int(interface), int(protocol), name, stype, \
						domain, avahi.PROTO_UNSPEC, dbus.UInt32(0), \
						reply_handler=self.service_resolved_callback, error_handler=self.print_error_callback)

	def remove_service_callback(self, interface, protocol, name, stype, domain, flags):
		# print "Service '%s' in domain '%s' on %i.%i disappeared." % (name, domain, interface, protocol)
		del self.contacts[name]
		self.remove_serviceCB(name)

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

	def check_jid(self, jid):
		# TODO: at least miranda uses bad service names(only host name), so change them - probabaly not so nice... need to find a better solution
		# [dkirov] maybe turn it into host+'@'+host, instead ?
		if jid.find('@') == -1:
			return 'bad-client@' + jid
		else:
			return jid
		
	def recreate_bad_jid(self,jid):
		at = jid.find('@')
		if  jid[:at] == 'bad-client':
			return jid[at+1:]
		else:
			return jid
		
	def txt_array_to_dict(self,txt_array):
		items = {}

		for byte_array in txt_array:
			# 'str' is used for string type in python
			value = avahi.byte_array_to_string(byte_array)
			poseq = value.find('=')
			items[value[:poseq]] = value[poseq+1:]
		return items
	
	def service_resolved_callback(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):	
		self.contacts[name] = (name, domain, interface, protocol, host, address, port, txt)
		self.new_serviceCB(name)

	# different handler when resolving all contacts
	def service_resolved_all_callback(self, interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags):
		#print "Service data for service '%s' in domain '%s' on %i.%i:" % (name, domain, interface, protocol)
		#print "\tHost %s (%s), port %i, TXT data: %s" % (host, address, port, str(avahi.txt_array_to_string_array(txt)))
		
		self.contacts[name] = (name, domain, interface, protocol, host, address, port, txt)

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

#		elif state == avahi.ENTRY_GROUP_FAILURE:

	# make zeroconf-valid names
	def replace_show(self, show):
		if show == 'chat' or show == '':
			show = 'online'
		elif show == 'xa':
			show = 'away'
		elif show == 'online':
			show = 'avail'
		return show

	def create_service(self):
		if not self.entrygroup:
			# create an EntryGroup for publishing
			self.entrygroup = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)
			self.entrygroup.connect_to_signal('StateChanged', self.entrygroup_state_changed_callback)

		self.txt['port.p2pj'] = self.port
		self.txt['version'] = 1
		self.txt['textvers'] = 1
		
		# replace gajim's status messages with proper ones
		if self.txt.has_key('status'):
				self.txt['status'] = self.replace_show(self.txt['status'])

		# print "Publishing service '%s' of type %s" % (self.name, self.stype)
		self.entrygroup.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), self.name, self.stype, '', '', self.port, avahi.dict_to_txt_array(self.txt), reply_handler=self.service_added_callback, error_handler=self.service_add_fail_callback)
		self.entrygroup.Commit(reply_handler=self.service_committed_callback, error_handler=self.print_error_callback)

	def announce(self):
		state = self.server.GetState()

		if state == avahi.SERVER_RUNNING:
			self.create_service()

	def remove_announce(self):
		if self.entrygroup:
			self.entrygroup.Reset()
			self.entrygroup.Free()
			self.entrygroup = None

	def browse_domain(self, interface, protocol, domain):
		self.new_service_type(interface, protocol, self.stype, domain, '')

	# connect to dbus
	def connect(self):
		self.bus = dbus.SystemBus()
		self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, \
			avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
		try:
			self.server.connect_to_signal('StateChanged', self.server_state_changed_callback)
		except dbus.dbus_bindings.DBusException, e:
			# Avahi service is not present
			gajim.log.debug(str(e))
			self.remove_announce()
			return
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

	def disconnect(self):
		self.remove_announce()

	# refresh data manually - really ok or too much traffic?
	def resolve_all(self):
		for val in self.contacts.values():
			#val:(name, domain, interface, protocol, host, address, port, txt)
			self.server.ResolveService(int(val[2]), int(val[3]), val[0], \
				self.stype, val[1], avahi.PROTO_UNSPEC, dbus.UInt32(0),\
				reply_handler=self.service_resolved_all_callback, error_handler=self.print_error_callback)
		
	def get_contacts(self):
		return self.contacts

	def get_contact(self, jid):
		if self.contacts.has_key(jid):
			return self.contacts[jid]
		
	def update_txt(self, txt):
		# update only given keys
		for key in txt.keys():
			self.txt[key]=txt[key]

		if txt.has_key('status'):
			self.txt['status'] = self.replace_show(txt['status'])

		txt = avahi.dict_to_txt_array(self.txt)

		self.entrygroup.UpdateServiceTxt(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), self.name, self.stype,'', txt, reply_handler=self.service_updated_callback, error_handler=self.print_error_callback)
#		self.entrygroup.Commit()         # TODO: necessary?

	
	def send (self, msg, sock):
		print 'send:'+msg
		totalsent = 0
		while totalsent < len(msg):
			sent = sock.send(msg[totalsent:])
			if sent == 0:
				raise RuntimeError, "socket connection broken"
			totalsent = totalsent + sent

	def send_message(self, jid, msg):
		print 'zeroconf.py: send_message:'+ msg
		jid = self.recreate_bad_jid(jid)
			
		sock = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
 		#sock.setblocking(False)
		sock.connect ( ( self.contacts[jid][4], self.contacts[jid][6] ) )
		
		try : recvd = sock.recv(16384)
		except: recvd = ''
	
		print 'receive:' + recvd
		
		self.send("<?xml version='1.0' encoding='UTF-8'?><stream:stream to="+ self.contacts[jid][5] +" xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams'>", sock)

		self.send("<message to=" + jid + " type='chat'><body>" + msg + "</body><html xmlns='html://www.w3.org/1999/xhtml'><body ichatballoncolor='#111111' ichattextcolor='#000000'><font face='Courier' ABSZ='3'>" + msg +"</font></body></html><x xmlns='jabber:x:event'><delivered /></x></message>", sock)
		
		try: recvd = sock.recv(16384)
		except: recvd = ''
		print 'receive:' + recvd

		self.send('</stream>', sock)
		sock.close()

# END Zeroconf

'''
# how to use
		
	zeroconf = Zeroconf()
	zeroconf.connect()				
	zeroconf.txt['1st'] = 'foo'
	zeroconf.txt['last'] = 'bar'
	zeroconfptxt['email'] = foo@bar.org
	zeroconf.announce()

	# updating after announcing
	txt = {}
	txt['status'] = 'avail'
	txt['msg'] = 'Here I am'
	zeroconf.update_txt(txt)
'''
