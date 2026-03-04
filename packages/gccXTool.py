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
# Inherited class for gcc
#
import os
import ToolPackage
import newlibXTool
class Package(ToolPackage.BaseClass):
    """ Class for describing a GCC package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'http://ftpmirror.gnu.org/gcc',
            'ftp://ftp.gnu.org/gnu/gcc',
        )
        self.newlibPkg = newlibXTool.Package('newlib',
                                             configDic,
                                             '.tar.gz')
        
    # returns True if all is OK, otherwise False
    def download(self):
        for base_url in self.repos_url:
            # NB GCC has an additional level of repositories
            url = (
                base_url + '/' +
                self.get_full_name() + '/' +
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
            '--prefix=' + self.configDic['install_dir'],
            '--target=' + self.configDic['target'],
            '--program-prefix=' + self.configDic['target'] + '-',
            '--with-newlib',
            '--disable-nls',
            '--enable-multilib',
            '--disable-werror',
            '--without-headers',
            '--enable-languages=c,c++',
            self.configDic['gcc_configure_extra_options'],
            'CFLAGS_FOR_TARGET=-Os -mcmodel=medany',
            'CXXFLAGS_FOR_TARGET=-Os -mcmodel=medany',
        ]
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        return status

    # returns True if all is OK, otherwise False
    def prerequisites(self):
        """ Install GCC required packages into its source directory
        """
        print('=x= Prerequisites of', self.get_full_name(), '...')
        if ( not(super().prerequisites()) ):
            print ('=x= Prerequisites of', self.get_full_name(), 'failed, aborting')
            return False
        else:
            print('=x=', self.name, ', Done.')
            
        # go to the src directory
        os.chdir(self.get_src())

        # call the contrib script in the GCC source directory. This script
        # downloads the GCC prerequisites
        cmd = [
            os.path.join(self.get_src(), 'contrib/download_prerequisites'),
        ]
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= Prerequisites of', self.get_full_name(), 'failed, aborting dload')
            return False
        else:
            print('=x=', self.name, ', Done.')

        # download and extract the newlib library
        print('=x=', self.name, 'Downloading newlib...')
        if ( not(self.newlibPkg.download()) ):
            print ('=x= Prerequisites of', self.get_full_name(), 'failed, aborting newlibPkg dload')
            return False
        else:
            print('=x=', self.name, ', Done.')
        
        print('=x=', self.name, 'Extracting newlib...')
        if ( not(self.newlibPkg.extract()) ):
            print ('=x= Prerequisites of', self.get_full_name(), 'failed, aborting newlibPkg extract')
            return False
        else:
            print('=x=', self.name, ', Done.')

        return True

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

        #FIXED  go to the build directory
        #FIXED os.chdir(self.get_build())

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
        cmd = ['make', '-j' + str(self.configDic['nparallel']), 'all-gcc']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= stage 0 build of', self.get_full_name(), 'failed, aborting compilation')
            return False
        else:
            print('=x=', self.name, ', Done.')
        cmd = ['make', '-j' + str(self.configDic['nparallel']), 'all-target-libgcc']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= library build of', self.get_full_name(), 'failed, aborting all-target-libgcc')
            return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        print('=x=', self.name, ' Making install...')
        if ( not(super().install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')
        
        # install-gcc
        cmd = ['make', 'install-gcc']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= stage 1 install of', self.get_full_name(), 'failed, aborting install-gcc')
            return False
        else:
            print('=x=', self.name, ', Done.')
        
        # install-target-libgcc
        cmd = ['make', 'install-target-libgcc']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= library install of', self.get_full_name(), 'failed, aborting install-target-libgcc')
            return False
        else:
            print('=x=', self.name, ', Done.')

        # build and install newlib (C-library)
        print('=x=', self.name, 'Building newlib...')
        if ( not(self.newlibPkg.build()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')
        print('=x=', self.name, 'Installing newlib...')
        if ( not(self.newlibPkg.install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # recompile a full GCC (stage 2)
        os.chdir(self.get_build())
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= stage 2 build of', self.get_full_name(), 'failed , aborting make')
            return False
        else:
            print('=x=', self.name, ', Done.')
            
        # install a full GCC (stage 2)
        # not clear why this is made here and not through install
        cmd = ['make', 'install']
        status = ToolPackage.do_and_show_cmd(self.name, cmd)
        if (not status):
            print ('=x= stage 2 install of', self.get_full_name(), 'failed, aborting make')
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

