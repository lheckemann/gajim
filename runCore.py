#!/usr/bin/env python
##	runCore.py
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

import logging
logging.basicConfig()

import common
import core

from common import i18n
i18n.init()
_ = i18n._

import getopt, sys

def usage():
	print "usage :", sys.argv[0], ' [OPTION]'
	print "  -c\tlaunch Gajim as a client of a Gajim server"
	print "  -h, --help\tdisplay this help and exit"

try:
	opts, args = getopt.getopt(sys.argv[1:], "ch", ["help"])
except getopt.GetoptError:
	# print help information and exit:
	usage()
	sys.exit(2)
mode = 'server'
for o, a in opts:
	if o == '-c':
		mode = 'client'
	if o in ("-h", "--help"):
		usage()
		sys.exit()

core.core.start(mode)
print _("Core Stopped")
