#!/usr/bin/env python
##	plugins/config.py
##
## Gajim Team:
## 	- Yann Le Boulanger <asterix@crans.org>
## 	- Vincent Hanquez <tab@snarc.org>
##
##	Copyright (C) 2003 Gajim Team
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

import pygtk
pygtk.require('2.0')
import gtk
from gtk import TRUE, FALSE
import gtk.glade,gobject
import os,string
import common.sleepy
from common import i18n
_ = i18n._
APP = i18n.APP
gtk.glade.bindtextdomain (APP, i18n.DIR)
gtk.glade.textdomain (APP)

from dialogs import *
import gtkgui

GTKGUI_GLADE='plugins/gtkgui/gtkgui.glade'


class vCard_Window:
	"""Class for window that show vCard information"""
	def delete_event(self, widget=None):
		"""close window"""
		del self.plugin.windows[self.account]['infos'][self.jid]

	def on_close(self, widget):
		"""When Close button is clicked"""
		widget.get_toplevel().destroy()

	def set_value(self, entry_name, value):
		try:
			self.xml.get_widget(entry_name).set_text(value)
		except AttributeError, e:
			pass

	def set_values(self, vcard):
		for i in vcard.keys():
			if type(vcard[i]) == type({}):
				for j in vcard[i].keys():
					self.set_value('entry_'+i+'_'+j, vcard[i][j])
			else:
				if i == 'DESC':
					self.xml.get_widget('textview_DESC').get_buffer().\
						set_text(vcard[i], 0)
				else:
					self.set_value('entry_'+i, vcard[i])

	def add_to_vcard(self, vcard, entry, txt):
		"""Add an information to the vCard dictionary"""
		entries = string.split(entry, '_')
		loc = vcard
		while len(entries) > 1:
			if not loc.has_key(entries[0]):
				loc[entries[0]] = {}
			loc = loc[entries[0]]
			del entries[0]
		loc[entries[0]] = txt
		return vcard

	def make_vcard(self):
		"""make the vCard dictionary"""
		entries = ['FN', 'NICKNAME', 'BDAY', 'EMAIL_USERID', 'URL', 'TEL_NUMBER',\
			'ADR_STREET', 'ADR_EXTADR', 'ADR_LOCALITY', 'ADR_REGION', 'ADR_PCODE',\
			'ADR_CTRY', 'ORG_ORGNAME', 'ORG_ORGUNIT', 'TITLE', 'ROLE']
		vcard = {}
		for e in entries:
			txt = self.xml.get_widget('entry_'+e).get_text()
			if txt != '':
				vcard = self.add_to_vcard(vcard, e, txt)
		buf = self.xml.get_widget('textview_DESC').get_buffer()
		start_iter = buf.get_start_iter()
		end_iter = buf.get_end_iter()
		txt = buf.get_text(start_iter, end_iter, 0)
		if txt != '':
			vcard['DESC']= txt
		return vcard


	def on_retrieve(self, widget):
		if self.plugin.connected[self.account]:
			self.plugin.send('ASK_VCARD', self.account, self.jid)
		else:
			warning_Window(_("You must be connected to get your informations"))

	def on_publish(self, widget):
		if not self.plugin.connected[self.account]:
			warning_Window(_("You must be connected to publish your informations"))
			return
		vcard = self.make_vcard()
		nick = ''
		if vcard.has_key('NICKNAME'):
			nick = vcard['NICKNAME']
		if nick == '':
			nick = self.plugin.accounts[self.account]['name']
		self.plugin.nicks[self.account] = nick
		self.plugin.send('VCARD', self.account, vcard)

	def __init__(self, jid, plugin, account):
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'vcard', APP)
		self.window = self.xml.get_widget('vcard')
		self.jid = jid
		self.plugin = plugin
		self.account = account
		
		self.xml.signal_connect('gtk_widget_destroy', self.delete_event)
		self.xml.signal_connect('on_close_clicked', self.on_close)
		self.xml.signal_connect('on_retrieve_clicked', self.on_retrieve)
		self.xml.signal_connect('on_publish_clicked', self.on_publish)

class preference_Window:
	"""Class for Preferences window"""
	def delete_event(self, widget):
		"""close window"""
		del self.plugin.windows['preferences']

	def on_cancel(self, widget):
		"""When Cancel button is clicked"""
		widget.get_toplevel().destroy()

	def write_cfg(self):
		"""Save preferences in config File and apply them"""
		#Color for incomming messages
		color = self.xml.get_widget('colorbutton_in').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['inmsgcolor'] = colSt
		#Color for outgoing messages
		color = self.xml.get_widget('colorbutton_out').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['outmsgcolor'] = colSt
		#Color for status messages
		color = self.xml.get_widget('colorbutton_status').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['statusmsgcolor'] = colSt
		#Color for account text
		color = self.xml.get_widget('colorbutton_account_text').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['accounttextcolor'] = colSt
		#Color for group text
		color = self.xml.get_widget('colorbutton_group_text').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['grouptextcolor'] = colSt
		#Color for user text
		color = self.xml.get_widget('colorbutton_user_text').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['usertextcolor'] = colSt
		#Color for background account
		color = self.xml.get_widget('colorbutton_account_bg').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['accountbgcolor'] = colSt
		#Color for background group
		color = self.xml.get_widget('colorbutton_group_bg').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['groupbgcolor'] = colSt
		#Color for background user
		color = self.xml.get_widget('colorbutton_user_bg').get_color()
		colSt = '#'+(hex(color.red)+'0')[2:4] + (hex(color.green)+'0')[2:4]\
			+(hex(color.blue)+'0')[2:4]
		self.plugin.config['userbgcolor'] = colSt
		#Font for account
		fontStr = self.xml.get_widget('fontbutton_account_text').get_font_name()
		self.plugin.config['accountfont'] = fontStr
		#Font for group
		fontStr = self.xml.get_widget('fontbutton_group_text').get_font_name()
		self.plugin.config['groupfont'] = fontStr
		#Font for user
		fontStr = self.xml.get_widget('fontbutton_user_text').get_font_name()
		self.plugin.config['userfont'] = fontStr
		#update opened chat windows
		for a in self.plugin.accounts.keys():
			for w in self.plugin.windows[a]['chats'].keys():
				self.plugin.windows[a]['chats'][w].tagIn.\
					set_property("foreground", self.plugin.config['inmsgcolor'])
				self.plugin.windows[a]['chats'][w].tagOut.\
					set_property("foreground", self.plugin.config['outmsgcolor'])
				self.plugin.windows[a]['chats'][w].tagStatus.\
					set_property("foreground", self.plugin.config['statusmsgcolor'])
		#IconStyle
		ist = self.combo_iconstyle.entry.get_text()
		self.plugin.config['iconstyle'] = ist
		self.plugin.roster.mkpixbufs()
		#save position
		chk = self.xml.get_widget('save_position_checkbutton')
		if chk.get_active():
			self.plugin.config['saveposition'] = 1
		else:
			self.plugin.config['saveposition'] = 0
		#autopopup
		if self.chk_autopp.get_active():
			self.plugin.config['autopopup'] = 1
		else:
			self.plugin.config['autopopup'] = 0
		#autopopupaway
		if self.chk_autoppaway.get_active():
			self.plugin.config['autopopupaway'] = 1
		else:
			self.plugin.config['autopopupaway'] = 0
		#autoaway
		if self.chk_autoaway.get_active():
			self.plugin.config['autoaway'] = 1
		else:
			self.plugin.config['autoaway'] = 0
		aat = self.spin_autoawaytime.get_value_as_int()
		self.plugin.config['autoawaytime'] = aat
		#autoxa
		if self.chk_autoxa.get_active():
			self.plugin.config['autoxa'] = 1
		else:
			self.plugin.config['autoxa'] = 0
		axt = self.spin_autoxatime.get_value_as_int()
		self.plugin.config['autoxatime'] = axt
		self.plugin.sleeper = common.sleepy.Sleepy(\
			self.plugin.config['autoawaytime']*60, \
			self.plugin.config['autoxatime']*60)
		#Status messages
		model = self.msg_tree.get_model()
		iter = model.get_iter_first()
		i = 0
		while iter:
			self.plugin.config['msg%i_name' % i] = model.get_value(iter, 0)
			self.plugin.config['msg%i' % i] = model.get_value(iter, 1)
			iter = model.iter_next(iter)
			i += 1
		while self.plugin.config.has_key('msg%s_name' % i):
			del self.plugin.config['msg%i_name' % i]
			del self.plugin.config['msg%i' % i]
			i += 1
		#trayicon
		if self.chk_trayicon.get_active():
			self.plugin.config['trayicon'] = 1
		else:
			self.plugin.config['trayicon'] = 0
		self.plugin.send('CONFIG', None, ('GtkGui', self.plugin.config, 'GtkGui'))
		self.plugin.roster.draw_roster()
		#log presences in user file
		if self.xml.get_widget('chk_log_pres_usr').get_active():
			self.config_logger['lognotusr'] = 1
		else:
			self.config_logger['lognotusr'] = 0
		#log presences in external file
		if self.xml.get_widget('chk_log_pres_ext').get_active():
			self.config_logger['lognotsep'] = 1
		else:
			self.config_logger['lognotsep'] = 0
		self.plugin.send('CONFIG', None, ('Logger', self.config_logger, 'GtkGui'))
		
	def on_ok(self, widget):
		"""When Ok button is clicked"""
		self.write_cfg()
		self.xml.get_widget('Preferences').destroy()

	def on_apply(self, widget):
		"""When Apply button is clicked"""
		self.write_cfg()

	def change_notebook_page(self, number):
		self.notebook.set_current_page(number)

	def on_lookfeel_button_clicked(self, widget, data=None):
		self.change_notebook_page(0)
		
	def on_events_button_clicked(self, widget, data=None):
		self.change_notebook_page(1)
		
	def on_presence_button_clicked(self, widget, data=None):
		self.change_notebook_page(2)

	def on_log_button_clicked(self, widget, data=None):
		self.change_notebook_page(3)

	def fill_msg_treeview(self):
		i = 0
		self.xml.get_widget('delete_msg_button').set_sensitive(False)
		model = self.msg_tree.get_model()
		model.clear()
		while self.plugin.config.has_key('msg%s_name' % i):
			iter = model.append()
			model.set(iter, 0, self.plugin.config['msg%s_name' % i], 1, self.plugin.config['msg%s' % i])
			i += 1

	def on_msg_cell_edited(self, cell, row, new_text):
		model = self.msg_tree.get_model()
		iter = model.get_iter_from_string(row)
		model.set_value(iter, 0, new_text)

	def on_msg_treeview_cursor_changed(self, widget, data=None):
		self.xml.get_widget('delete_msg_button').set_sensitive(True)
		buf = self.xml.get_widget('msg_textview').get_buffer()
		(model, iter) = self.msg_tree.get_selection().get_selected()
		name = model.get_value(iter, 0)
		msg = model.get_value(iter, 1)
		buf.set_text(msg)

	def on_new_msg_button_clicked(self, widget, data=None):
		model = self.msg_tree.get_model()
		iter = model.append()
		model.set(iter, 0, 'msg', 1, 'message')

	def on_delete_msg_button_clicked(self, widget, data=None):
		(model, iter) = self.msg_tree.get_selection().get_selected()
		buf = self.xml.get_widget('msg_textview').get_buffer()
		model.remove(iter)
		buf.set_text('')
		self.xml.get_widget('delete_msg_button').set_sensitive(False)

	def on_msg_textview_changed(self, widget, data=None):
		(model, iter) = self.msg_tree.get_selection().get_selected()
		if not iter:
			return
		buf = self.xml.get_widget('msg_textview').get_buffer()
		first_iter, end_iter = buf.get_bounds()
		name = model.get_value(iter, 0)
		model.set_value(iter, 1, buf.get_text(first_iter, end_iter))
	
	def on_chk_toggled(self, widget, widgets):
		"""set or unset sensitivity of widgets when widget is toggled"""
		for w in widgets:
			w.set_sensitive(widget.get_active())

	def __init__(self, plugin):
		"""Initialize Preference window"""
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'Preferences', APP)
		self.window = self.xml.get_widget('Preferences')
		self.plugin = plugin
		self.combo_iconstyle = self.xml.get_widget('combo_iconstyle')
		self.chk_autopp = self.xml.get_widget('chk_autopopup')
		self.chk_autoppaway = self.xml.get_widget('chk_autopopupaway')
		self.chk_autoaway = self.xml.get_widget('chk_autoaway')
		self.spin_autoawaytime = self.xml.get_widget('spin_autoawaytime')
		self.chk_autoxa = self.xml.get_widget('chk_autoxa')
		self.spin_autoxatime = self.xml.get_widget('spin_autoxatime')
		self.chk_trayicon = self.xml.get_widget('chk_trayicon')
		self.notebook = self.xml.get_widget('preferences_notebook')
		
		#Color for incomming messages
		colSt = self.plugin.config['inmsgcolor']
		self.xml.get_widget('colorbutton_in').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for outgoing messages
		colSt = self.plugin.config['outmsgcolor']
		self.xml.get_widget('colorbutton_out').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for status messages
		colSt = self.plugin.config['statusmsgcolor']
		self.xml.get_widget('colorbutton_status').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#iconStyle
		list_style = os.listdir('plugins/gtkgui/icons/')
		l = []
		for i in list_style:
			if i != 'CVS' and i[0] != '.':
				l.append(i)
		if l.count == 0:
			l.append(" ")
		self.combo_iconstyle.set_popdown_strings(l)
		if self.plugin.config['iconstyle'] in l:
			self.combo_iconstyle.entry.set_text(self.plugin.config['iconstyle'])

		#Save position
		st = self.plugin.config['saveposition']
		self.xml.get_widget('save_position_checkbutton').set_active(st)
		
		#Autopopup
		st = self.plugin.config['autopopup']
		self.chk_autopp.set_active(st)

		#Autopopupaway
		st = self.plugin.config['autopopupaway']
		self.chk_autoppaway.set_active(st)
		self.chk_autoppaway.set_sensitive(self.plugin.config['autopopup'])

		#Autoaway
		st = self.plugin.config['autoaway']
		self.chk_autoaway.set_active(st)

		#Autoawaytime
		st = self.plugin.config['autoawaytime']
		self.spin_autoawaytime.set_value(st)
		self.spin_autoawaytime.set_sensitive(self.plugin.config['autoaway'])

		#Autoxa
		st = self.plugin.config['autoxa']
		self.chk_autoxa.set_active(st)

		#Autoxatime
		st = self.plugin.config['autoxatime']
		self.spin_autoxatime.set_value(st)
		self.spin_autoxatime.set_sensitive(self.plugin.config['autoxa'])

		#Status messages
		self.msg_tree = self.xml.get_widget('msg_treeview')
		model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.msg_tree.set_model(model)
		col = gtk.TreeViewColumn('name')
		self.msg_tree.append_column(col)
		renderer = gtk.CellRendererText()
		col.pack_start(renderer, True)
		col.set_attributes(renderer, text=0)
		renderer.connect('edited', self.on_msg_cell_edited)
		renderer.set_property('editable', True)
		self.fill_msg_treeview()
		buf = self.xml.get_widget('msg_textview').get_buffer()
		buf.connect('changed', self.on_msg_textview_changed)

		#trayicon
		st = self.plugin.config['trayicon']
		self.chk_trayicon.set_active(st)
		if self.plugin.sleeper.getState() == common.sleepy.STATE_UNKNOWN:
			self.chk_trayicon.set_sensitive(False)

		#Color for account text
		colSt = self.plugin.config['accounttextcolor']
		self.xml.get_widget('colorbutton_account_text').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for group text
		colSt = self.plugin.config['grouptextcolor']
		self.xml.get_widget('colorbutton_group_text').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for user text
		colSt = self.plugin.config['usertextcolor']
		self.xml.get_widget('colorbutton_user_text').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for background account
		colSt = self.plugin.config['accountbgcolor']
		self.xml.get_widget('colorbutton_account_bg').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for background group
		colSt = self.plugin.config['groupbgcolor']
		self.xml.get_widget('colorbutton_group_bg').set_color(\
			gtk.gdk.color_parse(colSt))
		
		#Color for background user
		colSt = self.plugin.config['userbgcolor']
		self.xml.get_widget('colorbutton_user_bg').set_color(\
			gtk.gdk.color_parse(colSt))

		#font for account
		fontStr = self.plugin.config['accountfont']
		self.xml.get_widget('fontbutton_account_text').set_font_name(fontStr)
		
		#font for group
		fontStr = self.plugin.config['groupfont']
		self.xml.get_widget('fontbutton_group_text').set_font_name(fontStr)
		
		#font for account
		fontStr = self.plugin.config['userfont']
		self.xml.get_widget('fontbutton_user_text').set_font_name(fontStr)
		
		self.xml.signal_connect('gtk_widget_destroy', self.delete_event)
		self.xml.signal_connect('on_apply_clicked', self.on_apply)
		self.xml.signal_connect('on_ok_clicked', self.on_ok)
		self.xml.signal_connect('on_cancel_clicked', self.on_cancel)
		self.xml.signal_connect('on_msg_treeview_cursor_changed', \
			self.on_msg_treeview_cursor_changed)
		self.xml.signal_connect('on_new_msg_button_clicked', \
			self.on_new_msg_button_clicked)
		self.xml.signal_connect('on_delete_msg_button_clicked', \
			self.on_delete_msg_button_clicked)
		self.xml.signal_connect('on_chk_autopopup_toggled', \
			self.on_chk_toggled, [self.chk_autoppaway])
		self.xml.signal_connect('on_chk_autoaway_toggled', \
			self.on_chk_toggled, [self.spin_autoawaytime])
		self.xml.signal_connect('on_chk_autoxa_toggled', \
			self.on_chk_toggled, [self.spin_autoxatime])
		self.xml.signal_connect('on_lookfeel_button_clicked', \
			self.on_lookfeel_button_clicked)
		self.xml.signal_connect('on_events_button_clicked', \
			self.on_events_button_clicked)
		self.xml.signal_connect('on_presence_button_clicked', \
			self.on_presence_button_clicked)
		self.xml.signal_connect('on_log_button_clicked', \
			self.on_log_button_clicked)

		self.plugin.send('ASK_CONFIG', None, ('GtkGui', 'Logger', {'lognotsep':1,\
			'lognotusr':1}))
		self.config_logger = self.plugin.wait('CONFIG')

		#log presences in user file
		st = self.config_logger['lognotusr']
		self.xml.get_widget('chk_log_pres_usr').set_active(st)

		#log presences in external file
		st = self.config_logger['lognotsep']
		self.xml.get_widget('chk_log_pres_ext').set_active(st)

class accountPreference_Window:
	"""Class for account informations"""
	def delete_event(self, widget):
		"""close window"""
		del self.plugin.windows['accountPreference']
	
	def on_close(self, widget):
		"""When Close button is clicked"""
		widget.get_toplevel().destroy()

	def destroy(self):
		self.xml.get_widget("Account").destroy()

	def init_account(self, infos):
		"""Initialize window with defaults values"""
		if infos.has_key('accname'):
			self.xml.get_widget("entry_name").set_text(infos['accname'])
		if infos.has_key('jid'):
			self.xml.get_widget("entry_jid").set_text(infos['jid'])
		if infos.has_key('savepass'):
			self.xml.get_widget('chk_password').set_active(\
				infos['savepass'])
			if infos['savepass']:
				self.xml.get_widget('entry_password').set_sensitive(True)
				if infos.has_key('password'):
					self.xml.get_widget("entry_password").set_text(infos['password'])
		if infos.has_key('ressource'):
			self.xml.get_widget("entry_ressource").set_text(infos['ressource'])
		if infos.has_key('priority'):
			self.xml.get_widget("entry_priority").set_text(str(infos['priority']))
		if infos.has_key('use_proxy'):
			self.xml.get_widget("checkbutton_proxy").set_active(infos['use_proxy'])
		if infos.has_key('proxyhost'):
			self.xml.get_widget("entry_proxyhost").set_text(infos['proxyhost'])
		if infos.has_key('proxyport'):
			self.xml.get_widget("entry_proxyport").set_text(str(\
				infos['proxyport']))
		if not self.plugin.config.has_key('usegpg'):
			self.xml.get_widget('gpg_key_label').set_text('GPG is not usable on this computer')
			self.xml.get_widget('gpg_choose_key_button').set_sensitive(False)
		if infos.has_key('keyid') and self.plugin.config.has_key('usegpg'):
			if infos['keyid'] and self.plugin.config['usegpg']:
				self.xml.get_widget('gpg_key_label').set_text(infos['keyid'])
				if infos.has_key('keyname'):
					self.xml.get_widget('gpg_name_label').set_text(infos['keyname'])
				self.xml.get_widget('gpg_pass_checkbutton').set_sensitive(True)
				if infos.has_key('savegpgpass'):
					self.xml.get_widget('gpg_pass_checkbutton').set_active(\
						infos['savegpgpass'])
					if infos['savegpgpass']:
						self.xml.get_widget('gpg_pass_entry').set_sensitive(True)
						if infos.has_key('gpgpass'):
							self.xml.get_widget('gpg_pass_entry').set_text(\
								infos['gpgpass'])
		if infos.has_key('autoconnect'):
			self.xml.get_widget('chk_autoconnect').set_active(\
				infos['autoconnect'])

	def on_save_clicked(self, widget):
		"""When save button is clicked : Save informations in config file"""
		savepass = 0
		if self.xml.get_widget("chk_password").get_active():
			savepass = 1
		entryPass = self.xml.get_widget("entry_password")
		entryRessource = self.xml.get_widget("entry_ressource")
		entryPriority = self.xml.get_widget("entry_priority")
		prio = entryPriority.get_text()
		check = self.xml.get_widget("checkbutton")
		entryName = self.xml.get_widget("entry_name")
		entryJid = self.xml.get_widget("entry_jid")
		autoconnect = 0
		if self.xml.get_widget("chk_autoconnect").get_active():
			autoconnect = 1
		checkProxy = self.xml.get_widget("checkbutton_proxy")
		if checkProxy.get_active():
			useProxy = 1
		else:
			useProxy = 0
		entryProxyhost = self.xml.get_widget("entry_proxyhost")
		entryProxyport = self.xml.get_widget("entry_proxyport")
		proxyPort = entryProxyport.get_text()
		proxyHost = entryProxyhost.get_text()
		name = entryName.get_text()
		jid = entryJid.get_text()
		if (name == ''):
			warning_Window(_("You must enter a name for this account"))
			return 0
		if name.find(' ') != -1:
			warning_Window(_("Spaces are not permited in account name"))
			return 0
		if (jid == '') or (string.count(jid, '@') != 1):
			warning_Window(_("You must enter a Jabber ID for this account\nFor example : login@hostname"))
			return 0
		if useProxy:
			if proxyPort != '':
				try:
					proxyPort = string.atoi(proxyPort)
				except ValueError:
					warning_Window(_("Proxy Port must be a port number"))
					return 0
			if proxyHost == '':
				warning_Window(_("You must enter a proxy host to use proxy"))
		if prio != '':
			try:
				prio = string.atoi(prio)
			except ValueError:
				warning_Window(_("Priority must be a number"))
				return 0
		(login, hostname) = string.split(jid, '@')
		keyName = self.xml.get_widget('gpg_name_label').get_text()
		if keyName == '': #no key selected
			keyID = ''
			save_gpg_pass = 0
			gpg_pass = ''
		else:
			keyID = self.xml.get_widget('gpg_key_label').get_text()
			save_gpg_pass = 0
			if self.xml.get_widget('gpg_pass_checkbutton').get_active():
				save_gpg_pass = 1
			gpg_pass = self.xml.get_widget('gpg_pass_entry').get_text()
		#if we are modifying an account
		if self.modify:
			#if we modify the name of the account
			if name != self.account:
				#update variables
				self.plugin.windows[name] = self.plugin.windows[self.account]
				self.plugin.queues[name] = self.plugin.queues[self.account]
				self.plugin.connected[name] = self.plugin.connected[self.account]
				self.plugin.nicks[name] = self.plugin.nicks[self.account]
				self.plugin.roster.groups[name] = \
					self.plugin.roster.groups[self.account]
				self.plugin.roster.contacts[name] = \
					self.plugin.roster.contacts[self.account]
				del self.plugin.windows[self.account]
				del self.plugin.queues[self.account]
				del self.plugin.connected[self.account]
				del self.plugin.nicks[self.account]
				del self.plugin.roster.groups[self.account]
				del self.plugin.roster.contacts[self.account]
				del self.plugin.accounts[self.account]
				self.plugin.send('ACC_CHG', self.account, name)
			self.plugin.accounts[name] = {'name': login, 'hostname': hostname,\
				'savepass': savepass, 'password': entryPass.get_text(), \
				'ressource': entryRessource.get_text(), 'priority' : prio, \
				'autoconnect': autoconnect, 'use_proxy': useProxy, 'proxyhost': \
				entryProxyhost.get_text(), 'proxyport': proxyPort, 'keyid': keyID, \
				'keyname': keyName, 'savegpgpass': save_gpg_pass, \
				'gpgpass': gpg_pass}
			self.plugin.send('CONFIG', None, ('accounts', self.plugin.accounts, \
				'GtkGui'))
			#refresh accounts window
			if self.plugin.windows.has_key('accounts'):
				self.plugin.windows['accounts'].init_accounts()
			#refresh roster
			self.plugin.roster.draw_roster()
			widget.get_toplevel().destroy()
			return
		#if it's a new account
		if name in self.plugin.accounts.keys():
			warning_Window(_("An account already has this name"))
			return
		#if we neeed to register a new account
		if check.get_active():
			self.plugin.send('NEW_ACC', None, (hostname, login, \
				entryPass.get_text(), name, entryRessource.get_text(), prio, \
				useProxy, proxyHost, proxyPort))
			check.set_active(FALSE)
			return
		self.plugin.accounts[name] = {'name': login, 'hostname': hostname,\
			'savepass': savepass, 'password': entryPass.get_text(), 'ressource': \
			entryRessource.get_text(), 'priority' : prio, 'autoconnect': \
			autoconnect, 'use_proxy': useProxy, 'proxyhost': \
			entryProxyhost.get_text(), 'proxyport': proxyPort, 'keyid': keyID, \
			'keyname': keyName, 'savegpgpass': save_gpg_pass, 'gpgpass': gpg_pass}
		self.plugin.send('CONFIG', None, ('accounts', self.plugin.accounts, \
			'GtkGui'))
		#update variables
		self.plugin.windows[name] = {'infos': {}, 'chats': {}, 'gc': {}}
		self.plugin.queues[name] = {}
		self.plugin.connected[name] = 0
		self.plugin.roster.groups[name] = {}
		self.plugin.roster.contacts[name] = {}
		self.plugin.nicks[name] = login
		self.plugin.sleeper_state[name] = 0
		#refresh accounts window
		if self.plugin.windows.has_key('accounts'):
			self.plugin.windows['accounts'].init_accounts()
		#refresh roster
		self.plugin.roster.draw_roster()
		widget.get_toplevel().destroy()

	def on_edit_details_clicked(self, widget):
		entryJid = self.xml.get_widget("entry_jid")
		if not self.plugin.windows.has_key('vcard'):
			self.plugin.windows[self.account]['infos'][entryJid.get_text()] = \
				vCard_Window(entryJid.get_text(), self.plugin, self.account)
			if self.plugin.connected[self.account]:
				self.plugin.send('ASK_VCARD', self.account, entryJid.get_text())
			else:
				warning_Window(_("You must be connected to get your informations"))
	
	def on_choose_gpg(self, widget, data=None):
		w = choose_gpg_Window()
		self.plugin.windows['gpg_keys'] = w
		self.plugin.send('GPG_SECRETE_KEYS', None, ())
		keyID = w.run()
		if keyID == -1:
			return
		if keyID[0] == 'None':
			self.xml.get_widget('gpg_key_label').set_text(_('No key selected'))
			self.xml.get_widget('gpg_name_label').set_text('')
			self.xml.get_widget('gpg_pass_checkbutton').set_sensitive(False)
			self.xml.get_widget('gpg_pass_entry').set_sensitive(False)
		else:
			self.xml.get_widget('gpg_key_label').set_text(keyID[0])
			self.xml.get_widget('gpg_name_label').set_text(keyID[1])
			self.xml.get_widget('gpg_pass_checkbutton').set_sensitive(True)
		self.xml.get_widget('gpg_pass_checkbutton').set_active(False)
		self.xml.get_widget('gpg_pass_entry').set_text('')
	
	def on_chk_toggled(self, widget, widgets):
		"""set or unset sensitivity of widgets when widget is toggled"""
		for w in widgets:
			w.set_sensitive(widget.get_active())

	def on_chk_toggled_and_clear(self, widget, widgets):
		self.on_chk_toggled(widget, widgets)
		for w in widgets:
			if not widget.get_active():
				w.set_text('')

	#info must be a dictionnary
	def __init__(self, plugin, infos = {}):
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'Account', APP)
		self.window = self.xml.get_widget("Account")
		self.plugin = plugin
		self.account = ''
		self.modify = False
		self.xml.get_widget('gpg_key_label').set_text('No key selected')
		self.xml.get_widget('gpg_name_label').set_text('')
		self.xml.get_widget('gpg_pass_checkbutton').set_sensitive(False)
		self.xml.get_widget('gpg_pass_entry').set_sensitive(False)
		self.xml.get_widget('entry_password').set_sensitive(False)
		if infos:
			self.modify = True
			self.account = infos['accname']
			self.init_account(infos)
			self.xml.get_widget("checkbutton").set_sensitive(FALSE)
		self.xml.signal_connect('gtk_widget_destroy', self.delete_event)
		self.xml.signal_connect('on_save_clicked', self.on_save_clicked)
		self.xml.signal_connect('on_edit_details_clicked', \
			self.on_edit_details_clicked)
		self.xml.signal_connect('on_close_clicked', self.on_close)
		self.xml.signal_connect('on_choose_gpg_clicked', self.on_choose_gpg)
		self.xml.signal_connect('on_gpg_pass_checkbutton_toggled', \
			self.on_chk_toggled_and_clear, [self.xml.get_widget('gpg_pass_entry')])
		self.xml.signal_connect('on_pass_checkbutton_toggled', \
			self.on_chk_toggled_and_clear, [self.xml.get_widget('entry_password')])

class accounts_Window:
	"""Class for accounts window : lists of accounts"""
	def delete_event(self, widget):
		"""close window"""
		del self.plugin.windows['accounts']
		
	def on_close(self, widget):
		"""When Close button is clicked"""
		widget.get_toplevel().destroy()
		
	def init_accounts(self):
		"""initialize listStore with existing accounts"""
		self.xml.get_widget("modify_button").set_sensitive(False)
		self.xml.get_widget("delete_button").set_sensitive(False)
		model = self.treeview.get_model()
		model.clear()
		for account in self.plugin.accounts:
			activ = 1
			if self.plugin.accounts[account].has_key("active"):
				activ = self.plugin.accounts[account]["active"]
			iter = model.append()
			model.set(iter, 0, account, 1, \
				self.plugin.accounts[account]["hostname"], 2, activ)

	def on_row_activated(self, widget):
		"""Activate delete and modify buttons when a row is selected"""
		self.xml.get_widget("modify_button").set_sensitive(True)
		self.xml.get_widget("delete_button").set_sensitive(True)

	def on_new_clicked(self, widget):
		"""When new button is clicked : open an account information window"""
		if not self.plugin.windows.has_key('accountPreference'):
			self.plugin.windows['accountPreference'] = \
				accountPreference_Window(self.plugin)

	def on_delete_clicked(self, widget):
		"""When delete button is clicked :
		Remove an account from the listStore and from the config file"""
		sel = self.treeview.get_selection()
		(model, iter) = sel.get_selected()
		account = model.get_value(iter, 0)
		window = confirm_Window(_("Are you sure you want to remove this account (%s) ?") % account)
		if window.wait() == gtk.RESPONSE_OK:
			if self.plugin.connected[account]:
				self.plugin.send('STATUS', account, ('offline', 'offline'))
			del self.plugin.accounts[account]
			self.plugin.send('CONFIG', None, ('accounts', self.plugin.accounts, \
				'GtkGui'))
			del self.plugin.windows[account]
			del self.plugin.queues[account]
			del self.plugin.connected[account]
			del self.plugin.roster.groups[account]
			del self.plugin.roster.contacts[account]
			self.plugin.roster.draw_roster()
			self.init_accounts()

	def on_modify_clicked(self, widget):
		"""When modify button is clicked :
		open the account information window for this account"""
		if not self.plugin.windows.has_key('accountPreference'):
#			infos = {}
			sel = self.treeview.get_selection()
			(model, iter) = sel.get_selected()
			account = model.get_value(iter, 0)
			infos = self.plugin.accounts[account]
			infos['accname'] = account
			infos['jid'] = self.plugin.accounts[account]["name"] + \
				'@' +  self.plugin.accounts[account]["hostname"]
			self.plugin.windows['accountPreference'] = \
				accountPreference_Window(self.plugin, infos)

	def on_toggled(self, cell, path, model=None):
		iter = model.get_iter(path)
		model.set_value(iter, 2, not cell.get_active())
		account = model.get_value(iter, 0)
		if cell.get_active():
			self.plugin.accounts[account]["active"] = 0
		else:
			self.plugin.accounts[account]["active"] = 1
		
	def __init__(self, plugin):
		self.plugin = plugin
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'Accounts', APP)
		self.window = self.xml.get_widget("Accounts")
		self.treeview = self.xml.get_widget("treeview")
		model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, \
			gobject.TYPE_BOOLEAN)
		self.treeview.set_model(model)
		#columns
		renderer = gtk.CellRendererText()
		self.treeview.insert_column_with_attributes(-1, _('Name'), renderer, \
			text=0)
		renderer = gtk.CellRendererText()
		self.treeview.insert_column_with_attributes(-1, _('Server'), \
			renderer, text=1)
		renderer = gtk.CellRendererToggle()
		renderer.set_property('activatable', True)
		renderer.connect('toggled', self.on_toggled, model)
		self.treeview.insert_column_with_attributes(-1, _('Active'), \
			renderer, active=2)
		self.xml.signal_connect('gtk_widget_destroy', self.delete_event)
		self.xml.signal_connect('on_row_activated', self.on_row_activated)
		self.xml.signal_connect('on_new_clicked', self.on_new_clicked)
		self.xml.signal_connect('on_delete_clicked', self.on_delete_clicked)
		self.xml.signal_connect('on_modify_clicked', self.on_modify_clicked)
		self.xml.signal_connect('on_close_clicked', self.on_close)
		self.init_accounts()


class agentRegistration_Window:
	"""Class for agent registration window :
	window that appears when we want to subscribe to an agent"""
	def on_cancel(self, widget):
		"""When Cancel button is clicked"""
		widget.get_toplevel().destroy()
		
	def draw_table(self):
		"""Draw the table in the window"""
		nbrow = 0
		table = self.xml.get_widget('table')
		for name in self.infos.keys():
			if name != 'key' and name != 'instructions' and name != 'x':
				nbrow = nbrow + 1
				table.resize(rows=nbrow, columns=2)
				label = gtk.Label(name)
				table.attach(label, 0, 1, nbrow-1, nbrow, 0, 0, 0, 0)
				entry = gtk.Entry()
				entry.set_text(self.infos[name])
				table.attach(entry, 1, 2, nbrow-1, nbrow, 0, 0, 0, 0)
				self.entries[name] = entry
				if nbrow == 1:
					entry.grab_focus()
		table.show_all()
	
	def on_ok(self, widget):
		"""When Ok button is clicked :
		send registration info to the core"""
		for name in self.entries.keys():
			self.infos[name] = self.entries[name].get_text()
		user1 = gtkgui.user(self.agent, self.agent, ['Agents'], 'offline', 'offline', \
			'from', '', 0, '')
		self.plugin.roster.contacts[self.account][self.agent] = [user1]
		self.plugin.roster.add_user_to_roster(self.agent, self.account)
		self.plugin.send('REG_AGENT', self.account, self.agent)
		widget.get_toplevel().destroy()
	
	def __init__(self, agent, infos, plugin, account):
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'agent_reg', APP)
		self.agent = agent
		self.infos = infos
		self.plugin = plugin
		self.account = account
		self.xml.get_widget('agent_reg').set_title(_("Register to %s") % agent)
		self.xml.get_widget('label').set_text(infos['instructions'])
		self.entries = {}
		self.draw_table()
		self.xml.signal_connect('on_cancel_clicked', self.on_cancel)
		self.xml.signal_connect('on_button_ok_clicked', self.on_ok)


class browseAgent_Window:
	"""Class for bowser agent window :
	to know the agents on the selected server"""
	def delete_event(self, widget):
		"""close window"""
		del self.plugin.windows[self.account]['browser']

	def on_cancel(self, widget):
		"""When Cancel button is clicked"""
		widget.get_toplevel().destroy()

	def on_close(self, widget):
		"""When Close button is clicked"""
		widget.get_toplevel().destroy()
		
	def browse(self):
		"""Send a request to the core to know the available agents"""
		self.plugin.send('REQ_AGENTS', self.account, None)
	
	def agents(self, agents):
		"""When list of available agent arrive :
		Fill the treeview with it"""
		model = self.treeview.get_model()
		for agent in agents:
			iter = model.append(None, (agent['name'], agent['jid']))
			self.agent_infos[agent['jid']] = {'features' : []}
	
	def agent_info(self, agent, identities, features, items):
		"""When we recieve informations about an agent"""
		model = self.treeview.get_model()
		iter = model.get_iter_root()
		if not iter:
			return
		while (1):
			if agent == model.get_value(iter, 1):
				break
			if model.iter_has_child(iter):
				iter = model.iter_children(iter)
			else:
				if not model.iter_next(iter):
					iter = model.iter_parent(iter)
				iter = model.iter_next(iter)
			if not iter:
				return
		self.agent_infos[agent]['features'] = features
		if len(identities):
			self.agent_infos[agent]['identities'] = identities
			if identities[0].has_key('name'):
				model.set_value(iter, 0, identities[0]['name'])
		for item in items:
			model.append(iter, (item['name'], item['jid']))
			self.agent_infos[item['jid']] = {'identities': [item]}

	def on_refresh(self, widget):
		"""When refresh button is clicked :
		refresh list : clear and rerequest it"""
		self.treeview.get_model().clear()
		self.browse()

	def on_row_activated(self, widget, path, col=0):
		"""When a row is activated :
		Register or join the selected agent"""
		pass

	def on_join_button_clicked(self, widget):
		"""When we want to join a conference :
		Ask specific informations about the selected agent and close the window"""
		model, iter = self.treeview.get_selection().get_selected()
		service = model.get_value(iter, 1)
		room = ''
		if string.find(service, '@') > -1:
			services = string.split(service, '@')
			room = services[0]
			service = services[1]
		if not self.plugin.windows.has_key('join_gc'):
			self.plugin.windows['join_gc'] = join_gc(self.plugin, self.account, service, room)

	def on_register_button_clicked(self, widget):
		"""When we want to register an agent :
		Ask specific informations about the selected agent and close the window"""
		model, iter = self.treeview.get_selection().get_selected()
		service = model.get_value(iter, 1)
		self.plugin.send('REG_AGENT_INFO', self.account, service)
		widget.get_toplevel().destroy()
	
	def on_cursor_changed(self, widget):
		"""When we select a row :
		activate buttons if needed"""
		model, iter = self.treeview.get_selection().get_selected()
		jid = model.get_value(iter, 1)
		self.register_button.set_sensitive(False)
		if self.agent_infos[jid].has_key('features'):
			if common.jabber.NS_REGISTER in self.agent_infos[jid]['features']:
				self.register_button.set_sensitive(True)
		self.join_button.set_sensitive(False)
		if self.agent_infos[jid].has_key('identities'):
			if len(self.agent_infos[jid]['identities']):
				if self.agent_infos[jid]['identities'][0].has_key('category'):
					if self.agent_infos[jid]['identities'][0]['category'] == 'conference':
						self.join_button.set_sensitive(True)
		
	def __init__(self, plugin, account):
		xml = gtk.glade.XML(GTKGUI_GLADE, 'browser', APP)
		self.window = xml.get_widget('browser')
		self.treeview = xml.get_widget('treeview')
		self.plugin = plugin
		self.account = account
		self.agent_infos = {}
		model = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.treeview.set_model(model)
		#columns
		renderer = gtk.CellRendererText()
		renderer.set_data('column', 0)
		self.treeview.insert_column_with_attributes(-1, 'Name', renderer, text=0)
		renderer = gtk.CellRendererText()
		renderer.set_data('column', 1)
		self.treeview.insert_column_with_attributes(-1, 'Service', \
			renderer, text=1)

		self.register_button = xml.get_widget('register_button')
		self.register_button.set_sensitive(False)
		self.join_button = xml.get_widget('join_button')
		self.join_button.set_sensitive(False)

		xml.signal_connect('gtk_widget_destroy', self.delete_event)
		xml.signal_connect('on_refresh_clicked', self.on_refresh)
		xml.signal_connect('on_row_activated', self.on_row_activated)
		xml.signal_connect('on_join_button_clicked', self.on_join_button_clicked)
		xml.signal_connect('on_register_button_clicked', self.on_register_button_clicked)
		xml.signal_connect('on_cursor_changed', self.on_cursor_changed)
		xml.signal_connect('on_close_clicked', self.on_close)
		if self.plugin.connected[account]:
			self.browse()
		else:
			warning_Window(_("You must be connected to view Agents"))

class join_gc:
	def delete_event(self, widget):
		"""close window"""
		del self.plugin.windows['join_gc']

	def on_close(self, widget):
		"""When Cancel button is clicked"""
		widget.get_toplevel().destroy()

	def on_join(self, widget):
		"""When Join button is clicked"""
		nick = self.xml.get_widget('entry_nick').get_text()
		room = self.xml.get_widget('entry_room').get_text()
		server = self.xml.get_widget('entry_server').get_text()
		passw = self.xml.get_widget('entry_pass').get_text()
		jid = '%s@%s' % (room, server)
		self.plugin.windows[self.account]['gc'][jid] = gtkgui.gc(jid, nick, \
			self.plugin, self.account)
		#TODO: verify entries
		self.plugin.send('GC_JOIN', self.account, (nick, room, server, passw))
		widget.get_toplevel().destroy()

	def __init__(self, plugin, account, server='', room = ''):
		self.plugin = plugin
		self.account = account
		self.xml = gtk.glade.XML(GTKGUI_GLADE, 'Join_gc', APP)
		self.window = self.xml.get_widget('Join_gc')
		self.xml.get_widget('entry_server').set_text(server)
		self.xml.get_widget('entry_room').set_text(room)
		self.xml.get_widget('entry_nick').set_text(self.plugin.nicks[self.account])
		self.xml.signal_connect('gtk_widget_destroy', self.delete_event)
		self.xml.signal_connect('on_cancel_clicked', self.on_close)
		self.xml.signal_connect('on_join_clicked', self.on_join)
