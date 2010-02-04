# -*- coding:utf-8 -*-
## src/common/check_paths.py
##
## Copyright (C) 2005-2006 Travis Shirk <travis AT pobox.com>
##                         Nikos Kouremenos <kourem AT gmail.com>
## Copyright (C) 2005-2008 Yann Leboulanger <asterix AT lagaule.org>
## Copyright (C) 2006 Dimitur Kirov <dkirov AT gmail.com>
## Copyright (C) 2007 Tomasz Melcer <liori AT exroot.org>
## Copyright (C) 2008 Jean-Marie Traissard <jim AT lapin.org>
##
## This file is part of Gajim.
##
## Gajim is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 3 only.
##
## Gajim is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Gajim. If not, see <http://www.gnu.org/licenses/>.
##

import os
import sys
import stat

from common import gajim
import logger

# DO NOT MOVE ABOVE OF import gajim
import sqlite3 as sqlite

def create_log_db():
	print _('creating logs database')
	print logger.LOG_DB_PATH
	con = sqlite.connect(logger.LOG_DB_PATH)
	os.chmod(logger.LOG_DB_PATH, 0600) # rw only for us
	cur = con.cursor()
	# create the tables
	# kind can be
	# status, gcstatus, gc_msg, (we only recv for those 3),
	# single_msg_recv, chat_msg_recv, chat_msg_sent, single_msg_sent
	# to meet all our needs
	# logs.jid_id --> jids.jid_id but Sqlite doesn't do FK etc so it's done in python code
	# jids.jid text column will be JID if TC-related, room_jid if GC-related,
	# ROOM_JID/nick if pm-related.
	# also check optparser.py, which updates databases on gajim updates
	cur.executescript(
		'''
		CREATE TABLE jids(
			jid_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
			jid TEXT UNIQUE,
			type INTEGER
		);

		CREATE TABLE unread_messages(
			message_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
			jid_id INTEGER,
			shown BOOLEAN default 0
		);

		CREATE INDEX idx_unread_messages_jid_id ON unread_messages (jid_id);

		CREATE TABLE logs(
			log_line_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
			jid_id INTEGER,
			contact_name TEXT,
			time INTEGER,
			kind INTEGER,
			show INTEGER,
			message TEXT,
			subject TEXT
		);

		CREATE INDEX idx_logs_jid_id_time ON logs (jid_id, time DESC);
		'''
		)

	con.commit()
	con.close()

def create_cache_db():
	print _('creating cache database')
	con = sqlite.connect(logger.CACHE_DB_PATH)
	os.chmod(logger.CACHE_DB_PATH, 0600) # rw only for us
	cur = con.cursor()
	cur.executescript(
		'''
		CREATE TABLE transports_cache (
			transport TEXT UNIQUE,
			type INTEGER
		);

		CREATE TABLE caps_cache (
			hash_method TEXT,
			hash TEXT,
			data BLOB,
			last_seen INTEGER);

		CREATE TABLE rooms_last_message_time(
			jid_id INTEGER PRIMARY KEY UNIQUE,
			time INTEGER
		);

		CREATE TABLE IF NOT EXISTS roster_entry(
			account_jid_id INTEGER,
			jid_id INTEGER,
			name TEXT,
			subscription INTEGER,
			ask BOOLEAN,
			PRIMARY KEY (account_jid_id, jid_id)
		);

		CREATE TABLE IF NOT EXISTS roster_group(
			account_jid_id INTEGER,
			jid_id INTEGER,
			group_name TEXT,
			PRIMARY KEY (account_jid_id, jid_id, group_name)
		);
		'''
		)

	con.commit()
	con.close()

def check_and_possibly_create_paths():
	LOG_DB_PATH = logger.LOG_DB_PATH
	LOG_DB_FOLDER, LOG_DB_FILE = os.path.split(LOG_DB_PATH)
	CACHE_DB_PATH = logger.CACHE_DB_PATH
	CACHE_DB_FOLDER, CACHE_DB_FILE = os.path.split(CACHE_DB_PATH)
	VCARD_PATH = gajim.VCARD_PATH
	AVATAR_PATH = gajim.AVATAR_PATH
	import configpaths
	MY_DATA = configpaths.gajimpaths['MY_DATA']
	MY_CONFIG = configpaths.gajimpaths['MY_CONFIG']
	MY_CACHE = configpaths.gajimpaths['MY_CACHE']

	if not os.path.exists(MY_DATA):
		create_path(MY_DATA)
	elif os.path.isfile(MY_DATA):
		print _('%s is a file but it should be a directory') % MY_DATA
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(MY_CONFIG):
		create_path(MY_CONFIG)
	elif os.path.isfile(MY_CONFIG):
		print _('%s is a file but it should be a directory') % MY_CONFIG
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(MY_CACHE):
		create_path(MY_CACHE)
	elif os.path.isfile(MY_CACHE):
		print _('%s is a file but it should be a directory') % MY_CACHE
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(VCARD_PATH):
		create_path(VCARD_PATH)
	elif os.path.isfile(VCARD_PATH):
		print _('%s is a file but it should be a directory') % VCARD_PATH
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(AVATAR_PATH):
		create_path(AVATAR_PATH)
	elif os.path.isfile(AVATAR_PATH):
		print _('%s is a file but it should be a directory') % AVATAR_PATH
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(LOG_DB_FOLDER):
		create_path(LOG_DB_FOLDER)
	elif os.path.isfile(LOG_DB_FOLDER):
		print _('%s is a file but it should be a directory') % LOG_DB_FOLDER
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(LOG_DB_PATH):
		create_log_db()
		gajim.logger.init_vars()
	elif os.path.isdir(LOG_DB_PATH):
		print _('%s is a directory but should be a file') % LOG_DB_PATH
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(CACHE_DB_FOLDER):
		create_path(CACHE_DB_FOLDER)
	elif os.path.isfile(CACHE_DB_FOLDER):
		print _('%s is a file but it should be a directory') % CACHE_DB_FOLDER
		print _('Gajim will now exit')
		sys.exit()

	if not os.path.exists(CACHE_DB_PATH):
		create_cache_db()
		gajim.logger.attach_cache_database()
	elif os.path.isdir(CACHE_DB_PATH):
		print _('%s is a directory but should be a file') % CACHE_DB_PATH
		print _('Gajim will now exit')
		sys.exit()

def create_path(directory):
	print _('creating %s directory') % directory
	os.mkdir(directory, 0700)

# vim: se ts=3:
