#!/usr/bin/env python3
## 
#  Cross-toolchain build script
#  Copyright (C) 2024 Cesar Fuguet
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
#ENVIRONMENT
#
# Requires following env variables:
#  RISCV Specifies the base folder for installation of executables
#
# Fills the current working directory with archives, src and
# build directories, used to download sware and compile it
# use `python -u` to unbufferize output (useful if you track log for errors)
# 
# NB the src directories are used to create the build directories
#    the build directories are used to create the target binaries
#    So, if you are running again in the same directory,
#    all existing configuration might be related to a different target
#    Unless you are sure that you are trying to build the same targets,
#    You should answer "Y" to the "Recursively remove all dirs" question
#
# Even though RISCV defines the base folder for the toolchain, some
# libraries might be installed in the folder containing the toolchain base
# folder: this folder is identified by the variable LOCAL_DIR.
#
# E.g. if RISCV is <local_path>/riscv32-unknown-elf, then
#         LOCAL_DIR is <local_path> and, if you install gmp, 
#                  <local_path>/include/
#                  <local_path>/lib/
#                  <local_path>/share/
#      will also be created and filled with stuff.
#
"""This script installs a RISC-V cross-toolchain for a given target architecture
"""

# TODO: check output status of subprocess calls

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__author__ = 'Cesar Fuguet'
__version__ = '1.0.0'

import os
import sys
import errno
import tarfile
import subprocess
import shutil, stat
import argparse

# Determine which command has been called
CalledLink = sys.argv[0]
name = os.path.basename(CalledLink)
# Short description
oneLinerComment = 'Build a RISC-V toolchain at $RISCV'

# These two become only default values
DEFBUILD  = 'x86_64-pc-linux-gnu'
DEFTARGETLIST = ['riscv32-unknown-elf']

# WARNING : if you answer by Y, write-protected dirs
# and files will be removed.
# simple function to support recursive remove of
# write-protected files 
def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)

def remove_onExistence(dirTree, nameString):
    if os.path.exists(dirTree):
        print("=x= WARNING:",  nameString, "dir " + dirTree + " already exists.")
        while True:
            uInput = input("Recursively remove (even write-protected) dirs (Y/N/Q)?")
            if uInput.lower() == "y":
                shutil.rmtree(dirTree, onerror=remove_readonly)
                break
            elif uInput.lower() == "n":     
                print("OK, but it will not work if you tried on a different target ...")
                break
            elif uInput.lower() == "q":     
               print("Exiting ...")
               exit()
            print("I do not understand, continuing ...")
        print()
    return

def show_pwd():
    cwd = os.getcwd()
    return(cwd)

PREFIX_DIR = os.environ["RISCV"]
LOCAL_DIR = os.path.dirname(PREFIX_DIR) 
SYSROOT_DIR = os.path.join(PREFIX_DIR, 'sysroot')
SCRIPT_DIR = os.getcwd()


# Setting this, allows to call tools like riscv32-unknown-elf-ar
# without their full path specification, avoiding errors like 
#/bin/sh: line 2: riscv32-unknown-elf-ar: command not found
os.environ["PATH"] = os.path.join(PREFIX_DIR, 'bin') + ':' + os.environ["PATH"]


class ToolPackage(object):
    """ Generic class for describing a tool package
    """
    def __init__(self, name, configDic, tar_extension):
        """ This function initialize package attributes
        """
        self.name = name
        self.configDic = configDic
        # Allow a more uniform access to version
        # (instead of using gcc_version, gdb_version etc.)
        versionKey = self.name + "_version" 
        self.version = self.configDic[versionKey]
        self.tar_extension = tar_extension

    def get_full_name(self):
        """ This function returns full name of package (name + version)
        """
        return self.name + '-' + self.version

    def get_src(self):
        """ This function returns full path to the package source directory
        """
        return os.path.join(self.configDic['src_dir'], self.get_full_name())

    def get_build(self):
        """ This function returns full path to the package build directory
        """
        return os.path.join(self.configDic['build_dir'], self.get_full_name())

    def get_tar(self):
        """ This function returns full path to the package tar file
        """
        tar_file = self.get_full_name() + self.tar_extension
        return os.path.join(self.configDic['archive_dir'], tar_file)

    # returns True if all is OK, otherwise False
    def download(self, url):
        if os.path.exists(self.get_src()):
            print('The package sources are already extracted.. do nothing')
            return True
        if os.path.exists(self.get_tar()):
            print('The package archive is already downloaded.. do nothing')
            return True
        if not os.path.exists(self.configDic['archive_dir']):
            os.mkdir(self.configDic['archive_dir'])
        print('Fetching from', url)
        cmd = ['wget', '--tries=50', '-q', '-O', self.get_tar(), url]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        return True if returncode == 0 else False

    # returns True always (empty)
    def prerequisites(self):
        print('Downloading prerequisites')
        return True

    # returns True always ... 
    def extract(self):
        """ This function extracts the package tar file
        """
        if not os.path.lexists(self.get_tar()):
            raise IOError(self.get_tar() + ' file not found')
        if not os.path.exists(self.configDic['src_dir']):
            os.mkdir(self.configDic['src_dir'])
        if not os.path.exists(self.get_src()):
            tar = tarfile.open(name=self.get_tar(), mode='r')
            tar.extractall(path=self.configDic['src_dir'])
            tar.close()
        else:
            print('Package already extracted.. do nothing')
        return True

    # returns True always
    # This is a common preliminary step for all build
    # of all packages
    def build(self):
        """ This function prepares the package for its building
        """
        if not os.path.exists(self.configDic['build_dir']):
            os.mkdir(self.configDic['build_dir'])
        if not os.path.exists(self.get_build()):
            os.mkdir(self.get_build())

        # go to the build directory
        os.chdir(self.get_build())
        return True

    # returns True if all is OK, otherwise False
    # TODO : verify that the return values do not introduce side effects
    def install(self):
        """ This function prepares the package for its installation
        """
        if not os.path.exists(self.configDic['install_dir']):
            print('The installation directory does not exists')
            return False
        if not os.access(self.configDic['install_dir'], os.W_OK):
            print('The installation directory has not write permissions')
            return False

        # go to the build directory
        os.chdir(self.get_build())
        return True

class NewlibPackage(ToolPackage):
    """ Class for describing a newlib package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'ftp://sourceware.org/pub/newlib',
        )

    # returns True if all is OK, otherwise False
    def download(self):
        for base_url in self.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(NewlibPackage, self).download(url):
                return True

        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the NEWLIB package for the target
        architecture
        """
        print('=x=NewlibP= _Configuring', self.get_full_name(), '...')
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + self.configDic['install_dir'],
            '--build=' + self.configDic['build'],
            '--host=' + self.configDic['host'],
            '--target=' + self.configDic['target'],
            '--enable-newlib-reent-small',
            '--enable-newlib-nano-malloc',
            '--enable-newlib-global-atexit',
            '--enable-newlib-nano-formatted-io',
            '--enable-lite-exit',
            '--enable-multilib',
            '--disable-newlib-fvwrite-in-streamio',
            '--disable-newlib-fseek-optimization',
            '--disable-newlib-wide-orient',
            '--disable-newlib-unbuf-stream-opt',
            '--disable-newlib-supplied-syscalls',
            '--disable-nls',
            'CFLAGS_FOR_TARGET= -ffunction-sections -fdata-sections -mcmodel=medany',
            'CXXFLAGS_FOR_TARGET= -ffunction-sections -fdata-sections -mcmodel=medany',
        ]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else :
            print('=x=', self.name, ' : ', str(returncode))
        return True

    # returns True if all is OK, otherwise False
    def build(self):
        """ This function builds the NEWLIB package for the target
        architecture
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super(NewlibPackage, self).build()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory ... '
                  'Skip configure')
        else:
            if ( not(self._configure()) ):
                return False
            else:
                print('=x=', self.name, ', Done.')

        # build
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super(NewlibPackage, self).install()) ):
            return False

        # install
        cmd = ['make', 'install']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
            return False
        else:
            print('=x=', self.name, ', Done.')
        return True


class BinutilsPackage(ToolPackage):
    """ Class for describing a binutils package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'http://ftpmirror.gnu.org/binutils',
            'http://ftp.gnu.org/gnu/binutils',
        )

    def download(self):
        for base_url in self.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(BinutilsPackage, self).download(url):
                return True

        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the BINUTILS package for the target
        architecture
        """
        print('=x= _Configuring', self.get_full_name(), '...')
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + self.configDic['install_dir'],
            '--target=' + self.configDic['target'],
            '--program-prefix=' + self.configDic['target'] + '-',
            '--disable-nls',
            '--enable-multilib',
            '--disable-werror',
            self.configDic['binutils_configure_extra_options']
        ]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def build(self):
        """ This function builds the BINUTILS package for the target
        architecture
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super(BinutilsPackage, self).build()) ):
            return False

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory ... '
                  'Skip configure')
        else:
            if ( not(self._configure()) ):
                return False
            else:
                print('=x=', self.name, ', Done.')

        # build
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super(BinutilsPackage, self).install()) ):
            return False

        # install
        cmd = ['make', 'install']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True


class GccPackage(ToolPackage):
    """ Class for describing a GCC package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        print ("Calling deep")
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'http://ftpmirror.gnu.org/gcc',
            'ftp://ftp.gnu.org/gnu/gcc',
        )
        self.newlibPkg = NewlibPackage('newlib',
                                       configDic,
                                       '.tar.gz')
        
    def download(self):
        for base_url in self.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(GccPackage, self).download(url):
                return True

        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the GCC package for the target
        architecture
        """
        print('=x= _Configuring ', self.get_full_name(), '...')
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
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def prerequisites(self):
        """ Install GCC required packages into its source directory
        """
        print('=x= Prerequisites of', self.get_full_name(), '...')
        if ( not(super(GccPackage, self).prerequisites()) ):
            print ("Condition 0 not reached")
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
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
            print ("Condition 1 not reached")
            return False
        else:
            print('=x=', self.name, ', Done.')

        # download and extract the newlib library
        print('=x=', self.name, 'Downloading newlib...')
        if ( not(self.newlibPkg.download()) ):
            print ("Condition 2 not reached")
            return False
        else:
            print('=x=', self.name, ', Done.')
        
        print('=x=', self.name, 'Extracting newlib...')
        if ( not(self.newlibPkg.extract()) ):
            print ("Condition 3 not reached")
            return False
        else:
            print('=x=', self.name, ', Done.')

        return True

    # returns True if all is OK, otherwise False
    def build(self):
        """ This function builds the GCC package for the target architecture
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super(GccPackage, self).build()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # go to the build directory
        os.chdir(self.get_build())

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory ... '
                  'Skip configure')
        else:
            print('=x=', self.name, ' Configuring...')
            if ( not(self._configure()) ):
                return False
            else:
                print('=x=', self.name, ', Done.')

        # compile a partial GCC (stage1)
        # build
        cmd = ['make', '-j' + str(self.configDic['nparallel']), 'all-gcc']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
            return False
        else:
            print('=x=', self.name, ', Done.')
        cmd = ['make', '-j' + str(self.configDic['nparallel']), 'all-target-libgcc']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        print('=x=', self.name, ' Making install...')
        if ( not(super(GccPackage, self).install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')
        
        # install-gcc
        cmd = ['make', 'install-gcc']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
         
        # install-target-libgcc
        cmd = ['make', 'install-target-libgcc']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
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

        # recompile a full GCC (stage2)
        os.chdir(self.get_build())
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        cmd = ['make', 'install']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super(GccPackage, self).install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        cmd = ['make', 'install']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True


class GmpPackage(ToolPackage):
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
            if super(GmpPackage, self).download(url):
                return True

        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the GDB package for the target
        architecture
        """
        print('=x= _Configuring', self.get_full_name(), '...')
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + LOCAL_DIR
        ]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True
    
    # returns True if all is OK, otherwise False
    # performs configure and make steps
    def build(self):
        """ This function builds the GMP package
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super(GmpPackage, self).build()) ):
            return False

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory ... '
                  'Skip configure')
        else:
            if ( not(self._configure()) ):
                return False
            else:
                print('=x=', self.name, ', Done.')

        # build
        cmd = ['make', '-j' + str(self.configDic['nparallel'])]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True
    
    # returns True if all is OK, otherwise False
    # performs make install step
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super(GmpPackage, self).install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        cmd = ['make', 'install']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True


class GdbPackage(ToolPackage):
    """ Class for describing a GDB package
    """
    
    # NB python does not implicitely call constructors of base class
    def __init__(self, name, configDic, tar_extension):
        super().__init__(name, configDic, tar_extension)
        self.repos_url = (
            'http://ftpmirror.gnu.org/gdb',
            'http://ftp.gnu.org/gnu/gdb',
        )
    
    # returns True if all is OK, otherwise False
    def download(self):
        for base_url in self.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(GdbPackage, self).download(url):
                return True

        return False

    # returns True if all is OK, otherwise False
    def _configure(self):
        """ This function configures the GDB package for the target
        architecture
        """
        print('=x= _Configuring', self.get_full_name(), '...')
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + self.configDic['install_dir'],
            '--target=' + self.configDic['target'],
            '--program-prefix=' + self.configDic['target'] + '-',
            '--enable-tui',
            self.configDic['gdb_configure_extra_options']
        ]
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def build(self):
        """ This function builds the GDB package for the target architecture
        """
        print('=x= Building', self.get_full_name(), '...')
        if ( not(super(GdbPackage, self).build()) ):
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
        cmd = ['make', '-j' + str(self.configDic['nparallel']), 'all-gdb']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True

    # returns True if all is OK, otherwise False
    def install(self):
        print('=x= Installing', self.get_full_name(), '...')
        if ( not(super(GdbPackage, self).install()) ):
            return False
        else:
            print('=x=', self.name, ', Done.')

        # install
        cmd = ['make', 'install-gdb']
        print('=x=', self.name, '= Working in   : ', show_pwd())
        print('=x=', self.name, '= Line command : ', cmd)
        returncode = subprocess.call(cmd)
        if (returncode) :
             return False
        else:
            print('=x=', self.name, ', Done.')
        return True


def main():
    """ Main routine
    """
    parser = argparse.ArgumentParser(prog = name,
                                     description = oneLinerComment)
    #'+'. means that all command-line arguments present are gathered into a
    #list. Additionally, an error message will be generated if there wasn’t
    # at least one command-line argument present. 
    parser.add_argument("-t", "--target",  nargs='+',
                        help = "one or more compiler target architectures [e.g. riscv64-unknown-elf",
                        type = str, required=False)
    parser.add_argument("-b", "--build",  nargs=1,
                        help = "The local compiler [e.g. x86_64-pc-linux-gnu]",
                        type = str, required=False)
    # this sets args.target and args.build, if user has provided them
    args = parser.parse_args()
    if (args.build):
        # TO DO : check if it is good wrt local machine
        BUILD = args.build
    else:
        BUILD = DEFBUILD
    if (args.target):
        # TO DO: verify if this is a reasonable target or not
        # TO DO: verify if this works with a list or not
        # basically, all sources should be zapped from the scratch
        TARGETLIST = args.target
    else:
        TARGETLIST = DEFTARGETLIST

    print("B:", BUILD)
    print("T:", TARGETLIST)
    
    CONFIG = {
        'build'             : BUILD,
        'host'              : BUILD,

        #  version of tools
        'binutils_version' :                 '2.38',
        'gcc_version'      :                 '11.2.0',
        'gdb_version'      :                 '11.2',
        'gmp_version'      :                 '6.2.1',
        'mpfr_version'     :                 '4.1.0',
        'mpc_version'      :                 '1.2.1',
        'isl_version'      :                 '0.24',
        'newlib_version'   :                 '4.1.0',

        #  maximum number of parallel jobs to build the tools
        'nparallel'        :                  1,

        #  extra configure options
        'gcc_configure_extra_options' :       '',
        # 'gcc_configure_extra_options' :     '--with-isa-spec=2.2',
        'binutils_configure_extra_options' :  '',
        # 'binutils_configure_extra_options' : '--with-isa-spec=2.2',
        'gdb_configure_extra_options' :  '--with-libgmp-prefix='+LOCAL_DIR,
        #  base directories shared by all tools
        'archive_dir' :                      os.path.join(SCRIPT_DIR, 'archives'),
        'src_dir' :                          os.path.join(SCRIPT_DIR, 'src'),
        'build_dir' :                        os.path.join(SCRIPT_DIR, 'build'),
        'install_dir' :                      PREFIX_DIR,
        'sysroot_dir' :                      SYSROOT_DIR,
    }
    # This would allow doing dry run only
    doStuff = True
    for TARGET in TARGETLIST:
        
        print("=x= running on host :")
        py3output = subprocess.check_output(['uname', '-a'])
        print(py3output)
        print("=x= = = = = = = = == = = = = = = = = = = = = = =")
        print("=x= Treating target : " + TARGET)
        CONFIG['target']= TARGET
        print("=x= = = = = = = = == = = = = = = = = = = = = = =")
        # The most safe to avoid overwriting is this
        # You can tweak and issue only a warning or an error
        if os.path.exists(CONFIG['install_dir']):
            print('WARNING : This installation directory already exists:')
            print(CONFIG['install_dir'])
            # exit(1)
        else:
            print('Creating installation directory ...')
            os.makedirs(CONFIG['install_dir'])    

        remove_onExistence(CONFIG['build_dir'], "build")

        remove_onExistence(CONFIG['src_dir'], "src")

        print('=x= Building', CONFIG['target'], 'cross-compiler')
        print('=x= Archives directory:', CONFIG['archive_dir'])
        print('=x= Sources directory:', CONFIG['src_dir'])
        print('=x= Build directory:', CONFIG['build_dir'])
        print('=x= Install directory:', CONFIG['install_dir'])

        packages = (
            # The order is relevant. gmp must be placed BEFORE gdb.
            BinutilsPackage('binutils', CONFIG, '.tar.gz'),
            GccPackage('gcc', CONFIG, '.tar.gz'),
            GmpPackage('gmp', CONFIG, '.tar.xz'),
            GdbPackage('gdb', CONFIG, '.tar.gz'),
        )
        for pkg in packages:
            print('\n=x= Processing', pkg.get_full_name(), '...')
            print('=x= Starting download phase of', pkg.get_tar(), '...')
            if (doStuff):
                if not(pkg.download())  :
                    print('=x= Download phase failed for', pkg.get_full_name(), '...')
                    break
            print('=x= Starting Extract phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.extract()) ) :
                    print('=x= Extract phase failed for', pkg.get_full_name(), '...')
                    break
            print('=x= Starting Prerequisite phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.prerequisites()) ) :
                    print('=x= Prerequisite phase failed for', pkg.get_full_name(), '...')
                    break
            print('=x= Starting Build phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.build()) ) :
                    print('=x= Build phase failed for', pkg.get_full_name(), '...')
                    break
            print('=x= Starting install phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.install()) ) :
                    print('=x= Install phase failed for', pkg.get_full_name(), '...')
                    break
        print("=x= Completed target : " + TARGET)
    print("=x= xTools completed succesfully.")


if __name__ == '__main__':
    main()
