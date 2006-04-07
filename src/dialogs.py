# -*- coding: utf-8 -*-
##	dialogs.py
##
## Copyright (C) 2003-2006 Yann Le Boulanger <asterix@lagaule.org>
## Copyright (C) 2003-2004 Vincent Hanquez <tab@snarc.org>
## Copyright (C) 2005-2006 Nikos Kouremenos <nkour@jabber.org>
## Copyright (C) 2005 Dimitur Kirov <dkirov@gmail.com>
## Copyright (C) 2005-2006 Travis Shirk <travis@pobox.com>
## Copyright (C) 2005 Norman Rasmussen <norman@rasmussen.co.za>
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
import gtk.glade
import gobject
import os
import sys

import gtkgui_helpers
import vcard
import conversation_textview

try:
	import gtkspell
	HAS_GTK_SPELL = True
except:
	HAS_GTK_SPELL = False

# those imports are not used in this file, but in files that 'import dialogs'
# so they can do dialog.GajimThemesWindow() for example
from filetransfers_window import FileTransfersWindow
from gajim_themes_window import GajimThemesWindow
from advanced import AdvancedConfigurationWindow

from common import gajim
from common import helpers
from common import i18n

_ = i18n._
APP = i18n.APP
gtk.glade.bindtextdomain (APP, i18n.DIR)
gtk.glade.textdomain (APP)

GTKGUI_GLADE = 'gtkgui.glade'

class EditGroupsDialog:
	'''Class for the edit group dialog window'''
	def __init__(self, user, account):
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'edit_groups_dialog', APP)
		self.dialog = self.xml.get_widget('edit_groups_dialog')
		self.account = account
		self.user = user
		self.changes_made = False
		self.list = self.xml.get_widget('groups_treeview')
		self.xml.get_widget('nickname_label').set_markup(
			_("Contact's name: <i>%s</i>") % user.get_shown_name())
		self.xml.get_widget('jid_label').set_markup(
			_('JID: <i>%s</i>') % user.jid)
		
		self.xml.signal_autoconnect(self)
		self.init_list()

	def run(self):
		self.dialog.show_all()
		if self.changes_made:
			gajim.connections[self.account].update_contact(self.user.jid,
				self.user.name, self.user.groups)

	def on_edit_groups_dialog_response(self, widget, response_id):
		if response_id == gtk.RESPONSE_CLOSE:
			self.dialog.destroy()

	def update_contact(self):
		tag = gajim.contacts.get_metacontacts_tag(self.account, self.user.jid)
		if not tag:
			gajim.interface.roster.remove_contact(self.user, self.account)
			gajim.interface.roster.add_contact_to_roster(self.user.jid,
				self.account)
			gajim.connections[self.account].update_contact(self.user.jid,
				self.user.name, self.user.groups)
			return
		all_jid = gajim.contacts.get_metacontacts_jids(tag)
		for _account in all_jid:
			for _jid in all_jid[_account]:
				c = gajim.contacts.get_first_contact_from_jid(_account, _jid)
				if not c:
					continue
				gajim.interface.roster.remove_contact(c, _account)
				gajim.interface.roster.add_contact_to_roster(_jid, _account)
				gajim.connections[_account].update_contact(_jid, c.name, c.groups)

	def remove_group(self, group):
		'''add group group to self.user and all his brothers'''
		tag = gajim.contacts.get_metacontacts_tag(self.account, self.user.jid)
		if not tag:
			if group in self.user.groups:
				self.user.groups.remove(group)
			return
		all_jid = gajim.contacts.get_metacontacts_jids(tag)
		for _account in all_jid:
			for _jid in all_jid[_account]:
				contacts = gajim.contacts.get_contact(_account, _jid)
				for contact in contacts:
					if group in contact.groups:
						contact.groups.remove(group)

	def add_group(self, group):
		'''add group group to self.user and all his brothers'''
		tag = gajim.contacts.get_metacontacts_tag(self.account, self.user.jid)
		if not tag:
			if group not in self.user.groups:
				self.user.groups.append(group)
			return
		all_jid = gajim.contacts.get_metacontacts_jids(tag)
		for _account in all_jid:
			for _jid in all_jid[_account]:
				contacts = gajim.contacts.get_contact(_account, _jid)
				for contact in contacts:
					if not group in contact.groups:
						contact.groups.append(group)

	def on_add_button_clicked(self, widget):
		group = self.xml.get_widget('group_entry').get_text().decode('utf-8')
		if not group:
			return
		# check if it already exists
		model = self.list.get_model()
		iter = model.get_iter_root()
		while iter:
			if model.get_value(iter, 0).decode('utf-8') == group:
				return
			iter = model.iter_next(iter)
		self.changes_made = True
		model.append((group, True))
		self.add_group(group)
		self.update_contact()

	def group_toggled_cb(self, cell, path):
		self.changes_made = True
		model = self.list.get_model()
		model[path][1] = not model[path][1]
		group = model[path][0].decode('utf-8')
		if model[path][1]:
			self.add_group(group)
		else:
			self.remove_group(group)
		self.update_contact()

	def init_list(self):
		store = gtk.ListStore(str, bool)
		self.list.set_model(store)
		for g in gajim.groups[self.account].keys():
			if g in helpers.special_groups:
				continue
			iter = store.append()
			store.set(iter, 0, g)
			if g in self.user.groups:
				store.set(iter, 1, True)
			else:
				store.set(iter, 1, False)
		column = gtk.TreeViewColumn(_('Group'))
		column.set_expand(True)
		self.list.append_column(column)
		renderer = gtk.CellRendererText()
		column.pack_start(renderer)
		column.set_attributes(renderer, text = 0)
		
		column = gtk.TreeViewColumn(_('In the group'))
		column.set_expand(False)
		self.list.append_column(column)
		renderer = gtk.CellRendererToggle()
		column.pack_start(renderer)
		renderer.set_property('activatable', True)
		renderer.connect('toggled', self.group_toggled_cb)
		column.set_attributes(renderer, active = 1)

class PassphraseDialog:
	'''Class for Passphrase dialog'''
	def run(self):
		'''Wait for OK button to be pressed and return passphrase/password'''
		rep = self.window.run()
		if rep == gtk.RESPONSE_OK:
			passphrase = self.passphrase_entry.get_text().decode('utf-8')
		else:
			passphrase = -1
		save_passphrase_checkbutton = self.xml.\
			get_widget('save_passphrase_checkbutton')
		self.window.destroy()
		return passphrase, save_passphrase_checkbutton.get_active()

	def __init__(self, titletext, labeltext, checkbuttontext):
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'passphrase_dialog', APP)
		self.window = self.xml.get_widget('passphrase_dialog')
		self.passphrase_entry = self.xml.get_widget('passphrase_entry')
		self.passphrase = -1
		self.window.set_title(titletext)
		self.xml.get_widget('message_label').set_text(labeltext)
		self.xml.get_widget('save_passphrase_checkbutton').set_label(
			checkbuttontext)
		self.xml.signal_autoconnect(self)
		self.window.show_all()

class ChooseGPGKeyDialog:
	'''Class for GPG key dialog'''
	def __init__(self, title_text, prompt_text, secret_keys, selected = None):
		#list : {keyID: userName, ...}
		xml = gtk.glade.XML(GTKGUI_GLADE, 'choose_gpg_key_dialog', APP)
		self.window = xml.get_widget('choose_gpg_key_dialog')
		self.window.set_title(title_text)
		self.keys_treeview = xml.get_widget('keys_treeview')
		prompt_label = xml.get_widget('prompt_label')
		prompt_label.set_text(prompt_text)
		model = gtk.ListStore(str, str)
		model.set_sort_column_id(1, gtk.SORT_ASCENDING)
		self.keys_treeview.set_model(model)
		#columns
		renderer = gtk.CellRendererText()
		self.keys_treeview.insert_column_with_attributes(-1, _('KeyID'),
			renderer, text = 0)
		renderer = gtk.CellRendererText()
		self.keys_treeview.insert_column_with_attributes(-1, _('Contact name'),
			renderer, text = 1)
		self.fill_tree(secret_keys, selected)
		self.window.show_all()

	def run(self):
		rep = self.window.run()
		if rep == gtk.RESPONSE_OK:
			selection = self.keys_treeview.get_selection()
			(model, iter) = selection.get_selected()
			keyID = [ model[iter][0].decode('utf-8'),
				model[iter][1].decode('utf-8') ]
		else:
			keyID = None
		self.window.destroy()
		return keyID

	def fill_tree(self, list, selected):
		model = self.keys_treeview.get_model()
		for keyID in list.keys():
			iter = model.append((keyID, list[keyID]))
			if keyID == selected:
				path = model.get_path(iter)
				self.keys_treeview.set_cursor(path)


class ChangeStatusMessageDialog:
	def __init__(self, show = None):
		self.show = show
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'change_status_message_dialog',
			APP)
		self.window = self.xml.get_widget('change_status_message_dialog')
		if show:
			uf_show = helpers.get_uf_show(show)
			title_text = _('%s Status Message') % uf_show
		else:
			title_text = _('Status Message')
		self.window.set_title(title_text)
		
		message_textview = self.xml.get_widget('message_textview')
		self.message_buffer = message_textview.get_buffer()
		self.message_buffer.connect('changed',
			self.toggle_sensitiviy_of_save_as_preset)
		msg = None
		if show:
			msg = gajim.config.get('last_status_msg_' + show)
		if not msg:
			msg = ''
		msg = helpers.from_one_line(msg)
		self.message_buffer.set_text(msg)
		
		# have an empty string selectable, so user can clear msg
		self.preset_messages_dict = {'': ''}
		for msg_name in gajim.config.get_per('statusmsg'):
			msg_text = gajim.config.get_per('statusmsg', msg_name, 'message')
			msg_text = helpers.from_one_line(msg_text)
			self.preset_messages_dict[msg_name] = msg_text
		sorted_keys_list = helpers.get_sorted_keys(self.preset_messages_dict)
		
		self.message_liststore = gtk.ListStore(str) # msg_name
		self.message_combobox = self.xml.get_widget('message_combobox')
		self.message_combobox.set_model(self.message_liststore)
		cellrenderertext = gtk.CellRendererText()
		self.message_combobox.pack_start(cellrenderertext, True)
		self.message_combobox.add_attribute(cellrenderertext, 'text', 0)
		for msg_name in sorted_keys_list:
			self.message_liststore.append((msg_name,))
		self.xml.signal_autoconnect(self)
		self.window.show_all()

	def run(self):
		'''Wait for OK or Cancel button to be pressed and return status messsage
		(None if users pressed Cancel or x button of WM'''
		rep = self.window.run()
		if rep == gtk.RESPONSE_OK:
			beg, end = self.message_buffer.get_bounds()
			message = self.message_buffer.get_text(beg, end).decode('utf-8')\
				.strip()
			msg = helpers.to_one_line(message)
			if self.show:
				gajim.config.set('last_status_msg_' + self.show, msg)
		else:
			message = None # user pressed Cancel button or X wm button
		self.window.destroy()
		return message

	def on_message_combobox_changed(self, widget):
		model = widget.get_model()
		active = widget.get_active()
		if active < 0:
			return None
		name = model[active][0].decode('utf-8')
		self.message_buffer.set_text(self.preset_messages_dict[name])
	
	def on_change_status_message_dialog_key_press_event(self, widget, event):
		if event.keyval == gtk.keysyms.Return or \
		event.keyval == gtk.keysyms.KP_Enter:  # catch CTRL+ENTER
			if (event.state & gtk.gdk.CONTROL_MASK):
				self.window.response(gtk.RESPONSE_OK)

	def toggle_sensitiviy_of_save_as_preset(self, widget):
		btn = self.xml.get_widget('save_as_preset_button')
		if self.message_buffer.get_char_count() == 0:
			btn.set_sensitive(False)
		else:
			btn.set_sensitive(True)
	
	def on_save_as_preset_button_clicked(self, widget):
		start_iter, finish_iter = self.message_buffer.get_bounds()
		status_message_to_save_as_preset = self.message_buffer.get_text(
			start_iter, finish_iter)
		dlg = InputDialog(_('Save as Preset Status Message'),
			_('Please type a name for this status message'), is_modal = True)
		response = dlg.get_response()
		if response == gtk.RESPONSE_OK:
			msg_name = dlg.input_entry.get_text()
			msg_text = helpers.to_one_line(status_message_to_save_as_preset)
			if not msg_name: # msg_name was ''
				msg_name = msg_text
			iter_ = self.message_liststore.append((msg_name,))
			
			gajim.config.add_per('statusmsg', msg_name)
			gajim.config.set_per('statusmsg', msg_name, 'message', msg_text)
			self.preset_messages_dict[msg_name] = msg_text
			# select in combobox the one we just saved 
			self.message_combobox.set_active_iter(iter_)


class AddNewContactWindow:
	'''Class for AddNewContactWindow'''
	def __init__(self, account, jid = None):
		self.account = account
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'add_new_contact_window', APP)
		self.window = self.xml.get_widget('add_new_contact_window')
		self.uid_entry = self.xml.get_widget('uid_entry')
		self.protocol_combobox = self.xml.get_widget('protocol_combobox')
		self.jid_entry = self.xml.get_widget('jid_entry')
		self.nickname_entry = self.xml.get_widget('nickname_entry')
		if len(gajim.connections) >= 2:
			prompt_text =\
_('Please fill in the data of the contact you want to add in account %s') %account
		else:
			prompt_text = _('Please fill in the data of the contact you want to add')
		self.xml.get_widget('prompt_label').set_text(prompt_text)
		self.old_uid_value = ''
		liststore = gtk.ListStore(str, str)
		liststore.append(['Jabber', ''])
		self.agents = ['Jabber']
		jid_agents = []
		for j in gajim.contacts.get_jid_list(account):
			contact = gajim.contacts.get_first_contact_from_jid(account, j)
			if _('Transports') in contact.groups and contact.show != 'offline' and\
					contact.show != 'error':
				jid_agents.append(j)
		for a in jid_agents:
			if a.find('aim') > -1:
				name = 'AIM'
			elif a.find('icq') > -1:
				name = 'ICQ'
			elif a.find('msn') > -1:
				name = 'MSN'
			elif a.find('yahoo') > -1:
				name = 'Yahoo!'
			else:
				name = a
			iter = liststore.append([name, a])
			self.agents.append(name)
		
		self.protocol_combobox.set_model(liststore)
		self.protocol_combobox.set_active(0)
		self.fill_jid()
		if jid:
			self.jid_entry.set_text(jid)
			self.uid_entry.set_sensitive(False)
			jid_splited = jid.split('@')
			if jid_splited[1] in jid_agents:
				uid = jid_splited[0].replace('%', '@')
				self.uid_entry.set_text(uid)
				self.protocol_combobox.set_active(jid_agents.index(jid_splited[1])\
					+ 1)
			else:
				self.uid_entry.set_text(jid)
				self.protocol_combobox.set_active(0)
			self.set_nickname()
			self.nickname_entry.grab_focus()

		self.group_comboboxentry = self.xml.get_widget('group_comboboxentry')
		liststore = gtk.ListStore(str)
		self.group_comboboxentry.set_model(liststore)
		for g in gajim.groups[account].keys():
			if g not in helpers.special_groups:
				self.group_comboboxentry.append_text(g)

		if not jid_agents:
			# There are no transports, so hide the protocol combobox and label
			self.protocol_combobox.hide()
			self.protocol_combobox.set_no_show_all(True)
			protocol_label = self.xml.get_widget('protocol_label')
			protocol_label.hide()
			protocol_label.set_no_show_all(True)

		self.xml.signal_autoconnect(self)
		self.window.show_all()

	def on_add_new_contact_window_key_press_event(self, widget, event):
		if event.keyval == gtk.keysyms.Escape: # ESCAPE
			self.window.destroy()

	def on_cancel_button_clicked(self, widget):
		'''When Cancel button is clicked'''
		self.window.destroy()

	def on_subscribe_button_clicked(self, widget):
		'''When Subscribe button is clicked'''
		jid = self.jid_entry.get_text().decode('utf-8')
		nickname = self.nickname_entry.get_text().decode('utf-8')
		if not jid:
			return
	
		# check if jid is conform to RFC and stringprep it
		try:
			jid = helpers.parse_jid(jid)
		except helpers.InvalidFormat, s:
			pritext = _('Invalid User ID')
			ErrorDialog(pritext, str(s))
			return

		# No resource in jid
		if jid.find('/') >= 0:
			pritext = _('Invalid User ID')
			ErrorDialog(pritext, _('The user ID must not contain a resource.'))
			return

		# Check if jid is already in roster
		if jid in gajim.contacts.get_jid_list(self.account):
			c = gajim.contacts.get_first_contact_from_jid(self.account, jid)
			if _('Not in Roster') not in c.groups and c.sub in ('both', 'to'):
				ErrorDialog(_('Contact already in roster'),
				_('This contact is already listed in your roster.'))
				return

		message_buffer = self.xml.get_widget('message_textview').get_buffer()
		start_iter = message_buffer.get_start_iter()
		end_iter = message_buffer.get_end_iter()
		message = message_buffer.get_text(start_iter, end_iter).decode('utf-8')
		group = self.group_comboboxentry.child.get_text().decode('utf-8')
		auto_auth = self.xml.get_widget('auto_authorize_checkbutton').get_active()
		gajim.interface.roster.req_sub(self, jid, message, self.account,
			group = group, pseudo = nickname, auto_auth = auto_auth)
		self.window.destroy()
		
	def fill_jid(self):
		model = self.protocol_combobox.get_model()
		index = self.protocol_combobox.get_active()
		jid = self.uid_entry.get_text().decode('utf-8').strip()
		if index > 0: # it's not jabber but a transport
			jid = jid.replace('@', '%')
		agent = model[index][1].decode('utf-8')
		if agent:
			jid += '@' + agent
		self.jid_entry.set_text(jid)

	def on_protocol_combobox_changed(self, widget):
		self.fill_jid()

	def guess_agent(self):
		uid = self.uid_entry.get_text().decode('utf-8')
		model = self.protocol_combobox.get_model()
		
		#If login contains only numbers, it's probably an ICQ number
		if uid.isdigit():
			if 'ICQ' in self.agents:
				self.protocol_combobox.set_active(self.agents.index('ICQ'))
				return

	def set_nickname(self):
		uid = self.uid_entry.get_text().decode('utf-8')
		nickname = self.nickname_entry.get_text().decode('utf-8')
		if nickname == self.old_uid_value:
			self.nickname_entry.set_text(uid.split('@')[0])
			
	def on_uid_entry_changed(self, widget):
		uid = self.uid_entry.get_text().decode('utf-8')
		self.guess_agent()
		self.set_nickname()
		self.fill_jid()
		self.old_uid_value = uid.split('@')[0]

class AboutDialog:
	'''Class for about dialog'''
	def __init__(self):
		dlg = gtk.AboutDialog()
		dlg.set_name('Gajim')
		dlg.set_version(gajim.version)
		s = u'Copyright © 2003-2006 Gajim Team'
		dlg.set_copyright(s)
		text = open('../COPYING').read()
		dlg.set_license(text)

		dlg.set_comments(_('A GTK+ jabber client'))
		dlg.set_website('http://www.gajim.org')

		authors = [
			'Current Developers:',
			'Yann Le Boulanger <asterix@lagaule.org>',
			'Nikos Kouremenos <kourem@gmail.com>',
			'Dimitur Kirov <dkirov@gmail.com>',
			'Travis Shirk <travis@pobox.com>',
			'',
			_('Past Developers:'),
			'Vincent Hanquez <tab@snarc.org>',
			'',
			_('THANKS:'),
		]

		text = open('../THANKS').read()
		text_splitted = text.split('\n')
		text = '\n'.join(text_splitted[:-2]) # remove one english setence
		# and add it manually as translatable
		text += '\n%s\n' % _('Last but not least, we would like to thank all '
			'the package maintainers.')
		authors.append(text)
		
		dlg.set_authors(authors)
		
		if gtk.pygtk_version >= (2, 8, 0) and gtk.gtk_version >= (2, 8, 0):
			dlg.props.wrap_license = True

		pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(
			gajim.DATA_DIR, 'pixmaps', 'gajim_about.png'))			

		dlg.set_logo(pixbuf)
		#here you write your name in the form Name FamilyName <someone@somewhere>
		dlg.set_translator_credits(_('translator-credits'))
		
		artists = ['Anders Ström', 'Christophe Got', 'Dennis Craven',
			'Guillaume Morin', 'Membris Khan']
		dlg.set_artists(artists)

		rep = dlg.run()
		dlg.destroy()

class Dialog(gtk.Dialog):
	def __init__(self, parent, title, buttons, default = None):
		gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL | gtk.DIALOG_NO_SEPARATOR)

		self.set_border_width(6)
		self.vbox.set_spacing(12)
		self.set_resizable(False)

		for stock, response in buttons:
			self.add_button(stock, response)

		if default is not None:
			self.set_default_response(default)
		else:
			self.set_default_response(buttons[-1][1])

	def get_button(self, index):
		buttons = self.action_area.get_children()
		return index < len(buttons) and buttons[index] or None


class HigDialog(gtk.MessageDialog):
	def __init__(self, parent, type, buttons, pritext, sectext,
	on_response_ok = None, on_response_cancel = None, on_response_yes = None,
	on_response_no = None):
		gtk.MessageDialog.__init__(self, parent, 
				gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL,
				type, buttons, message_format = pritext)

		self.format_secondary_text(sectext)

		buttons = self.action_area.get_children()
		possible_responses = {gtk.STOCK_OK: on_response_ok,
			gtk.STOCK_CANCEL: on_response_cancel, gtk.STOCK_YES: on_response_yes,
			gtk.STOCK_NO: on_response_no}
		for b in buttons:
			for response in possible_responses:
				if b.get_label() == response:
					if not possible_responses[response]:
						b.connect('clicked', self.just_destroy)
					elif isinstance(possible_responses[response], tuple):
						if len(possible_response[response]) == 1:
							b.connect('clicked', possible_responses[response][0])
						else:
							b.connect('clicked', *possible_responses[response])
					else:
						b.connect('clicked', possible_responses[response])
					break
	
	def just_destroy(self, widget):
		self.destroy()

	def popup(self):
		'''show dialog'''
		vb = self.get_children()[0].get_children()[0] # Give focus to top vbox
		vb.set_flags(gtk.CAN_FOCUS)
		vb.grab_focus()
		self.show_all()

	def get_response(self):
		'''Be carefull: this function uses dialog.run() function so GUI is not updated'''
		# Give focus to top vbox
		vb = self.get_children()[0].get_children()[0]
		vb.set_flags(gtk.CAN_FOCUS)
		vb.grab_focus()
		self.show_all()
		response = self.run()
		self.destroy()
		return response


class FileChooserDialog(gtk.FileChooserDialog):
	'''Non-blocking FileChooser Dialog around gtk.FileChooserDialog'''
	def __init__(self, title_text, action, buttons, default_response,
	select_multiple, current_folder, on_response_ok = None,
	on_response_cancel = None):

		gtk.FileChooserDialog.__init__(self, title=title_text, 
			action=action, buttons=buttons)
		
		self.set_default_response(default_response)
		self.set_select_multiple(select_multiple)
		if current_folder and os.path.isdir(current_folder):
			self.set_current_folder(current_folder)
		else:
			self.set_current_folder(helpers.get_documents_path())
		
		self.show_all()
	

class ConfirmationDialog(HigDialog):
	'''HIG compliant confirmation dialog.'''
	def __init__(self, pritext, sectext='', on_response_ok = None,
	on_response_cancel = None):
		HigDialog.__init__(self, None, 
			gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, pritext, sectext,
			on_response_ok, on_response_cancel)
		self.popup()

class WarningDialog(HigDialog):
	def __init__(self, pritext, sectext=''):
		'''HIG compliant warning dialog.'''
		HigDialog.__init__( self, None, 
			gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, pritext, sectext)
		self.popup()

class InformationDialog(HigDialog):
	def __init__(self, pritext, sectext=''):
		'''HIG compliant info dialog.'''
		HigDialog.__init__( self, None, 
			gtk.MESSAGE_INFO, gtk.BUTTONS_OK, pritext, sectext)
		self.popup()

class ErrorDialog(HigDialog):
	def __init__(self, pritext, sectext=''):
		'''HIG compliant error dialog.'''
		HigDialog.__init__( self, None, 
			gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, pritext, sectext)
		self.popup()

class YesNoDialog(HigDialog):
	def __init__(self, pritext, sectext='', on_response_yes = None,
	on_response_no = None):
		'''HIG compliant YesNo dialog.'''
		HigDialog.__init__( self, None, 
			gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, pritext, sectext,
				on_response_yes = on_response_yes, on_response_no = on_response_no)
		self.popup()

class ConfirmationDialogCheck(ConfirmationDialog):
	'''HIG compliant confirmation dialog with checkbutton.'''
	def __init__(self, pritext, sectext='', checktext = '',
	on_response_ok = None, on_response_cancel = None):
		HigDialog.__init__(self, None, gtk.MESSAGE_QUESTION,
			gtk.BUTTONS_OK_CANCEL, pritext, sectext, on_response_ok,
			on_response_cancel)

		self.set_default_response(gtk.RESPONSE_OK)

		ok_button = self.action_area.get_children()[0] # right to left
		ok_button.grab_focus()

		self.checkbutton = gtk.CheckButton(checktext)
		self.vbox.pack_start(self.checkbutton, expand = False, fill = True)
		self.popup()

	def is_checked(self):
		''' Get active state of the checkbutton '''
		return self.checkbutton.get_active()

class FTOverwriteConfirmationDialog(ConfirmationDialog):
	'''HIG compliant confirmation dialog to overwrite or resume a file transfert'''
	def __init__(self, pritext, sectext='', propose_resume=True):
		HigDialog.__init__(self, None, gtk.MESSAGE_QUESTION, gtk.BUTTONS_CANCEL,
			pritext, sectext)

		if propose_resume:
			b = gtk.Button('', gtk.STOCK_REFRESH)
			align = b.get_children()[0]
			hbox = align.get_children()[0]
			label = hbox.get_children()[1]
			label.set_text('_Resume')
			label.set_use_underline(True)
			self.add_action_widget(b, 100)

		b = gtk.Button('', gtk.STOCK_SAVE_AS)
		align = b.get_children()[0]
		hbox = align.get_children()[0]
		label = hbox.get_children()[1]
		label.set_text('Re_place')
		label.set_use_underline(True)
		self.add_action_widget(b, 200)

class InputDialog:
	'''Class for Input dialog'''
	def __init__(self, title, label_str, input_str = None, is_modal = True,
ok_handler = None):
		# if modal is True you also need to call get_response()
		# and ok_handler won't be used
		xml = gtk.glade.XML(GTKGUI_GLADE, 'input_dialog', APP)
		self.dialog = xml.get_widget('input_dialog')
		label = xml.get_widget('label')
		self.input_entry = xml.get_widget('input_entry')
		self.dialog.set_title(title)
		label.set_markup(label_str)
		if input_str:
			self.input_entry.set_text(input_str)
			self.input_entry.select_region(0, -1) # select all
		
		self.is_modal = is_modal
		if not is_modal and ok_handler is not None:
			self.ok_handler = ok_handler
			okbutton = xml.get_widget('okbutton')
			okbutton.connect('clicked', self.on_okbutton_clicked)
			cancelbutton = xml.get_widget('cancelbutton')
			cancelbutton.connect('clicked', self.on_cancelbutton_clicked)
			self.dialog.show_all()

	def on_okbutton_clicked(self,  widget):
		user_input = self.input_entry.get_text().decode('utf-8')
		self.dialog.destroy()
		self.ok_handler(user_input)
	
	def on_cancelbutton_clicked(self,  widget):
		self.dialog.destroy()

	def get_response(self):
		if self.is_modal:
			response = self.dialog.run()
			self.dialog.destroy()
		return response

class SubscriptionRequestWindow:
	def __init__(self, jid, text, account):
		xml = gtk.glade.XML(GTKGUI_GLADE, 'subscription_request_window', APP)
		self.window = xml.get_widget('subscription_request_window')
		self.jid = jid
		self.account = account
		if len(gajim.connections) >= 2:
			prompt_text = _('Subscription request for account %s from %s')\
				% (account, self.jid)
		else:
			prompt_text = _('Subscription request from %s') % self.jid
		xml.get_widget('from_label').set_text(prompt_text)
		xml.get_widget('message_textview').get_buffer().set_text(text)
		xml.signal_autoconnect(self)
		self.window.show_all()

	def on_close_button_clicked(self, widget):
		self.window.destroy()
		
	def on_authorize_button_clicked(self, widget):
		'''accept the request'''
		gajim.connections[self.account].send_authorization(self.jid)
		self.window.destroy()
		if self.jid not in gajim.contacts.get_jid_list(self.account):
			AddNewContactWindow(self.account, self.jid)

	def on_contact_info_button_clicked(self, widget):
		'''ask vcard'''
		if gajim.interface.instances[self.account]['infos'].has_key(self.jid):
			gajim.interface.instances[self.account]['infos'][self.jid].window.present()
		else:
			contact = gajim.contacts.create_contact(jid = self.jid, name='',
			groups=[], show='', status='', sub='', ask='', resource='',
			priority=5, keyID='', our_chatstate=None, chatstate=None)
			gajim.interface.instances[self.account]['infos'][self.jid] = \
				vcard.VcardWindow(contact, self.account)
			# Remove jabber page
			gajim.interface.instances[self.account]['infos'][self.jid].xml.\
				get_widget('information_notebook').remove_page(0)
			gajim.connections[self.account].request_vcard(self.jid)
	
	def on_deny_button_clicked(self, widget):
		'''refuse the request'''
		gajim.connections[self.account].refuse_authorization(self.jid)
		self.window.destroy()

class JoinGroupchatWindow:
	def __init__(self, account, server = '', room = '', nick = ''):
		self.account = account
		if nick == '':
			nick = gajim.nicks[self.account]
		if gajim.connections[account].connected < 2:
			ErrorDialog(_('You are not connected to the server'),
_('You can not join a group chat unless you are connected.'))
			raise RuntimeError, 'You must be connected to join a groupchat'

		self._empty_required_widgets = []

		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'join_groupchat_window', APP)
		self.window = self.xml.get_widget('join_groupchat_window')
		self.xml.get_widget('server_entry').set_text(server)
		self.xml.get_widget('room_entry').set_text(room)
		self.xml.get_widget('nickname_entry').set_text(nick)
		self.xml.signal_autoconnect(self)
		gajim.interface.instances[account]['join_gc'] = self #now add us to open windows
		if len(gajim.connections) > 1:
			title = _('Join Group Chat with account %s') % account
		else:
			title = _('Join Group Chat')
		self.window.set_title(title)

		self.recently_combobox = self.xml.get_widget('recently_combobox')
		liststore = gtk.ListStore(str)
		self.recently_combobox.set_model(liststore)
		cell = gtk.CellRendererText()
		self.recently_combobox.pack_start(cell, True)
		self.recently_combobox.add_attribute(cell, 'text', 0)
		self.recently_groupchat = gajim.config.get('recently_groupchat').split()
		for g in self.recently_groupchat:
			self.recently_combobox.append_text(g)
		if len(self.recently_groupchat) == 0:
			self.recently_combobox.set_sensitive(False)
		elif server == '' and room == '':
			self.recently_combobox.set_active(0)
			self.xml.get_widget('room_entry').select_region(0, -1)
		elif room and server:
			self.xml.get_widget('join_button').grab_focus()

		self._server_entry = self.xml.get_widget('server_entry')
		self._room_entry = self.xml.get_widget('room_entry')
		self._nickname_entry = self.xml.get_widget('nickname_entry')
		if not self._server_entry.get_text():
			self._empty_required_widgets.append(self._server_entry)
		if not self._room_entry.get_text():
			self._empty_required_widgets.append(self._room_entry)
		if not self._nickname_entry.get_text():
			self._empty_required_widgets.append(self._nickname_entry)
		if len(self._empty_required_widgets):
			self.xml.get_widget('join_button').set_sensitive(False)

		self.window.show_all()

	def on_join_groupchat_window_destroy(self, widget):
		'''close window'''
		# remove us from open windows
		del gajim.interface.instances[self.account]['join_gc']

	def on_join_groupchat_window_key_press_event(self, widget, event):
		if event.keyval == gtk.keysyms.Escape: # ESCAPE
			widget.destroy()

	def on_required_entry_changed(self, widget):
		if not widget.get_text():
			self._empty_required_widgets.append(widget)
			self.xml.get_widget('join_button').set_sensitive(False)
		else:
			if widget in self._empty_required_widgets:
				self._empty_required_widgets.remove(widget)
				if len(self._empty_required_widgets) == 0:
					self.xml.get_widget('join_button').set_sensitive(True)

	def on_room_entry_key_press_event(self, widget, event):
		# Check for pressed @ and jump to server_entry if found
		if event.keyval == gtk.keysyms.at:
			self.xml.get_widget('server_entry').grab_focus()
			return True

	def on_server_entry_key_press_event(self, widget, event):
		# If backspace is pressed in empty server_entry, return to the room entry
		backspace = event.keyval == gtk.keysyms.BackSpace
		server_entry = self.xml.get_widget('server_entry')
		empty = len(server_entry.get_text()) == 0
		if backspace and empty:
			self.xml.get_widget('room_entry').grab_focus()
			return True

	def on_recently_combobox_changed(self, widget):
		model = widget.get_model()
		iter = widget.get_active_iter()
		gid = model[iter][0].decode('utf-8')
		self.xml.get_widget('room_entry').set_text(gid.split('@')[0])
		self.xml.get_widget('server_entry').set_text(gid.split('@')[1])

	def on_cancel_button_clicked(self, widget):
		'''When Cancel button is clicked'''
		self.window.destroy()

	def on_join_button_clicked(self, widget):
		'''When Join button is clicked'''
		nickname = self.xml.get_widget('nickname_entry').get_text().decode('utf-8')
		room = self.xml.get_widget('room_entry').get_text().decode('utf-8')
		server = self.xml.get_widget('server_entry').get_text().decode('utf-8')
		password = self.xml.get_widget('password_entry').get_text().decode('utf-8')
		jid = '%s@%s' % (room, server)
		try:
			jid = helpers.parse_jid(jid)
		except:
			ErrorDialog(_('Invalid room or server name'),
				_('The room name or server name has not allowed characters.'))
			return

		if jid in self.recently_groupchat:
			self.recently_groupchat.remove(jid)
		self.recently_groupchat.insert(0, jid)
		if len(self.recently_groupchat) > 10:
			self.recently_groupchat = self.recently_groupchat[0:10]
		gajim.config.set('recently_groupchat', ' '.join(self.recently_groupchat))
		
		gajim.interface.roster.join_gc_room(self.account, jid, nickname, password)

		self.window.destroy()

class NewMessageDialog:
	def __init__(self, account):
		self.account = account
		
		if len(gajim.connections) > 1:
			title = _('Start Chat with account %s') % account
		else:
			title = _('Start Chat')
		prompt_text = _('Fill in the contact ID of the contact you would like\nto send a chat message to:')

		InputDialog(title, prompt_text, is_modal = False, ok_handler = self.new_message_response)
			
	def new_message_response(self, jid):
		''' called when ok button is clicked '''
		if gajim.connections[self.account].connected <= 1:
			#if offline or connecting
			ErrorDialog(_('Connection not available'),
		_('Please make sure you are connected with "%s".' % self.account))
			return

		gajim.interface.roster.new_chat_from_jid(self.account, jid)

class ChangePasswordDialog:
	def __init__(self, account):
		# 'account' can be None if we are about to create our first one
		if not account or gajim.connections[account].connected < 2:
			ErrorDialog(_('You are not connected to the server'),
				_('Without a connection, you can not change your password.'))
			raise RuntimeError, 'You are not connected to the server'
		self.account = account
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'change_password_dialog', APP)
		self.dialog = self.xml.get_widget('change_password_dialog')
		self.password1_entry = self.xml.get_widget('password1_entry')
		self.password2_entry = self.xml.get_widget('password2_entry')

		self.dialog.show_all()

	def run(self):
		'''Wait for OK button to be pressed and return new password'''
		end = False
		while not end:
			rep = self.dialog.run()
			if rep == gtk.RESPONSE_OK:
				password1 = self.password1_entry.get_text().decode('utf-8')
				if not password1:
					ErrorDialog(_('Invalid password'),
							_('You must enter a password.'))
					continue
				password2 = self.password2_entry.get_text().decode('utf-8')
				if password1 != password2:
					ErrorDialog(_('Passwords do not match'),
							_('The passwords typed in both fields must be identical.'))
					continue
				message = password1
			else:
				message = -1
			end = True
		self.dialog.destroy()
		return message


class PopupNotificationWindow:
	def __init__(self, event_type, jid, account, msg_type = '',
	path_to_image = None, title = None, text = None):
		self.account = account
		self.jid = jid
		self.msg_type = msg_type

		xml = gtk.glade.XML(GTKGUI_GLADE, 'popup_notification_window', APP)
		self.window = xml.get_widget('popup_notification_window')
		close_button = xml.get_widget('close_button')
		event_type_label = xml.get_widget('event_type_label')
		event_description_label = xml.get_widget('event_description_label')
		eventbox = xml.get_widget('eventbox')
		image = xml.get_widget('notification_image')

		if not text:
			text = gajim.get_name_from_jid(account, jid) # default value of text
		if not title:
			title = event_type

		event_type_label.set_markup(
			'<span foreground="black" weight="bold">%s</span>' % title)

		# set colors [ http://www.pitt.edu/~nisg/cis/web/cgi/rgb.html ]
		self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))

		# default image
		if not path_to_image:
			path_to_image = os.path.abspath(
				os.path.join(gajim.DATA_DIR, 'pixmaps', 'events', 'chat_msg_recv.png')) # img to display

		if event_type == _('Contact Signed In'):
			bg_color = 'limegreen'
		elif event_type == _('Contact Signed Out'):
			bg_color = 'red'
		elif event_type in (_('New Message'), _('New Single Message'),
			_('New Private Message'), _('New E-mail')):
			bg_color = 'dodgerblue'
		elif event_type == _('File Transfer Request'):
			bg_color = 'khaki'
		elif event_type == _('File Transfer Error'):
			bg_color = 'firebrick'
		elif event_type in (_('File Transfer Completed'),
			_('File Transfer Stopped')):
			bg_color = 'yellowgreen'
		elif event_type == _('Groupchat Invitation'):
			bg_color = 'tan1'
		else: # Unknown event ! Shouldn't happen but deal with it
			bg_color = 'white'
		popup_bg_color = gtk.gdk.color_parse(bg_color)
		close_button.modify_bg(gtk.STATE_NORMAL, popup_bg_color)
		eventbox.modify_bg(gtk.STATE_NORMAL, popup_bg_color)
		event_description_label.set_markup(
			'<span foreground="black">%s</span>' % text)	
			
		# set the image
		image.set_from_file(path_to_image)
		
		# position the window to bottom-right of screen
		window_width, self.window_height = self.window.get_size()
		gajim.interface.roster.popups_notification_height += self.window_height
		pos_x = gajim.config.get('notification_position_x')
		if pos_x < 0:
			pos_x = gtk.gdk.screen_width() - window_width + pos_x + 1
		pos_y = gajim.config.get('notification_position_y')
		if pos_y < 0:
			pos_y = gtk.gdk.screen_height() - gajim.interface.roster.popups_notification_height + pos_y + 1
		self.window.move(pos_x, pos_y)

		xml.signal_autoconnect(self)
		self.window.show_all()
		timeout = gajim.config.get('notification_timeout') * 1000 # make it ms
		gobject.timeout_add(timeout, self.on_timeout)

	def on_close_button_clicked(self, widget):
		self.adjust_height_and_move_popup_notification_windows()

	def on_timeout(self):
		self.adjust_height_and_move_popup_notification_windows()

	def adjust_height_and_move_popup_notification_windows(self):
		#remove
		gajim.interface.roster.popups_notification_height -= self.window_height
		self.window.destroy()

		if len(gajim.interface.roster.popup_notification_windows) > 0:
			# we want to remove the first window added in the list
			gajim.interface.roster.popup_notification_windows.pop(0) # remove 1st item
		
		# move the rest of popup windows
		gajim.interface.roster.popups_notification_height = 0
		for window_instance in gajim.interface.roster.popup_notification_windows:
			window_width, window_height = window_instance.window.get_size()
			gajim.interface.roster.popups_notification_height += window_height
			window_instance.window.move(gtk.gdk.screen_width() - window_width,
		gtk.gdk.screen_height() - gajim.interface.roster.popups_notification_height)

	def on_popup_notification_window_button_press_event(self, widget, event):
		if event.button != 1:
			self.window.destroy()
			return
		gajim.interface.handle_event(self.account, self.jid, self.msg_type)
		self.adjust_height_and_move_popup_notification_windows()

class SingleMessageWindow:
	'''SingleMessageWindow can send or show a received
	singled message depending on action argument which can be 'send'
	or 'receive'.
	'''
	def __init__(self, account, to = '', action = '', from_whom = '',
	subject = '', message = '', resource = ''):
		self.account = account
		self.action = action

		self.subject = subject
		self.message = message
		self.to = to
		self.from_whom = from_whom
		self.resource = resource
		
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'single_message_window', APP)
		self.window = self.xml.get_widget('single_message_window')
		self.count_chars_label = self.xml.get_widget('count_chars_label')
		self.from_label = self.xml.get_widget('from_label')
		self.from_entry = self.xml.get_widget('from_entry')
		self.to_label = self.xml.get_widget('to_label')
		self.to_entry = self.xml.get_widget('to_entry')
		self.subject_entry = self.xml.get_widget('subject_entry')
		self.message_scrolledwindow = self.xml.get_widget(
			'message_scrolledwindow')
		self.message_textview = self.xml.get_widget('message_textview')
		self.message_tv_buffer = self.message_textview.get_buffer()
		self.conversation_scrolledwindow = self.xml.get_widget(
			'conversation_scrolledwindow')
		self.conversation_textview = conversation_textview.ConversationTextview(
			account)
		self.conversation_textview.show()
		self.conversation_tv_buffer = self.conversation_textview.get_buffer()
		self.xml.get_widget('conversation_scrolledwindow').add(
			self.conversation_textview)
		self.send_button = self.xml.get_widget('send_button')
		self.reply_button = self.xml.get_widget('reply_button')
		self.send_and_close_button = self.xml.get_widget('send_and_close_button')
		self.cancel_button = self.xml.get_widget('cancel_button')
		self.close_button = self.xml.get_widget('close_button')
		self.message_tv_buffer.connect('changed', self.update_char_counter)
		
		self.to_entry.set_text(to)
		
		if gajim.config.get('use_speller') and HAS_GTK_SPELL:
			try:
				gtkspell.Spell(self.conversation_textview)
				gtkspell.Spell(self.message_textview)
			except gobject.GError, msg:
				#FIXME: add a ui for this use spell.set_language()
				ErrorDialog(unicode(msg), _('If that is not your language for which you want to highlight misspelled words, then please set your $LANG as appropriate. Eg. for French do export LANG=fr_FR or export LANG=fr_FR.UTF-8 in ~/.bash_profile or to make it global in /etc/profile.\n\nHighlighting misspelled words feature will not be used'))
				gajim.config.set('use_speller', False)
		
		self.send_button.set_no_show_all(True)
		self.reply_button.set_no_show_all(True)
		self.send_and_close_button.set_no_show_all(True)
		self.to_label.set_no_show_all(True)
		self.to_entry.set_no_show_all(True)
		self.from_label.set_no_show_all(True)
		self.from_entry.set_no_show_all(True)
		self.close_button.set_no_show_all(True)
		self.cancel_button.set_no_show_all(True)
		self.message_scrolledwindow.set_no_show_all(True)
		self.conversation_scrolledwindow.set_no_show_all(True)
		
		self.prepare_widgets_for(self.action)

		# set_text(None) raises TypeError exception
		if self.subject is None:
			self.subject = ''
		self.subject_entry.set_text(self.subject)

		self.xml.signal_autoconnect(self)

		if gajim.config.get('saveposition'):
			# get window position and size from config
			gtkgui_helpers.move_window(self.window,
				gajim.config.get('single-msg-x-position'),
				gajim.config.get('single-msg-y-position'))
			gtkgui_helpers.resize_window(self.window,
				gajim.config.get('single-msg-width'),
				gajim.config.get('single-msg-height'))
		self.window.show_all()

	def set_cursor_to_end(self):
			end_iter = self.message_tv_buffer.get_end_iter()
			self.message_tv_buffer.place_cursor(end_iter)

	def save_pos(self):
		if gajim.config.get('saveposition'):
			# save the window size and position
			x, y = self.window.get_position()
			gajim.config.set('single-msg-x-position', x)
			gajim.config.set('single-msg-y-position', y)
			width, height = self.window.get_size()
			gajim.config.set('single-msg-width', width)
			gajim.config.set('single-msg-height', height)
			gajim.interface.save_config()

	def on_single_message_window_delete_event(self, window, ev):
		self.save_pos()

	def prepare_widgets_for(self, action):
		if len(gajim.connections) > 1:
			#FIXME: for Received with should become 'in'
			title = _('Single Message with account %s') % self.account
		else:
			title = _('Single Message')

		if action == 'send': # prepare UI for Sending
			title = _('Send %s') % title
			self.send_button.show()
			self.send_and_close_button.show()
			self.to_label.show()
			self.to_entry.show()
			self.reply_button.hide()
			self.from_label.hide()
			self.from_entry.hide()
			self.conversation_scrolledwindow.hide()
			self.message_scrolledwindow.show()
			
			if self.message: # we come from a reply?
				self.message_textview.grab_focus()
				self.cancel_button.hide()
				self.close_button.show()
				self.message_tv_buffer.set_text(self.message)
				gobject.idle_add(self.set_cursor_to_end)
			else: # we write a new message (not from reply)
				self.close_button.hide()
				if self.to: # do we already have jid?
					self.subject_entry.grab_focus()
			
		elif action == 'receive': # prepare UI for Receiving
			title = _('Received %s') % title
			self.reply_button.show()
			self.from_label.show()
			self.from_entry.show()
			self.send_button.hide()
			self.send_and_close_button.hide()
			self.to_label.hide()
			self.to_entry.hide()
			self.conversation_scrolledwindow.show()
			self.message_scrolledwindow.hide()

			if self.message:
				self.conversation_textview.print_real_text(self.message)
			fjid = self.from_whom 
			if self.resource:
				fjid += '/' + self.resource # Full jid of sender (with resource)
			self.from_entry.set_text(fjid)
			self.from_entry.set_property('editable', False)
			self.subject_entry.set_property('editable', False)
			self.reply_button.grab_focus()
			self.cancel_button.hide()
			self.close_button.show()
		
		self.window.set_title(title)

	def on_cancel_button_clicked(self, widget):
		self.save_pos()
		self.window.destroy()

	def on_close_button_clicked(self, widget):
		self.save_pos()
		self.window.destroy()

	def update_char_counter(self, widget):
		characters_no = self.message_tv_buffer.get_char_count()
		self.count_chars_label.set_text(unicode(characters_no))
	
	def send_single_message(self):
		if gajim.connections[self.account].connected <= 1:
			# if offline or connecting
			ErrorDialog(_('Connection not available'),
		_('Please make sure you are connected with "%s".' % self.account))
			return
		to_whom_jid = self.to_entry.get_text().decode('utf-8')
		subject = self.subject_entry.get_text().decode('utf-8')
		begin, end = self.message_tv_buffer.get_bounds()
		message = self.message_tv_buffer.get_text(begin, end).decode('utf-8')

		if to_whom_jid.find('/announce/') != -1:
			gajim.connections[self.account].send_motd(to_whom_jid, subject,
				message)
			return

		# FIXME: allow GPG message some day
		gajim.connections[self.account].send_message(to_whom_jid, message,
			keyID = None, type = 'normal', subject=subject)
		
		self.subject_entry.set_text('') # we sent ok, clear the subject
		self.message_tv_buffer.set_text('') # we sent ok, clear the textview

	def on_send_button_clicked(self, widget):
		self.send_single_message()

	def on_reply_button_clicked(self, widget):
		# we create a new blank window to send and we preset RE: and to jid
		self.subject = _('RE: %s') % self.subject
		self.message = _('%s wrote:\n' % self.from_whom) + self.message
		# add > at the begining of each line
		self.message = self.message.replace('\n', '\n> ') + '\n\n'
		self.window.destroy()
		SingleMessageWindow(self.account, to = self.from_whom,
			action = 'send',	from_whom = self.from_whom, subject = self.subject,
			message = self.message)

	def on_send_and_close_button_clicked(self, widget):
		self.send_single_message()
		self.save_pos()
		self.window.destroy()

	def on_single_message_window_key_press_event(self, widget, event):
		if event.keyval == gtk.keysyms.Escape: # ESCAPE
			self.save_pos()
			self.window.destroy()

class XMLConsoleWindow:
	def __init__(self, account):
		self.account = account
		
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'xml_console_window', APP)
		self.window = self.xml.get_widget('xml_console_window')
		self.input_textview = self.xml.get_widget('input_textview')
		self.stanzas_log_textview = self.xml.get_widget('stanzas_log_textview')
		self.input_tv_buffer = self.input_textview.get_buffer()
		buffer = self.stanzas_log_textview.get_buffer()
		end_iter = buffer.get_end_iter()
		buffer.create_mark('end', end_iter, False)
		
		self.tagIn = buffer.create_tag('incoming')
		color = gajim.config.get('inmsgcolor')
		self.tagIn.set_property('foreground', color)
		self.tagOut = buffer.create_tag('outgoing')
		color = gajim.config.get('outmsgcolor')
		self.tagOut.set_property('foreground', color)

		self.enabled = False

		self.input_textview.modify_text(
			gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
		
		if len(gajim.connections) > 1:
			title = _('XML Console for %s') % self.account
		else:
			title = _('XML Console')
		
		self.window.set_title(title)
		self.window.show_all()
		
		self.xml.signal_autoconnect(self)

	def on_xml_console_window_delete_event(self, widget, event):
		self.window.hide()
		return True # do NOT destroy the window

	def on_clear_button_clicked(self, widget):
		buffer = self.stanzas_log_textview.get_buffer()
		buffer.set_text('')

	def on_enable_checkbutton_toggled(self, widget):
		self.enabled = widget.get_active()

	def scroll_to_end(self, ):
		parent = self.stanzas_log_textview.get_parent()
		buffer = self.stanzas_log_textview.get_buffer()
		self.stanzas_log_textview.scroll_to_mark(buffer.get_mark('end'), 0, True,
			0, 1)
		adjustment = parent.get_hadjustment()
		adjustment.set_value(0)
		return False

	def print_stanza(self, stanza, kind):
		# kind must be 'incoming' or 'outgoing'
		if not self.enabled:
			return

		buffer = self.stanzas_log_textview.get_buffer()
		at_the_end = False
		end_iter = buffer.get_end_iter()
		end_rect = self.stanzas_log_textview.get_iter_location(end_iter)
		visible_rect = self.stanzas_log_textview.get_visible_rect()
		if end_rect.y <= (visible_rect.y + visible_rect.height):
			at_the_end = True
		end_iter = buffer.get_end_iter()
		buffer.insert_with_tags_by_name(end_iter, stanza.replace('><', '>\n<') + \
			'\n\n', kind)
		if at_the_end:
			gobject.idle_add(self.scroll_to_end)

	def on_send_button_clicked(self, widget):
		if gajim.connections[self.account].connected <= 1:
			#if offline or connecting
			ErrorDialog(_('Connection not available'),
		_('Please make sure you are connected with "%s".' % self.account))
			return
		begin_iter, end_iter = self.input_tv_buffer.get_bounds()
		stanza = self.input_tv_buffer.get_text(begin_iter, end_iter).decode('utf-8')
		if stanza:
			gajim.connections[self.account].send_stanza(stanza)
			self.input_tv_buffer.set_text('') # we sent ok, clear the textview
	
	def on_presence_button_clicked(self, widget):
		self.input_tv_buffer.set_text(
		'<presence><show></show><status></status><priority></priority></presence>'
		)

	def on_iq_button_clicked(self, widget):
		self.input_tv_buffer.set_text(
			'<iq to="" type=""><query xmlns=""></query></iq>'
		)
	
	def on_message_button_clicked(self, widget):
		self.input_tv_buffer.set_text(
			'<message to="" type=""><body></body></message>'
		)

	def on_expander_activate(self, widget):
		if not widget.get_expanded(): # it's the opposite!
			# it's expanded!!
			self.input_textview.grab_focus()

class InvitationReceivedDialog:
	def __init__(self, account, room_jid, contact_jid, password = None, comment = None):

		self.room_jid = room_jid
		self.account = account
		xml = gtk.glade.XML(GTKGUI_GLADE, 'invitation_received_dialog', APP)
		self.dialog = xml.get_widget('invitation_received_dialog')
		
		#FIXME: use nickname instead of contact_jid
		pritext = _('%(contact_jid)s has invited you to %(room_jid)s room') % {
			'room_jid': room_jid, 'contact_jid': contact_jid }
		
		label_text = '<big><b>%s</b></big>' % pritext

		if comment: # only if not None and not ''
			sectext = _('Comment: %s') % comment
			label_text += '\n\n%s' % sectext

		xml.get_widget('label').set_markup(label_text)

		xml.get_widget('deny_button').connect('clicked',
			self.on_deny_button_clicked)
		xml.get_widget('accept_button').connect('clicked',
			self.on_accept_button_clicked)
		self.dialog.show_all()
	
	def on_deny_button_clicked(self, widget):
		self.dialog.destroy()
	
	def on_accept_button_clicked(self, widget):
		self.dialog.destroy()
		room, server = gajim.get_room_name_and_server_from_room_jid(self.room_jid)
		JoinGroupchatWindow(self.account, server = server, room = room)
			
class ProgressDialog:
	def __init__(self, title_text, during_text, messages_queue):
		'''during text is what to show during the procedure,
		messages_queue has the message to show
		in the textview'''
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'progress_dialog', APP)
		self.dialog = self.xml.get_widget('progress_dialog')
		self.messages_queue = messages_queue
		self.label = self.xml.get_widget('label')
		self.label.set_markup('<big>' + during_text + '</big>')
		self.progressbar = self.xml.get_widget('progressbar')
		self.textview = self.xml.get_widget('textview')
		self.textview_buffer = self.textview.get_buffer()
		end_iter = self.textview_buffer.get_end_iter()
		self.textview_buffer.create_mark('end', end_iter, False)
		
		self.dialog.set_title(title_text)
		self.dialog.set_default_size(450, 500)
		self.dialog.show_all()
		self.xml.signal_autoconnect(self)
		
		self.update_progressbar_timeout_id = gobject.timeout_add(100,
					self.update_progressbar)
		
		self.read_from_queue_id = gobject.timeout_add(200,
			self.read_from_queue_and_update_textview)
	
	def update_progressbar(self):
		self.progressbar.pulse()
		return True # loop forever
	
	def read_from_queue_and_update_textview(self):
		while not self.messages_queue.empty():
			message = self.messages_queue.get()
			end_iter = self.textview_buffer.get_end_iter()
			self.textview_buffer.insert(end_iter, message + '\n')
			self.textview.scroll_to_mark(self.textview_buffer.get_mark('end'), 0,
				True, 0, 1)

		return True # loop for ever
	
	def on_progress_dialog_delete_event(self, widget, event):
		return True # WM's X button or Escape key should not destroy the window

	def done(self, done_text):
		'''whatever we were doing is done (either we problems or not),
		make close button sensitive and show the done_text in label'''
		self.xml.get_widget('close_button').set_sensitive(True)
		self.label.set_markup('<big>' + done_text + '</big>')
		gobject.source_remove(self.update_progressbar_timeout_id)
		gobject.source_remove(self.read_from_queue_id)
		self.read_from_queue_and_update_textview()
		self.progressbar.set_fraction(1)

class SoundChooserDialog:
	def __init__(self, path_to_snd_file = ''):
		'''optionally accepts path_to_snd_file so it has that as selected'''
		self.dialog = gtk.FileChooserDialog(_('Choose Sound'), None,
					gtk.FILE_CHOOSER_ACTION_OPEN,
					(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
					gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		self.dialog.set_default_response(gtk.RESPONSE_OK)
		last_sounds_dir = gajim.config.get('last_sounds_dir')
		if last_sounds_dir and os.path.isdir('last_sounds_dir'):
			self.dialog.set_current_folder(last_sounds_dir)
		else:
			self.dialog.set_current_folder(gajim.HOME_DIR)

		filter = gtk.FileFilter()
		filter.set_name(_('All files'))
		filter.add_pattern('*')
		self.dialog.add_filter(filter)

		filter = gtk.FileFilter()
		filter.set_name(_('Wav Sounds'))
		filter.add_pattern('*.wav')
		self.dialog.add_filter(filter)
		self.dialog.set_filter(filter)
		
		self.path_to_snd_file = path_to_snd_file
		self.dialog.set_filename(self.path_to_snd_file)
		
		self.path_to_snd_file = ''
		while True:
			response = self.dialog.run()
			if response != gtk.RESPONSE_OK:
				break
			self.path_to_snd_file = self.dialog.get_filename()
			try:
				self.path_to_snd_file = path_to_snd_file.decode(
					sys.getfilesystemencoding())
			except:
				pass
			if os.path.exists(self.path_to_snd_file):
				break
		

class AddSpecialNotificationDialog:
	def __init__(self, jid):
		'''jid is the jid for which we want to add special notification
		(sound and notification popups)'''
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'add_special_notification_window',
			APP)
		self.window = self.xml.get_widget('add_special_notification_window')
		self.condition_combobox = self.xml.get_widget('condition_combobox')
		self.condition_combobox.set_active(0)
		self.notification_popup_yes_no_combobox = self.xml.get_widget(
			'notification_popup_yes_no_combobox')
		self.notification_popup_yes_no_combobox.set_active(0)
		self.listen_sound_combobox = self.xml.get_widget('listen_sound_combobox')
		self.listen_sound_combobox.set_active(0)
		
		
		self.jid = jid
		self.xml.get_widget('when_foo_becomes_label').set_text(
			_('When %s becomes:') % self.jid)
		
		
		self.window.set_title(_('Adding Special Notification for %s') % jid)
		self.window.show_all()
		self.xml.signal_autoconnect(self)
	
	def on_cancel_button_clicked(self, widget):
		self.window.destroy()
	
	def on_add_special_notification_window_delete_event(self, widget, event):
		self.window.destroy()

	def on_listen_sound_combobox_changed(self, widget):
		model = widget.get_model()
		active = widget.get_active()
		if active == 1: # user selected 'choose sound'
			dlg_instance = SoundChooserDialog()
			path_to_snd_file = dlg_instance.path_to_snd_file
			dlg_instance.dialog.destroy()
			
			if path_to_snd_file:
				print path_to_snd_file
			else: # user selected nothing (X button or Cancel)
				widget.set_active(0) # go back to No Sound
		#model[iter][0] = 
	
	def on_ok_button_clicked(self, widget):
		conditions = ('online', 'chat', 'online_and_chat',
			'away', 'xa', 'away_and_xa', 'dnd', 'xa_and_dnd', 'offline')
		active = self.condition_combobox.get_active()
		print conditions[active]
	
		active_iter = self.listen_sound_combobox.get_active_iter()
		listen_sound_model = self.listen_sound_combobox.get_model()
		print listen_sound_model[active_iter][0]
