# -*- coding: utf-8 -*-

## This file is part of Gajim.
##
## Gajim is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 3 only.
##
## Gajim is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Gajim.  If not, see <http://www.gnu.org/licenses/>.
##

'''
Plug-in management related classes.

:author: Mateusz Biliński <mateusz@bilinski.it>
:since: 30th May 2008
:copyright: Copyright (2008) Mateusz Biliński <mateusz@bilinski.it>
:license: GPL
'''

__all__ = ['PluginManager']

import os
import sys
import fnmatch

from common import gajim
from common import nec

from plugins.helpers import log, log_calls, Singleton
from plugins.plugin import GajimPlugin

class PluginManager(object):
	'''
	Main plug-in management class.
	
	Currently: 
		- scans for plugins
		- activates them
		- handles GUI extension points, when called by GUI objects after plugin 
		  is activated (by dispatching info about call to handlers in plugins)
	
	:todo: add more info about how GUI extension points work
	:todo: add list of available GUI extension points
	:todo: implement mechanism to dynamically load plugins where GUI extension
		   points have been already called (i.e. when plugin is activated
		   after GUI object creation). [DONE?]
	:todo: implement mechanism to dynamically deactive plugins (call plugin's
		   deactivation handler) [DONE?]
	:todo: when plug-in is deactivated all GUI extension points are removed
		   from `PluginManager.gui_extension_points_handlers`. But when
		   object that invoked GUI extension point is abandoned by Gajim, eg.
		   closed ChatControl object, the reference to called GUI extension
		   points is still in `PluginManager.gui_extension_points`. These
		   should be removed, so that object can be destroyed by Python.
		   Possible solution: add call to clean up method in classes
		   'destructors' (classes that register GUI extension points)
	'''
	
	__metaclass__ = Singleton

	#@log_calls('PluginManager')
	def __init__(self):
		self.plugins = []
		'''
		Detected plugin classes.
		
		Each class object in list is `GajimPlugin` subclass.
		
		:type: [] of class objects
		'''
		self.active_plugins = []
		'''
		Instance objects of active plugins.
		
		These are object instances of classes held `plugins`, but only those
		that were activated.
		
		:type: [] of `GajimPlugin` based objects
		'''
		self.gui_extension_points = {}
		'''
		Registered GUI extension points.
		'''
		
		self.gui_extension_points_handlers = {}
		'''
		Registered handlers of GUI extension points.
		'''

		for path in gajim.PLUGINS_DIRS:
			self.add_plugins(PluginManager.scan_dir_for_plugins(path))

		#log.debug('plugins: %s'%(self.plugins))

		self._activate_all_plugins_from_global_config()

		#log.debug('active: %s'%(self.active_plugins))

	@log_calls('PluginManager')
	def _plugin_has_entry_in_global_config(self, plugin):
		if gajim.config.get_per('plugins', plugin.short_name) is None:
			return False
		else:
			return True
	
	@log_calls('PluginManager')
	def _create_plugin_entry_in_global_config(self, plugin):
		gajim.config.add_per('plugins', plugin.short_name)
		
	@log_calls('PluginManager')
	def add_plugin(self, plugin_class):
		'''
		:todo: what about adding plug-ins that are already added? Module reload
		and adding class from reloaded module or ignoring adding plug-in?
		'''
		plugin = plugin_class()
		
		if plugin not in self.plugins:
			if not self._plugin_has_entry_in_global_config(plugin):
				self._create_plugin_entry_in_global_config(plugin)
				
			self.plugins.append(plugin)
			plugin.active = False
		else:
			log.info('Not loading plugin %s v%s from module %s (identified by short name: %s). Plugin already loaded.'%(
				plugin.name, plugin.version, plugin.__module__, plugin.short_name))
	
	@log_calls('PluginManager')
	def add_plugins(self, plugin_classes):
		for plugin_class in plugin_classes:
			self.add_plugin(plugin_class)
		
	@log_calls('PluginManager')
	def gui_extension_point(self, gui_extpoint_name, *args):
		'''
		Invokes all handlers (from plugins) for particular GUI extension point
		and adds it to collection for further processing (eg. by plugins not active
		yet).
		
		:param gui_extpoint_name: name of GUI extension point.
		:type gui_extpoint_name: unicode
		:param args: parameters to be passed to extension point handlers 
			(typically and object that invokes `gui_extension_point`; however, 
			this can be practically anything)
		:type args: tuple

		:todo: GUI extension points must be documented well - names with
			parameters that will be passed to handlers (in plugins). Such
			documentation must be obeyed both in core and in plugins. This
			is a loosely coupled approach and is pretty natural in Python.
			   
		:bug: what if only some handlers are successfully connected? we should
			revert all those connections that where successfully made. Maybe
			call 'self._deactivate_plugin()' or sth similar.
			Looking closer - we only rewrite tuples here. Real check should be
			made in method that invokes gui_extpoints handlers.
		'''

		self._add_gui_extension_point_call_to_list(gui_extpoint_name, *args)
		self._execute_all_handlers_of_gui_extension_point(gui_extpoint_name, *args)
	
	@log_calls('PluginManager')
	def remove_gui_extension_point(self, gui_extpoint_name, *args):
		'''
		Removes GUI extension point from collection held by `PluginManager`.
		
		From this point this particular extension point won't be visible
		to plugins (eg. it won't invoke any handlers when plugin is activated).
		
		GUI extension point is removed completely (there is no way to recover it
		from inside `PluginManager`).
		
		Removal is needed when instance object that given extension point was
		connect with is destroyed (eg. ChatControl is closed or context menu
		is hidden).
		
		Each `PluginManager.gui_extension_point` call should have a call of 
		`PluginManager.remove_gui_extension_point` related to it.

		:note: in current implementation different arguments mean different
			extension points. The same arguments and the same name mean
			the same extension point.
		:todo: instead of using argument to identify which extpoint should be
			removed, maybe add additional 'id' argument - this would work similar
			hash in Python objects. 'id' would be calculated based on arguments
			passed or on anything else (even could be constant). This would give
			core developers (that add new extpoints) more freedom, but is this 
			necessary?
		
		:param gui_extpoint_name: name of GUI extension point.
		:type gui_extpoint_name: unicode
		:param args: arguments that `PluginManager.gui_extension_point` was
			called with for this extension point. This is used (along with
			extension point name) to identify element to be removed.
		:type args: tuple
		'''

		if gui_extpoint_name in self.gui_extension_points:
			#log.debug('Removing GUI extpoint\n name: %s\n args: %s'%(gui_extpoint_name, args))
			self.gui_extension_points[gui_extpoint_name].remove(args)
		
				
	@log_calls('PluginManager')
	def _add_gui_extension_point_call_to_list(self, gui_extpoint_name, *args):
		'''
		Adds GUI extension point call to list of calls.
		
		This is done only if such call hasn't been added already
		(same extension point name and same arguments).
		
		:note: This is assumption that GUI extension points are different only
		if they have different name or different arguments. 
		
		:param gui_extpoint_name: GUI extension point name used to identify it
			by plugins.
		:type gui_extpoint_name: str
		
		:param args: parameters to be passed to extension point handlers 
			(typically and object that invokes `gui_extension_point`; however, 
			this can be practically anything)
		:type args: tuple
		
		'''
		if ((gui_extpoint_name not in self.gui_extension_points)
			or (args not in self.gui_extension_points[gui_extpoint_name])):
			self.gui_extension_points.setdefault(gui_extpoint_name, []).append(args)
	
	@log_calls('PluginManager')
	def _execute_all_handlers_of_gui_extension_point(self, gui_extpoint_name, *args):
		if gui_extpoint_name in self.gui_extension_points_handlers:
			for handlers in self.gui_extension_points_handlers[gui_extpoint_name]:
				handlers[0](*args)
				
	def _register_events_handlers_in_ged(self, plugin):
		for event_name, handler in plugin.events_handlers.iteritems():
			priority = handler[0]
			handler_function = handler[1]
			gajim.ged.register_event_handler(event_name,
											 priority,
											 handler_function)
			
	def _remove_events_handler_from_ged(self, plugin):
		for event_name, handler in plugin.events_handlers.iteritems():
			priority = handler[0]
			handler_function = handler[1]
			gajim.ged.remove_event_handler(event_name,
											 priority,
											 handler_function)
			
	def _register_network_events_in_nec(self, plugin):
		for event_class in plugin.events:
			if issubclass(event_class, nec.NetworkIncomingEvent):
				gajim.nec.register_incoming_event(event_class)
			elif issubclass(event_class, nec.NetworkOutgoingEvent):
				gajim.nec.register_outgoing_event(event_class)
	
	def _remove_network_events_from_nec(self, plugin):
		for event_class in plugin.events:
			if issubclass(event_class, nec.NetworkIncomingEvent):
				gajim.nec.unregister_incoming_event(event_class)
			elif issubclass(event_class, nec.NetworkOutgoingEvent):
				gajim.nec.unregister_outgoing_event(event_class)

	@log_calls('PluginManager')
	def activate_plugin(self, plugin):
		'''
		:param plugin: plugin to be activated
		:type plugin: class object of `GajimPlugin` subclass
		
		:todo: success checks should be implemented using exceptions. Such
			control should also be implemented in deactivation. Exceptions
			should be shown to user inside popup dialog, so the reason
			for not activating plugin is known.
		'''
		success = False
		if not plugin.active:
	
			self._add_gui_extension_points_handlers_from_plugin(plugin)
			self._handle_all_gui_extension_points_with_plugin(plugin)
			self._register_events_handlers_in_ged(plugin)
			self._register_network_events_in_nec(plugin)
			
			success = True
			
			if success:
				self.active_plugins.append(plugin)
				plugin.activate()
				self._set_plugin_active_in_global_config(plugin)
				plugin.active = True

		return success
	
	def deactivate_plugin(self, plugin):
		# remove GUI extension points handlers (provided by plug-in) from
		# handlers list
		for gui_extpoint_name, gui_extpoint_handlers in \
				plugin.gui_extension_points.iteritems():
			self.gui_extension_points_handlers[gui_extpoint_name].remove(gui_extpoint_handlers)
		
		# detaching plug-in from handler GUI extension points (calling
		# cleaning up method that must be provided by plug-in developer
		# for each handled GUI extension point)
		for gui_extpoint_name, gui_extpoint_handlers in \
				plugin.gui_extension_points.iteritems():
			if gui_extpoint_name in self.gui_extension_points:
				for gui_extension_point_args in self.gui_extension_points[gui_extpoint_name]:
					handler = gui_extpoint_handlers[1]
					if handler:
						handler(*gui_extension_point_args)
						
		self._remove_events_handler_from_ged(plugin)
		self._remove_network_events_from_nec(plugin)
		
		# removing plug-in from active plug-ins list
		plugin.deactivate()
		self.active_plugins.remove(plugin)
		self._set_plugin_active_in_global_config(plugin, False)
		plugin.active = False
		
	def _deactivate_all_plugins(self):
		for plugin_object in self.active_plugins:
			self.deactivate_plugin(plugin_object)
	
	@log_calls('PluginManager')
	def _add_gui_extension_points_handlers_from_plugin(self, plugin):
		for gui_extpoint_name, gui_extpoint_handlers in \
				plugin.gui_extension_points.iteritems():
			self.gui_extension_points_handlers.setdefault(gui_extpoint_name, []).append(
					gui_extpoint_handlers)
	
	@log_calls('PluginManager')
	def _handle_all_gui_extension_points_with_plugin(self, plugin):
		for gui_extpoint_name, gui_extpoint_handlers in \
				plugin.gui_extension_points.iteritems():
			if gui_extpoint_name in self.gui_extension_points:
				for gui_extension_point_args in self.gui_extension_points[gui_extpoint_name]:
					handler = gui_extpoint_handlers[0]
					if handler:
						handler(*gui_extension_point_args)

	@log_calls('PluginManager')
	def _activate_all_plugins(self):
		'''
		Activates all plugins in `plugins`.
		
		Activated plugins are appended to `active_plugins` list.
		'''
		#self.active_plugins = []
		for plugin in self.plugins:
			self.activate_plugin(plugin)
			
	def _activate_all_plugins_from_global_config(self):
		for plugin in self.plugins:
			if self._plugin_is_active_in_global_config(plugin):
				self.activate_plugin(plugin)
		
	def _plugin_is_active_in_global_config(self, plugin):
		return gajim.config.get_per('plugins', plugin.short_name, 'active')
	
	def _set_plugin_active_in_global_config(self, plugin, active=True):
		gajim.config.set_per('plugins', plugin.short_name, 'active', active)

	@staticmethod
	@log_calls('PluginManager')
	def scan_dir_for_plugins(path):
		'''
		Scans given directory for plugin classes.
		
		:param path: directory to scan for plugins
		:type path: unicode
		
		:return: list of found plugin classes (subclasses of `GajimPlugin`
		:rtype: [] of class objects
		
		:note: currently it only searches for plugin classes in '\*.py' files
			present in given direcotory `path` (no recursion here)
		
		:todo: add scanning packages
		:todo: add scanning zipped modules
		'''
		plugins_found = []
		if os.path.isdir(path):
			dir_list = os.listdir(path)
			#log.debug(dir_list)

			sys.path.insert(0, path)
			#log.debug(sys.path)

			for elem_name in dir_list:
				#log.debug('- "%s"'%(elem_name))
				file_path = os.path.join(path, elem_name)
				#log.debug('  "%s"'%(file_path))
				
				module = None
				
				if os.path.isfile(file_path) and fnmatch.fnmatch(file_path,'*.py'):
					module_name = os.path.splitext(elem_name)[0]
					#log.debug('Possible module detected.')
					try:
						module = __import__(module_name)
						#log.debug('Module imported.')
					except ValueError, value_error:
						pass
						#log.debug('Module not imported successfully. ValueError: %s'%(value_error))
					except ImportError, import_error:
						pass
						#log.debug('Module not imported successfully. ImportError: %s'%(import_error))
					
				elif os.path.isdir(file_path):
					module_name = elem_name
					file_path += os.path.sep
					#log.debug('Possible package detected.')
					try:
						module = __import__(module_name)
						#log.debug('Package imported.')
					except ValueError, value_error:
						pass
						#log.debug('Package not imported successfully. ValueError: %s'%(value_error))
					except ImportError, import_error:
						pass
						#log.debug('Package not imported successfully. ImportError: %s'%(import_error))
					
					
				if module:
					log.debug('Attributes processing started')
					for module_attr_name in [attr_name for attr_name in dir(module) 
											 if not (attr_name.startswith('__') or 
													 attr_name.endswith('__'))]:
						module_attr = getattr(module, module_attr_name)
						log.debug('%s : %s'%(module_attr_name, module_attr))
						
						try:
							if issubclass(module_attr, GajimPlugin) and \
							   not module_attr is GajimPlugin:
								log.debug('is subclass of GajimPlugin')
								#log.debug('file_path: %s\nabspath: %s\ndirname: %s'%(file_path, os.path.abspath(file_path), os.path.dirname(os.path.abspath(file_path))))
								#log.debug('file_path: %s\ndirname: %s\nabspath: %s'%(file_path, os.path.dirname(file_path), os.path.abspath(os.path.dirname(file_path))))
								module_attr.__path__ = os.path.abspath(os.path.dirname(file_path))
								plugins_found.append(module_attr)
						except TypeError, type_error:
							pass
							#log.debug('module_attr: %s, error : %s'%(
								#module_name+'.'+module_attr_name,
								#type_error))

					#log.debug(module)

		return plugins_found