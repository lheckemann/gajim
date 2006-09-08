##	vcard.py (has VcardWindow class and a func get_avatar_pixbuf_encoded_mime)
##
## Copyright (C) 2003-2006 Yann Le Boulanger <asterix@lagaule.org>
## Copyright (C) 2005-2006 Nikos Kouremenos <kourem@gmail.com>
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

import gtk
import gobject
import base64
import mimetypes
import os
import time
import locale

import gtkgui_helpers
import dialogs

from common import helpers
from common import gajim
from common.i18n import Q_

def get_avatar_pixbuf_encoded_mime(photo):
	'''return the pixbuf of the image
	photo is a dictionary containing PHOTO information'''
	if not isinstance(photo, dict):
		return None, None, None
	img_decoded = None
	avatar_encoded = None
	avatar_mime_type = None
	if photo.has_key('BINVAL'):
		img_encoded = photo['BINVAL']
		avatar_encoded = img_encoded
		try:
			img_decoded = base64.decodestring(img_encoded)
		except:
			pass
	if img_decoded:
		if photo.has_key('TYPE'):
			avatar_mime_type = photo['TYPE']
			pixbuf = gtkgui_helpers.get_pixbuf_from_data(img_decoded)
		else:
			pixbuf, avatar_mime_type = gtkgui_helpers.get_pixbuf_from_data(
							img_decoded, want_type=True)
	else:
		pixbuf = None
	return pixbuf, avatar_encoded, avatar_mime_type

class VcardWindow:
	'''Class for contact's information window'''

	def __init__(self, contact, account, is_fake = False):
		# the contact variable is the jid if vcard is true
		self.xml = gtkgui_helpers.get_glade('vcard_information_window.glade')
		self.window = self.xml.get_widget('vcard_information_window')

		self.contact = contact
		self.account = account
		self.is_fake = is_fake

		self.avatar_mime_type = None
		self.avatar_encoded = None

		self.fill_jabber_page()

		self.xml.signal_autoconnect(self)
		self.window.show_all()

	def on_vcard_information_window_destroy(self, widget):
		del gajim.interface.instances[self.account]['infos'][self.contact.jid]

	def on_vcard_information_window_key_press_event(self, widget, event):
		if event.keyval == gtk.keysyms.Escape:
			self.window.destroy()

	def on_log_history_checkbutton_toggled(self, widget):
		#log conversation history?
		oldlog = True
		no_log_for = gajim.config.get_per('accounts', self.account,
			'no_log_for').split()
		if self.contact.jid in no_log_for:
			oldlog = False
		log = widget.get_active()
		if not log and not self.contact.jid in no_log_for:
			no_log_for.append(self.contact.jid)
		if log and self.contact.jid in no_log_for:
			no_log_for.remove(self.contact.jid)
		if oldlog != log:
			gajim.config.set_per('accounts', self.account, 'no_log_for',
				' '.join(no_log_for))

	def on_PHOTO_eventbox_button_press_event(self, widget, event):
		'''If right-clicked, show popup'''
		if event.button == 3: # right click
			menu = gtk.Menu()
			menuitem = gtk.ImageMenuItem(gtk.STOCK_SAVE_AS)
			menuitem.connect('activate',
				gtkgui_helpers.on_avatar_save_as_menuitem_activate,
				self.contact.jid, self.account, self.contact.name + '.jpeg')
			menu.append(menuitem)
			menu.connect('selection-done', lambda w:w.destroy())	
			# show the menu
			menu.show_all()
			menu.popup(None, None, None, event.button, event.time)

	def set_value(self, entry_name, value):
		try:
			self.xml.get_widget(entry_name).set_text(value)
		except AttributeError:
			pass

	def set_values(self, vcard):
		for i in vcard.keys():
			if i == 'PHOTO':
				pixbuf, self.avatar_encoded, self.avatar_mime_type = \
					get_avatar_pixbuf_encoded_mime(vcard[i])
				image = self.xml.get_widget('PHOTO_image')
				if not pixbuf:
					image.set_from_icon_name('stock_person',
						gtk.ICON_SIZE_DIALOG)
					continue
				pixbuf = gtkgui_helpers.get_scaled_pixbuf(pixbuf, 'vcard')
				image.set_from_pixbuf(pixbuf)
				continue
			if i == 'ADR' or i == 'TEL' or i == 'EMAIL':
				for entry in vcard[i]:
					add_on = '_HOME'
					if 'WORK' in entry:
						add_on = '_WORK'
					for j in entry.keys():
						self.set_value(i + add_on + '_' + j + '_label', entry[j])
			if isinstance(vcard[i], dict):
				for j in vcard[i].keys():
					self.set_value(i + '_' + j + '_label', vcard[i][j])
			else:
				if i == 'DESC':
					self.xml.get_widget('DESC_textview').get_buffer().set_text(
						vcard[i], 0)
				else:
					self.set_value(i + '_label', vcard[i])

	def set_last_status_time(self):
		self.fill_status_label()

	def set_os_info(self, resource, client_info, os_info):
		if self.xml.get_widget('information_notebook').get_n_pages() < 4:
			return
		i = 0
		client = ''
		os = ''
		while self.os_info.has_key(i):
			if not self.os_info[i]['resource'] or \
					self.os_info[i]['resource'] == resource:
				self.os_info[i]['client'] = client_info
				self.os_info[i]['os'] = os_info
			if i > 0:
				client += '\n'
				os += '\n'
			client += self.os_info[i]['client']
			os += self.os_info[i]['os']
			i += 1

		if client == '':
			client = Q_('?Client:Unknown')
		if os == '':
			os = Q_('?OS:Unknown')
		self.xml.get_widget('client_name_version_label').set_text(client)
		self.xml.get_widget('os_label').set_text(os)

	def fill_status_label(self):
		if self.xml.get_widget('information_notebook').get_n_pages() < 4:
			return
		contact_list = gajim.contacts.get_contact(self.account, self.contact.jid)
		# stats holds show and status message
		stats = ''
		one = True # Are we adding the first line ?
		if contact_list:
			for c in contact_list:
				if not one:
					stats += '\n'
				stats += helpers.get_uf_show(c.show)
				if c.status:
					stats += ': ' + c.status
				if c.last_status_time:
					stats += '\n' + _('since %s') % time.strftime('%c',
						c.last_status_time).decode(locale.getpreferredencoding())
				one = False
		else: # Maybe gc_vcard ?
			stats = helpers.get_uf_show(self.contact.show)
			if self.contact.status:
				stats += ': ' + self.contact.status
		status_label = self.xml.get_widget('status_label')
		status_label.set_max_width_chars(15)
		status_label.set_text(stats)

		tip = gtk.Tooltips()
		status_label_eventbox = self.xml.get_widget('status_label_eventbox')
		tip.set_tip(status_label_eventbox, stats)

	def fill_jabber_page(self):
		tooltips = gtk.Tooltips()
		self.xml.get_widget('nickname_label').set_markup(
			'<b><span size="x-large">' +
			self.contact.get_shown_name() +
			'</span></b>')
		self.xml.get_widget('jid_label').set_text(self.contact.jid)
		uf_sub = helpers.get_uf_sub(self.contact.sub)
		self.xml.get_widget('subscription_label').set_text(uf_sub)
		eb = self.xml.get_widget('subscription_label_eventbox')
		if self.contact.sub == 'from':
			tt_text = _("This contact is interested in your presence information, but you are not interested in his/her presence")
		elif self.contact.sub == 'to':
			tt_text = _("You are interested in the contact's presence information, but he/she is not interested in yours")
		elif self.contact.sub == 'both':
			tt_text = _("You and the contact are interested in each other's presence information")
		else: # None
			tt_text = _("You are not interested in the contact's presence, and neither he/she is interested in yours")
		tooltips.set_tip(eb, tt_text)

		label = self.xml.get_widget('ask_label')
		uf_ask = helpers.get_uf_ask(self.contact.ask)
		label.set_text(uf_ask)
		eb = self.xml.get_widget('ask_label_eventbox')
		if self.contact.ask == 'subscribe':
			tooltips.set_tip(eb,
			_("You are waiting contact's answer about your subscription request"))
		log = True
		if self.contact.jid in gajim.config.get_per('accounts', self.account,
			'no_log_for').split(' '):
			log = False
		checkbutton = self.xml.get_widget('log_history_checkbutton')
		checkbutton.set_active(log)
		checkbutton.connect('toggled', self.on_log_history_checkbutton_toggled)
		
		resources = '%s (%s)' % (self.contact.resource, unicode(
			self.contact.priority))
		uf_resources = self.contact.resource + _(' resource with priority ')\
			+ unicode(self.contact.priority)
		if not self.contact.status:
			self.contact.status = ''

		# Request list time status
		gajim.connections[self.account].request_last_status_time(self.contact.jid,
			self.contact.resource)

		# Request os info in contact is connected
		if self.contact.show not in ('offline', 'error'):
			gobject.idle_add(gajim.connections[self.account].request_os_info,
				self.contact.jid, self.contact.resource)
		self.os_info = {0: {'resource': self.contact.resource, 'client': '',
			'os': ''}}
		i = 1
		contact_list = gajim.contacts.get_contact(self.account, self.contact.jid)
		if contact_list:
			for c in contact_list:
				if c.resource != self.contact.resource:
					resources += '\n%s (%s)' % (c.resource,
						unicode(c.priority))
					uf_resources += '\n' + c.resource + \
						_(' resource with priority ') + unicode(c.priority)
					if c.show not in ('offline', 'error'):
						gobject.idle_add(
							gajim.connections[self.account].request_os_info, c.jid,
							c.resource)
					gajim.connections[self.account].request_last_status_time(c.jid,
						c.resource)
					self.os_info[i] = {'resource': c.resource, 'client': '',
						'os': ''}
					i += 1
		self.xml.get_widget('resource_prio_label').set_text(resources)
		resource_prio_label_eventbox = self.xml.get_widget(
			'resource_prio_label_eventbox')
		tooltips.set_tip(resource_prio_label_eventbox, uf_resources)

		self.fill_status_label()

		gajim.connections[self.account].request_vcard(self.contact.jid, self.is_fake)
