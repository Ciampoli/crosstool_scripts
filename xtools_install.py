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
#SYNOPSIS
# [python [-u]] ./xtools_install.py [-t <target>] [-b <build>]
#
#DESCRIPTION
# Fills the current working directory with archives, src and
# build directories, used to download sware and compile it
#
#ENVIRONMENT
#
# Requires following env variables:
#  RISCV Specifies the base folder for installation of executables
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
#EXAMPLES
# python -u ./xtools_install.py -t riscv32-unknown-elf |& tee install.log
#
# `python -u` unbufferizes output, so you can search log for "=x="
# (highlighted actions ongoing).
# -t specifies the target, riscv32 baremetal cross-compiler ('elf')
# Other possible target examples: riscv64-unknown-elf, riscv64-unknown-linux
# 
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# WARNING
#
#    The src directories are used to create the build directories
#    The build directories are used to create the target binaries
# 
#    So, if you are running again in the same directory,
#    all existing configuration might be related to a different target
# 
#    Unless you are sure that you are trying to re-build the same targets
#    or continue some interrupted work, you should answer "Y" to all
#    "Recursively remove all dirs" questions
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
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
#import shutil, stat
import argparse


xToolsDir = os.getcwd()
sys.path.append(os.path.join(xToolsDir, 'packages'))
import ToolPackage
import gccXTool
import gdbXTool
import gmpXTool
import binutilsXTool

# Determine which command has been called
CalledLink = sys.argv[0]
name = os.path.basename(CalledLink)
# Short description
oneLinerComment = 'Build a RISC-V toolchain at $RISCV'

# These two become only default values
DEFBUILD  = 'x86_64-pc-linux-gnu'
DEFTARGETLIST = ['riscv32-unknown-elf']
# Other variables are used here and will be stored in configDic
PREFIX_DIR = os.environ["RISCV"]
LOCAL_DIR = os.path.dirname(PREFIX_DIR) 
SYSROOT_DIR = os.path.join(PREFIX_DIR, 'sysroot')
SCRIPT_DIR = os.getcwd()


# Setting this, allows to call tools like riscv32-unknown-elf-ar
# without their full path specification, avoiding errors like 
#/bin/sh: line 2: riscv32-unknown-elf-ar: command not found
os.environ["PATH"] = os.path.join(PREFIX_DIR, 'bin') + ':' + os.environ["PATH"]


def main():
    """ Main routine
    """
    parser = argparse.ArgumentParser(prog = name,
                                     description = oneLinerComment)
    #'+'. means that all command-line arguments present are gathered into a
    #list. Additionally, an error message will be generated if there wasn’t
    # at least one command-line argument present. 
    parser.add_argument('-t', '--target',  nargs='+',
                        help = "one or more compiler target architectures [e.g. riscv64-unknown-elf",
                        type = str, required=False)
    parser.add_argument('-b', '--build',  nargs=1,
                        help = "The local compiler [e.g. x86_64-pc-linux-gnu]",
                        type = str, required=False)

    parser.add_argument('-p', '--package',  nargs=1,
                        help = "Package to be installed [e.g. gcc or gdb]",
                        type = str, required=True)

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
        'nparallel'        :                  8,

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
        'local_dir' :                        LOCAL_DIR,
        'sysroot_dir' :                      SYSROOT_DIR,
    }
        
    # Next should be in part redundant
    quitCauseSyntaxError = False
    pName = ''
    if (args.package == None):
        quitCauseSyntaxError = True

    if (isinstance(args.package, list)):
        if (len(args.package)>1):
            quitCauseSyntaxError = True
        else:
            pName = args.package[0]
            
    if (quitCauseSyntaxError):
        print ('ERROR: please provide exactly one package to be installed')
        print ('Currently supported options are :')
        print ('   gcc')
        print ('   gdb')
        print (' ... bailing out.')
        exit(1)

   
    packages = []
    if (pName == 'gcc'):
        packages = (
            # The order is relevant. binutils must be placed BEFORE gcc.
            binutilsXTool.Package('binutils', CONFIG, '.tar.gz'),
            gccXTool.Package('gcc', CONFIG, '.tar.gz'),
        )
    if (pName == 'gdb'):
        packages = (
            # The order is relevant. gmp must be placed BEFORE gdb.
            gmpXTool.Package('gmp', CONFIG, '.tar.xz'),
            gdbXTool.Package('gdb', CONFIG, '.tar.gz'),
        )
    if (not len(packages) ) :
        print ('ERROR: package argument', args.package, 'not recognized')
        print ('Currently supported options are :')
        print ('   gcc')
        print ('   gdb')
        print (' ... bailing out.')
        exit(2)
    print("B:", BUILD)
    print("T:", TARGETLIST)
    
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

        ToolPackage.remove_onExistence(CONFIG['build_dir'], "build")

        ToolPackage.remove_onExistence(CONFIG['src_dir'], "src")

        print('=x= Building', CONFIG['target'], 'cross-compiler')
        print('=x= Archives directory:', CONFIG['archive_dir'])
        print('=x= Sources directory:', CONFIG['src_dir'])
        print('=x= Build directory:', CONFIG['build_dir'])
        print('=x= Install directory:', CONFIG['install_dir'])
        # this holds the current status
        failFlag = False
        for pkg in packages:
            print('\n=x= Processing', pkg.get_full_name(), '...')
            print('=x= Starting download phase of', pkg.get_tar(), '...')
            if (doStuff):
                if not(pkg.download())  :
                    print('=x= Download phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
            print('=x= Starting Extract phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.extract()) ) :
                    print('=x= Extract phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
            print('=x= Starting Prerequisite phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.prerequisites()) ) :
                    print('=x= Prerequisite phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
            print('=x= Starting Build phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.build()) ) :
                    print('=x= Build phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
            print('=x= Starting install phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.install()) ) :
                    print('=x= Install phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
            # this phase is required in multi-user environments
            print('=x= Starting chmod phase of', pkg.get_full_name(), '...')
            if (doStuff):
                if ( not(pkg.chmod_src()) ) :
                    print('=x= chmod phase failed for', pkg.get_full_name(), '...')
                    failFlag = True
                    break
        if (failFlag) :
            print("=x= Aborted at target : " + TARGET)
            break
        else:
            print("=x= Completed target : " + TARGET)
            
    if (failFlag) :
        print("=x= xTools aborted.")
        exit(3)
    else:
        print("=x= xTools completed succesfully.")


if __name__ == '__main__':
    main()
