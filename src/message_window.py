##	message_window.py
##
## Copyright (C) 2005-2006 Travis Shirk <travis@pobox.com>
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
import pango
import gobject

import common
from common import gajim

####################
# FIXME: Can't this stuff happen once?
from common import i18n
_ = i18n._
APP = i18n.APP

GTKGUI_GLADE = 'gtkgui.glade'
####################

class MessageWindow:
	'''Class for windows which contain message like things; chats,
	groupchats, etc.'''

	def __init__(self):
		self._controls = {}

		self.widget_name = 'message_window'
		self.xml = gtk.glade.XML(GTKGUI_GLADE, self.widget_name, APP)
		self.window = self.xml.get_widget(self.widget_name)
		self.alignment = self.xml.get_widget('alignment')
		self.notebook = self.xml.get_widget('notebook')

		# Remove the glade pages
		while self.notebook.get_n_pages():
			self.notebook.remove_page(0)
		# Tab customizations
		pref_pos = gajim.config.get('tabs_position')
		if pref_pos != 'top':
			if pref_pos == 'bottom':
				nb_pos = gtk.POS_BOTTOM
			elif pref_pos == 'left':
				nb_pos = gtk.POS_LEFT
			elif pref_pos == 'right':
				nb_pos = gtk.POS_RIGHT
			else:
				nb_pos = gtk.POS_TOP
		else:
			nb_pos = gtk.POS_TOP
		self.notebook.set_tab_pos(nb_pos)
		if gajim.config.get('tabs_always_visible'):
			self.notebook.set_show_tabs(True)
			self.alignment.set_property('top-padding', 2)
		else:
			self.notebook.set_show_tabs(False)
		self.notebook.set_show_border(gajim.config.get('tabs_border'))

		# Connect event handling for this Window
		self.window.connect('delete-event', self._on_window_delete)
		self.window.connect('destroy', self._on_window_destroy)
		
		self.window.show_all()

	def _on_window_delete(self, win, event):
		print "MessageWindow._on_window_delete:", win, event
	def _on_window_destroy(self, win):
		print "MessageWindow._on_window_destroy:", win

	def new_tab(self, control):
		assert(not self._controls.has_key(control.contact.jid))
		self._controls[control.contact.jid] = control

		control.widget.connect('key_press_event',
					self.on_conversation_textview_key_press_event)
		# FIXME: need to get this event without access to message_textvier
		#control.widget.connect('mykeypress',
		#			self.on_message_textview_mykeypress_event)
		control.widget.connect('key_press_event',
					self.on_message_textview_key_press_event)

		# Add notebook page and connect up to the tab's close button
		xml = gtk.glade.XML(GTKGUI_GLADE, 'chat_tab_ebox', APP)
		tab_label_box = xml.get_widget('chat_tab_ebox')
		xml.signal_connect('on_close_button_clicked', self.on_close_button_clicked,
					control.contact)
		self.notebook.append_page(control.widget, tab_label_box)

		self.redraw_tab(control.contact)
		self.window.show_all()

	def on_message_textview_mykeypress_event(self, widget, event_keyval,
						event_keymod):
		# FIXME: Not called yet
		print "MessageWindow.on_message_textview_mykeypress_event:", event
		# NOTE: handles mykeypress which is custom signal; see message_textview.py

		# construct event instance from binding
		event = gtk.gdk.Event(gtk.gdk.KEY_PRESS) # it's always a key-press here
		event.keyval = event_keyval
		event.state = event_keymod
		event.time = 0 # assign current time

		if event.keyval == gtk.keysyms.ISO_Left_Tab: # SHIFT + TAB
			if event.state & gtk.gdk.CONTROL_MASK: # CTRL + SHIFT + TAB
				self.notebook.emit('key_press_event', event)
		if event.keyval == gtk.keysyms.Tab:
			if event.state & gtk.gdk.CONTROL_MASK: # CTRL + TAB
				self.notebook.emit('key_press_event', event)

	def on_message_textview_key_press_event(self, widget, event):
		print "MessageWindow.on_message_textview_key_press_event:", event
		if event.keyval == gtk.keysyms.Page_Down: # PAGE DOWN
			if event.state & gtk.gdk.CONTROL_MASK: # CTRL + PAGE DOWN
				self.notebook.emit('key_press_event', event)
		elif event.keyval == gtk.keysyms.Page_Up: # PAGE UP
			if event.state & gtk.gdk.CONTROL_MASK: # CTRL + PAGE UP
				self.notebook.emit('key_press_event', event)

	def on_conversation_textview_key_press_event(self, widget, event):
		'''Do not block these events and send them to the notebook'''
		print "MessageWindow.on_conversation_textview_key_press_event:", event
		if event.state & gtk.gdk.CONTROL_MASK:
			if event.keyval == gtk.keysyms.Tab: # CTRL + TAB
				self.notebook.emit('key_press_event', event)
			elif event.keyval == gtk.keysyms.ISO_Left_Tab: # CTRL + SHIFT + TAB
				self.notebook.emit('key_press_event', event)
			elif event.keyval == gtk.keysyms.Page_Down: # CTRL + PAGE DOWN
				self.notebook.emit('key_press_event', event)
			elif event.keyval == gtk.keysyms.Page_Up: # CTRL + PAGE UP
				self.notebook.emit('key_press_event', event)

	def on_close_button_clicked(self, button, contact):
		'''When close button is pressed: close a tab'''
		self.remove_tab(contact)
	
	def remove_tab(self, contact):
		# TODO
		print "MessageWindow.remove_tab"

	def redraw_tab(self, contact):
		ctl = self._controls[contact.jid]
		ctl.update_state()

		hbox = self.notebook.get_tab_label(ctl.widget).get_children()[0]
		status_img = hbox.get_children()[0]
		nick_label = hbox.get_children()[1]

		# Optionally hide close button
		close_button = hbox.get_children()[2]
		if gajim.config.get('tabs_close_button'):
			close_button.show()
		else:
			close_button.hide()

		# FIXME: Handle nb_unread
		num_unread = 0

		# Update nick
		nick_label.set_markup(contact.name)

		# Set tab image (always 16x16); unread messages show the 'message' image
		img_16 = gajim.interface.roster.get_appropriate_state_images(contact.jid)
		if num_unread and gajim.config.get('show_unread_tab_icon'):
			tab_img = img_16['message']
		else:
			tab_img = img_16[contact.show]
		if tab_img.get_storage_type() == gtk.IMAGE_ANIMATION:
			status_img.set_from_animation(tab_img.get_animation())
		else:
			status_img.set_from_pixbuf(tab_img.get_pixbuf())

	def repaint_themed_widgets(self):
		'''Repaint controls in the window with theme color'''
		# iterate through controls and repaint
		for ctl in self._controls.values():
			ctl.repaint_themed_widgets()

class MessageWindowMgr:
	'''A manager and factory for MessageWindow objects'''

	# These constants map to common.config.opt_one_window_types indices
	CONFIG_NEVER   = 0
	CONFIG_ALWAYS  = 1
	CONFIG_PERACCT = 2
	CONFIG_PERTYPE = 3
	# A key constant for the main window for all messages
	MAIN_WIN = 'main'

	def __init__(self):
		''' A dictionary of windows; the key depends on the config:
		 CONFIG_NEVER: The key is the contact JID
		 CONFIG_ALWAYS: The key is MessageWindowMgr.MAIN_WIN 
		 CONFIG_PERACCT: The key is the account name
		 CONFIG_PERTYPE: The key is a message type constant'''
		self.windows = {}
		# Map the mode to a int constant for frequent compares
		mode = gajim.config.get('one_message_window')
		self.mode = common.config.opt_one_window_types.index(mode)
		assert(self.mode != -1)
	
	def _new_window(self):
		win = MessageWindow()
		# we track the lifetime of this window
		win.window.connect('delete-event', self._on_window_delete)
		win.window.connect('destroy', self._on_window_destroy)
		return win

	def _gtkWinToMsgWin(self, gtk_win):
		for w in self.windows.values():
			if w.window == gtk_win:
				return w
		return None

	def _on_window_delete(self, win, event):
		# FIXME
		print "MessageWindowMgr._on_window_delete:", win
		msg_win = self._gtkWinToMsgWin(win)

	def _on_window_destroy(self, win):
		# FIXME
		print "MessageWindowMgr._on_window_destroy:", win
		# TODO: Clean up windows

	def get_window(self, contact, acct, type):
		key = None
		if self.mode == self.CONFIG_NEVER:
			key = contact.jid
		elif self.mode == self.CONFIG_ALWAYS:
			key = self.MAIN_WIN
		elif self.mode == self.CONFIG_PERACCT:
			key = acct
		elif self.mode == self.CONFIG_PERTYPE:
			key = type

		win = None
		try:
			win = self.windows[key]
		except KeyError:
			# FIXME
			print "Creating tabbed chat window for '%s'" % str(key)
			win = self._new_window()
			self.windows[key] = win
		assert(win)
		return win

class MessageControl(gtk.VBox):
	'''An abstract base widget that can embed in the gtk.Notebook of a MessageWindow'''

	def __init__(self, widget_name, contact):
		gtk.VBox.__init__(self)

		self.widget_name = widget_name
		self.contact = contact
		self.compact_view = False

		self.xml = gtk.glade.XML(GTKGUI_GLADE, widget_name, APP)
		self.widget = self.xml.get_widget(widget_name)

	def draw_widgets(self):
		pass # NOTE: Derived classes should implement this
	def repaint_themed_widgets(self, theme):
		pass # NOTE: Derived classes SHOULD implement this
	def update_state(self):
		pass # NOTE: Derived classes SHOULD implement this
