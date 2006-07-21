'''atom_window.py - a window to display atom entries from pubsub. For now greatly simplified,
supports only simple feeds like the one from pubsub.com. '''

import gtk
import gtk.gdk

import gtkgui_helpers
from common import helpers

class AtomWindow:
	window = None
	entries = []

	@classmethod				# python2.4 decorator
	def newAtomEntry(cls, entry):
		''' Queue new entry, open window if there's no one opened. '''
		cls.entries.append(entry)

		if cls.window is None:
			cls.window = AtomWindow()
		else:
			cls.window.updateCounter()

	def __init__(self):
		''' Create new window... only if we have anything to show. '''
		assert len(self.__class__.entries)>0

		self.entry = None	# the entry actually displayed

		self.xml = gtkgui_helpers.get_glade('atom_entry_window.glade')
		self.window = self.xml.get_widget('atom_entry_window')
		for name in ('new_entry_label', 'feed_title_label', 'feed_title_eventbox',
			'feed_tagline_label', 'entry_title_label', 'entry_title_eventbox',
			'last_modified_label', 'close_button', 'next_button'):
			self.__dict__[name] = self.xml.get_widget(name)

		self.displayNextEntry()

		self.xml.signal_autoconnect(self)
		self.window.show_all()

		self.entry_title_eventbox.add_events(gtk.gdk.BUTTON_PRESS_MASK)
		self.feed_title_eventbox.add_events(gtk.gdk.BUTTON_PRESS_MASK)

	def displayNextEntry(self):
		''' Get next entry from the queue and display it in the window. '''
		assert len(self.__class__.entries)>0

		newentry = self.__class__.entries.pop(0)
		
		# fill the fields
		if newentry.feed_link is not None:
			self.feed_title_label.set_markup(
				u'<span foreground="blue" underline="single">%s</span>' % \
				gtkgui_helpers.escape_for_pango_markup(newentry.feed_title))
		else:
			self.feed_title_label.set_markup(
				gtkgui_helpers.escape_for_pango_markup(newentry.feed_title))

		self.feed_tagline_label.set_markup(
			u'<small>%s</small>' % \
			gtkgui_helpers.escape_for_pango_markup(newentry.feed_tagline))

		if newentry.uri is not None:
			self.entry_title_label.set_markup(
				u'<span foreground="blue" underline="single">%s</span>' % \
				gtkgui_helpers.escape_for_pango_markup(newentry.title))
		else:
			self.entry_title_label.set_markup(
				gtkgui_helpers.escape_for_pango_markup(newentry.title))

		self.last_modified_label.set_text(newentry.updated)

		# update the counters
		self.updateCounter()

		self.entry = newentry

	def updateCounter(self):
		''' We display number of events on the top of window, sometimes it needs to be
		changed...'''
		count = len(self.__class__.entries)
		# TODO: translate
		if count>0:
			self.new_entry_label.set_text( \
				'You have received new entries (and %(count)d not displayed):' % \
				{'count': count})
			self.next_button.set_sensitive(True)
		else:
			self.new_entry_label.set_text('You have received new entry:')
			self.next_button.set_sensitive(False)

	def on_close_button_clicked(self, widget):
		self.window.destroy()

	def on_next_button_clicked(self, widget):
		self.displayNextEntry()

	def on_entry_title_button_press_event(self, widget, event):
		# TODO: make it using special gtk2.10 widget
		print 1
		if event.button == 1:	# left click
			uri = self.entry.uri
			if uri is not None:
				helpers.launch_browser_mailer('url', uri)
		return True

	def on_feed_title_button_press_event(self, widget, event):
		# TODO: make it using special gtk2.10 widget
		print 2
		if event.button == 1:	# left click
			uri = self.entry.feed_uri
			if uri is not None:
				helpers.launch_browser_mailer('url', uri)
		return True
