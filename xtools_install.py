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
##
#ENVIRONMENT
#
# Requires following env variables:
#  RISCV Specifies the base folder for installation of executables
#
#
# Fills the current working directory with archives, src and
# build directories, used to download sware and compile it
#

"""This script installs a cross-toolchain for a given target architecture
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

def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)

TARGET = 'riscv64-unknown-elf'
PREFIX_DIR = os.environ["RISCV"]
SYSROOT_DIR = os.path.join(PREFIX_DIR, 'sysroot')
SCRIPT_DIR = os.getcwd()

CONFIG = {
    'target' :                           TARGET,

    #  version of tools
    'binutils_version' :                 '2.38',
    'gcc_version' :                      '11.2.0',
    'gdb_version' :                      '11.2',
    'gmp_version' :                      '6.2.1',
    'mpfr_version' :                     '4.1.0',
    'mpc_version' :                      '1.2.1',
    'isl_version' :                      '0.24',
    'newlib_version'    : '4.1.0',

    #  maximum number of parallel jobs to build the tools
    'nparallel' : 8,

    #  extra configure options
    'gcc_configure_extra_options' : '',
    # 'gcc_configure_extra_options' :      '--with-isa-spec=2.2',
    'binutils_configure_extra_options' : '',
    # 'binutils_configure_extra_options' : '--with-isa-spec=2.2',

    #  base directories shared by all tools
    'archive_dir' :                      os.path.join(SCRIPT_DIR, 'archives'),
    'src_dir' :                          os.path.join(SCRIPT_DIR, 'src'),
    'build_dir' :                        os.path.join(SCRIPT_DIR, 'build'),
    'install_dir' :                      PREFIX_DIR,
    'sysroot_dir' :                      SYSROOT_DIR,
}

os.environ["PATH"] = os.path.join(CONFIG['install_dir'], 'bin') + ':' + os.environ["PATH"]

class ToolPackage(object):
    """ Generic class for describing a tool package
    """
    def __init__(self, name, version, tar_extension):
        """ This function initialize package attributes
        """
        self.name = name
        self.version = version
        self.tar_extension = tar_extension

    def get_full_name(self):
        """ This function returns full name of package (name + version)
        """
        return self.name + '-' + self.version

    def get_src(self):
        """ This function returns full path to the package source directory
        """
        return os.path.join(CONFIG['src_dir'], self.get_full_name())

    def get_build(self):
        """ This function returns full path to the package build directory
        """
        return os.path.join(CONFIG['build_dir'], self.get_full_name())

    def get_tar(self):
        """ This function returns full path to the package tar file
        """
        tar_file = self.get_full_name() + self.tar_extension
        return os.path.join(CONFIG['archive_dir'], tar_file)

    def download(self, url):
        if os.path.exists(self.get_src()):
            print('The package sources are already extracted.. do nothing')
            return True
        if os.path.exists(self.get_tar()):
            print('The package archive is already downloaded.. do nothing')
            return True
        if not os.path.exists(CONFIG['archive_dir']):
            os.mkdir(CONFIG['archive_dir'])
        print('Fetching from', url)
        cmd = ['wget', '--tries=50', '-q', '-O', self.get_tar(), url]
        returncode = subprocess.call(cmd)
        return True if returncode == 0 else False

    def prerequisites(self):
        print('Downloading prerequisites')
        return

    def extract(self):
        """ This function extracts the package tar file
        """
        if not os.path.lexists(self.get_tar()):
            raise IOError(self.get_tar() + ' file not found')
        if not os.path.exists(CONFIG['src_dir']):
            os.mkdir(CONFIG['src_dir'])
        if not os.path.exists(self.get_src()):
            tar = tarfile.open(name=self.get_tar(), mode='r')
            tar.extractall(path=CONFIG['src_dir'])
            tar.close()
        else:
            print('Package already extracted.. do nothing')

    def build(self):
        """ This function prepares the package for its building
        """
        if not os.path.exists(CONFIG['build_dir']):
            os.mkdir(CONFIG['build_dir'])
        if not os.path.exists(self.get_build()):
            os.mkdir(self.get_build())

        # go to the build directory
        os.chdir(self.get_build())

    def install(self):
        """ This function prepares the package for its installation
        """
        if not os.path.exists(CONFIG['install_dir']):
            print('The installation directory does not exists')
            return
        if not os.access(CONFIG['install_dir'], os.W_OK):
            print('The installation directory has not write permissions')
            return

        # go to the build directory
        os.chdir(self.get_build())

class NewlibPackage(ToolPackage):
    """ Class for describing a newlib package
    """
    repos_url = (
        'ftp://sourceware.org/pub/newlib',
    )

    def download(self):
        for base_url in NewlibPackage.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(NewlibPackage, self).download(url):
                return True

        return False

    def _configure(self):
        """ This function configures the NEWLIB package for the target
        architecture
        """
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + CONFIG['install_dir'],
            '--target=' + CONFIG['target'],
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
        subprocess.call(cmd)

    def build(self):
        """ This function builds the NEWLIB package for the target
        architecture
        """
        super(NewlibPackage, self).build()

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory... '
                  'Skip configure')
        else:
            self._configure()

        # build
        cmd = ['make', '-j' + str(CONFIG['nparallel'])]
        subprocess.call(cmd)

    def install(self):
        super(NewlibPackage, self).install()

        # install
        cmd = ['make', 'install']
        subprocess.call(cmd)


class BinutilsPackage(ToolPackage):
    """ Class for describing a binutils package
    """
    repos_url = (
        'http://ftpmirror.gnu.org/binutils',
        'http://ftp.gnu.org/gnu/binutils',
    )

    def download(self):
        for base_url in BinutilsPackage.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(BinutilsPackage, self).download(url):
                return True

        return False

    def _configure(self):
        """ This function configures the BINUTILS package for the target
        architecture
        """
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + CONFIG['install_dir'],
            '--target=' + CONFIG['target'],
            '--program-prefix=' + CONFIG['target'] + '-',
            '--disable-nls',
            '--enable-multilib',
            '--disable-werror',
            CONFIG['binutils_configure_extra_options'],
        ]
        subprocess.call(cmd)

    def build(self):
        """ This function builds the BINUTILS package for the target
        architecture
        """
        super(BinutilsPackage, self).build()

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory... '
                  'Skip configure')
        else:
            self._configure()

        # build
        cmd = ['make', '-j' + str(CONFIG['nparallel'])]
        subprocess.call(cmd)

    def install(self):
        super(BinutilsPackage, self).install()

        # install
        cmd = ['make', 'install']
        subprocess.call(cmd)


class GccPackage(ToolPackage):
    """ Class for describing a GCC package
    """
    repos_url = (
        'http://ftpmirror.gnu.org/gcc',
        'ftp://ftp.gnu.org/gnu/gcc',
    )

    newlibPkg = NewlibPackage('newlib', CONFIG['newlib_version'], '.tar.gz')

    def download(self):
        for base_url in GccPackage.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(GccPackage, self).download(url):
                return True

        return False

    def _configure(self):
        """ This function configures the GCC package for the target
        architecture
        """
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + CONFIG['install_dir'],
            '--target=' + CONFIG['target'],
            '--program-prefix=' + CONFIG['target'] + '-',
            '--with-newlib',
            '--disable-nls',
            '--enable-multilib',
            '--disable-werror',
            '--without-headers',
            '--enable-languages=c,c++',
            CONFIG['gcc_configure_extra_options'],
            'CFLAGS_FOR_TARGET=-Os -mcmodel=medany',
            'CXXFLAGS_FOR_TARGET=-Os -mcmodel=medany',
        ]
        subprocess.call(cmd)

    def prerequisites(self):
        """ Install GCC required packages into its source directory
        """
        super(GccPackage, self).prerequisites()

        # go to the src directory
        os.chdir(self.get_src())

        # call the contrib script in the GCC source directory. This script
        # downloads the GCC prerequisites
        cmd = [
            os.path.join(self.get_src(), 'contrib/download_prerequisites'),
        ]
        subprocess.call(cmd)

        # download and extract the newlib library
        GccPackage.newlibPkg.download()
        GccPackage.newlibPkg.extract()

    def build(self):
        """ This function builds the GCC package for the target architecture
        """
        super(GccPackage, self).build()

        # go to the build directory
        os.chdir(self.get_build())

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory... '
                  'Skip configure')
        else:
            self._configure()

        # compile a partial GCC (stage1)
        # build
        cmd = ['make', '-j' + str(CONFIG['nparallel']), 'all-gcc']
        subprocess.call(cmd)
        cmd = ['make', '-j' + str(CONFIG['nparallel']), 'all-target-libgcc']
        subprocess.call(cmd)

        # install
        super(GccPackage, self).install()
        cmd = ['make', 'install-gcc']
        subprocess.call(cmd)
        cmd = ['make', 'install-target-libgcc']
        subprocess.call(cmd)

        # build and install newlib (C-library)
        GccPackage.newlibPkg.build()
        GccPackage.newlibPkg.install()

        # recompile a full GCC (stage2)
        os.chdir(self.get_build())
        cmd = ['make', '-j' + str(CONFIG['nparallel'])]
        subprocess.call(cmd)
        cmd = ['make', 'install']
        subprocess.call(cmd)

    def install(self):
        super(GccPackage, self).install()

        # install
        cmd = ['make', 'install']
        subprocess.call(cmd)


class GdbPackage(ToolPackage):
    """ Class for describing a GDB package
    """
    repos_url = (
        'http://ftpmirror.gnu.org/gdb',
        'http://ftp.gnu.org/gnu/gdb',
    )

    def download(self):
        for base_url in GdbPackage.repos_url:
            url = (
                base_url + '/' +
                self.get_full_name() + self.tar_extension
            )
            if super(GdbPackage, self).download(url):
                return True

        return False

    def _configure(self):
        """ This function configures the GDB package for the target
        architecture
        """
        cmd = [
            os.path.join(self.get_src(), 'configure'),
            '--prefix=' + CONFIG['install_dir'],
            '--target=' + CONFIG['target'],
            '--program-prefix=' + CONFIG['target'] + '-',
            '--enable-tui',
        ]
        subprocess.call(cmd)

    def build(self):
        """ This function builds the GDB package for the target architecture
        """
        super(GdbPackage, self).build()

        # configure
        if os.path.lexists('Makefile'):
            print('A Makefile already exists in the build directory... '
                  'Skip configure')
        else:
            self._configure()

        # build
        cmd = ['make', '-j' + str(CONFIG['nparallel']), 'all-gdb']
        subprocess.call(cmd)

    def install(self):
        super(GdbPackage, self).install()

        # install
        cmd = ['make', 'install-gdb']
        subprocess.call(cmd)


def main():
    """ Main routine
    """
    print("= = = = = = = == = = = = = = = = = = = = = =")
    print("Treating target : " + TARGET)
    print("= = = = = = = == = = = = = = = = = = = = = =")
    if not os.path.exists(CONFIG['install_dir']):
        print('ERROR : The installation directory does not exists')
        exit(1)
        
    buildTree = CONFIG['build_dir'];
    if os.path.exists(buildTree):
        print("WARNING: build dir " + buildTree + " already exists.")
        while True:
            uInput = input("Empty recursively dir (Y/N)?")
            if uInput.lower() == "y":
                shutil.rmtree(buildTree, onerror=remove_readonly)
                break
            elif uInput.lower() == "n":     
                print("Exiting...")
                exit()
            print("I do not understand, continuing...")
        
    print('Building', CONFIG['target'], 'cross-compiler')
    print('Archives directory:', CONFIG['archive_dir'])
    print('Sources directory:', CONFIG['src_dir'])
    print('Build directory:', CONFIG['build_dir'])
    print('Install directory:', CONFIG['install_dir'])

    packages = (
        BinutilsPackage('binutils', CONFIG['binutils_version'], '.tar.gz'),
        GccPackage('gcc', CONFIG['gcc_version'], '.tar.gz'),
        GdbPackage('gdb', CONFIG['gdb_version'], '.tar.gz'),
    )
    for pkg in packages:
        print('\nProcessing ', pkg.get_full_name(), '...')

        print('Downloading', pkg.get_tar(), '...')
        pkg.download()
        print('Extracting', pkg.get_full_name(), '...')
        pkg.extract()
        print('Prerequisites', pkg.get_full_name(), '...')
        pkg.prerequisites()
        print('Building', pkg.get_full_name(), '...')
        pkg.build()
        print('Installing', pkg.get_full_name(), '...')
        pkg.install()


if __name__ == '__main__':
    main()
