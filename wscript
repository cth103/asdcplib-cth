from __future__ import print_function

import subprocess
import shlex
import os
import sys
import distutils.spawn
from waflib import Logs

APPNAME = 'libasdcp-cth'

if os.path.exists('.git'):
    this_version = subprocess.Popen(shlex.split('git tag -l --points-at HEAD'), stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
    last_version = subprocess.Popen(shlex.split('git describe --tags --abbrev=0'), stdout=subprocess.PIPE).communicate()[0]
    if this_version == '':
        VERSION = '%sdevel' % last_version[1:].strip()
    else:
        VERSION = this_version[1:].strip()
else:
    VERSION = open('VERSION').read().strip()

def options(opt):
    opt.load('compiler_cxx')
    opt.add_option('--target-windows', action='store_true', default=False, help='set up to do a cross-compile to Windows')
    opt.add_option('--enable-debug', action='store_true', default=False, help='build with debugging information and without optimisation')
    opt.add_option('--static', action='store_true', default=False, help='build statically')

def configure(conf):
    conf.load('compiler_cxx')
    conf.env.append_value('CXXFLAGS', ['-Wall', '-Wextra', '-D_FILE_OFFSET_BITS=64', '-D__STDC_FORMAT_MACROS'])

    conf.env.TARGET_WINDOWS = conf.options.target_windows
    conf.env.TARGET_OSX = sys.platform == 'darwin'
    conf.env.TARGET_LINUX = not conf.env.TARGET_WINDOWS and not conf.env.TARGET_OSX
    conf.env.STATIC = conf.options.static
    conf.env.VERSION = VERSION

    if conf.env.TARGET_OSX:
        conf.env.append_value('CXXFLAGS', ['-Wno-unused-result', '-Wno-unused-parameter', '-Wno-unused-local-typedef'])

    if conf.env.TARGET_LINUX:
        gcc = conf.env['CC_VERSION']
        if int(gcc[0]) >= 4 and int(gcc[1]) > 1:
            conf.env.append_value('CXXFLAGS', ['-Wno-unused-result'])

    conf.check_cfg(package='openssl', args='--cflags --libs', uselib_store='OPENSSL', mandatory=True)

    if conf.options.target_windows:
        boost_lib_suffix = '-mt'
    else:
        boost_lib_suffix = ''

    if conf.options.enable_debug:
        conf.env.append_value('CXXFLAGS', '-g')
    else:
        conf.env.append_value('CXXFLAGS', '-O2')

    conf.check_cxx(fragment="""
                            #include <boost/version.hpp>\n
                            #if BOOST_VERSION < 104500\n
                            #error boost too old\n
                            #endif\n
                            int main(void) { return 0; }\n
                            """,
                   mandatory=True,
                   msg='Checking for boost library >= 1.45',
                   okmsg='yes',
                   errmsg='too old\nPlease install boost version 1.45 or higher.')

    conf.check_cxx(fragment="""
    			    #include <boost/filesystem.hpp>\n
    			    int main() { boost::filesystem::copy_file ("a", "b"); }\n
			    """,
                   msg='Checking for boost filesystem library',
                   libpath='/usr/local/lib',
                   lib=['boost_filesystem%s' % boost_lib_suffix, 'boost_system%s' % boost_lib_suffix],
                   uselib_store='BOOST_FILESYSTEM')

    conf.check(header_name='valgrind/memcheck.h', mandatory=False)

    conf.recurse('src')

def build(bld):
    if bld.env.TARGET_WINDOWS:
        boost_lib_suffix = '-mt'
        flags = '-DKM_WIN32'
    else:
        boost_lib_suffix = ''
        flags = ''

    bld(source='libasdcp-cth.pc.in',
        version=VERSION,
        includedir='%s/include/libasdcp-cth' % bld.env.PREFIX,
        libs="-L${libdir} -lasdcp-cth -lkumu-cth -lboost_system%s" % boost_lib_suffix,
        cflags=flags,
        install_path='${LIBDIR}/pkgconfig')

    bld.recurse('src')

    bld.add_post_fun(post)

def post(ctx):
    if ctx.cmd == 'install':
        ctx.exec_command('/sbin/ldconfig')

def tags(bld):
    os.system('etags src/*.cc src/*.h')

def dist(bld):
    f = open('VERSION', 'w')
    print(VERSION, file=f)
    f.close()
