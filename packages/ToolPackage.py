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
# Base class for all packages managed by xtools_install 
#
import os
import tarfile
import subprocess
import shutil, stat
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

# return True if OK
# return False if error
def do_and_show_cmd(name, cmd):
    print('=x=', name, '= Working in   : ', show_pwd())
    print('=x=', name, '= Line command : ', cmd)
    returncode = subprocess.call(cmd)
    if (returncode) :
        print('=x=', name, ' Error : ', str(returncode))
        return False
    else :
        print('=x=', name, ', Done.')
        return True

class BaseClass(object):
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
        status = do_and_show_cmd(self.name, cmd)
        return(status)

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
