#!/usr/bin/env python3
## 
#  Cross-toolchain build script
#  Copyright (C) 2026 Cesar Fuguet, Lorenzo Ciampolini
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
##
# @file   xtools_install.py
# @author Cesar Fuguet
# @author Lorenzo Ciampolini
##
#SYNOPSIS
# [python [-u]] ./xtools_install.py [-t <target>] [-b <build>]
#
#DESCRIPTION
# Inherited class for gmp 
#
import os
import ToolPackage
class Package(ToolPackage.BaseClass):
    """ Class for describing a GDB package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'http://gmplib.org/download/gmp',
        )

    # returns True if all is OK, otherwise False
    def download(self):
        for base_url in self.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super().download(url):
                return True
        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the package for the target
        architecture
        """
        print('=x= _Configuring', self.get_full_name(), '...')
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + self.configDic['local_dir']
        ]
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        return status

    # performs configure and make steps
    # returns True if all is OK, otherwise False
    def build(self):
        """ This function builds the package for the target
        architecture
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super().build()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory ... '
                  'Skip configure')
        else:
            print('=x=', self.name, 'Configuring...')
            if ( not(self._configure()) ):
                return False
            else:
                print('=x=', self.name, ', Done.')

        # build
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= build of', self.get_full_name(), 'failed, aborting make')
            return False
        else:
            print('=x=', self.name, ', Done.')
        return status

    # performs make install step
    # returns True if all is OK, otherwise False
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super().install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        cmd = ['make', 'install']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= install of', self.get_full_name(), 'failed, aborting make')
            return False
        else:
            print('=x=', self.name, ', Done.')
        return status

