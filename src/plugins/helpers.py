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
Helper code related to plug-ins management system.

:author: Mateusz Biliński <mateusz@bilinski.it>
:since: 05/30/2008
:copyright: Copyright (2008) Mateusz Biliński <mateusz@bilinski.it>
:license: GPL
'''

__all__ = ['log', 'log_calls', 'Singleton']

import logging
log = logging.getLogger('gajim.plugin_system')
'''
Logger for code related to plug-in system.

:type: logging.Logger
'''

consoleloghandler = logging.StreamHandler()
#consoleloghandler.setLevel(1)
consoleloghandler.setFormatter(
        logging.Formatter('%(levelname)s: %(message)s'))
        #logging.Formatter('%(asctime)s %(name)s: %(levelname)s: %(message)s'))
#log.setLevel(logging.DEBUG)
log.addHandler(consoleloghandler)
log.propagate = False

import functools

class log_calls(object):
    '''
    Decorator class for functions to easily log when they are entered and left.
    '''
    
    def __init__(self, classname='', log=log):
        '''
        :Keywords:
          classname : str
            Name of class to prefix function name (if function is a method).
          log : logging.Logger
            Logger to use when outputing debug information on when function has
            been entered and when left. By default: `plugins.helpers.log`
            is used.            
        '''
        
        self.full_func_name = ''
        '''
        Full name of function, with class name (as prefix) if given 
        to decorator.
        
        Otherwise, it's only function name retrieved from function object
        for which decorator was called.
        
        :type: str
        '''
        
        if classname:
            self.full_func_name = classname+'.'
        
    def __call__(self, f):
        '''
        :param f: function to be wrapped with logging statements
        
        :return: given function wrapped by *log.debug* statements
        :rtype: function
        '''
        self.full_func_name += f.func_name
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            log.debug('%(funcname)s() <entered>'%{
                'funcname': self.full_func_name})
            result = f(*args, **kwargs)
            log.debug('%(funcname)s() <left>'%{
                'funcname': self.full_func_name})
            return result
        return wrapper

class Singleton(type):
    '''
    Singleton metaclass.
    '''
    def __init__(cls,name,bases,dic):
        super(Singleton,cls).__init__(name,bases,dic)
        cls.instance=None
        
    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance=super(Singleton,cls).__call__(*args,**kw)
            log.debug('%(classname)s - new instance created'%{
                'classname' : cls.__name__})
        else:
            log.debug('%(classname)s - returning already existing instance'%{
                'classname' : cls.__name__})
            
        return cls.instance