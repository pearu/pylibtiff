
import sys
from os.path import join, basename, dirname, splitext
from glob import glob

from numpy.distutils import log
from distutils.dep_util import newer


def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    package_name = 'libtiff'
    config = Configuration(package_name,parent_package,top_path)

    bitarray_path = 'bitarray-0.3.5-numpy/bitarray'

    # Add subpackages here:
    config.add_subpackage('bitarray', bitarray_path)
    # eof add.

    # Add extensions here:
    config.add_extension('bitarray._bitarray', join(bitarray_path,'_bitarray.c'))
    config.add_extension('bittools', join('src','bittools.c'))
    config.add_extension('tif_lzw', join('src','tif_lzw.c'))
    # eof add.

    config.make_svn_version_py()

    wininst = 'bdist_wininst' in sys.argv

    # Scripts support: files in scripts directories are considered as
    # python scripts that will be installed as
    # <package_name>.<script_name> to scripts installation directory.
    scripts = glob(join(config.local_path, 'scripts', '*.py'))
    scripts += glob(join(config.local_path, '*', 'scripts', '*.py'))
    for script in scripts:
        if basename (script).startswith (package_name):
            config.add_scripts(script)
            continue

        def generate_a_script(build_dir, script=script, config=config):
            dist = config.get_distribution()
            install_lib = dist.get_command_obj('install_lib')
            if not install_lib.finalized:
                install_lib.finalize_options()

            script_replace_text = ''
            install_lib = install_lib.install_dir
            if install_lib is not None:
                script_replace_text = '''
import sys
if %(d)r not in sys.path:
    sys.path.insert(0, %(d)r)
''' % dict(d=install_lib)

            start_mark = '### START UPDATE SYS.PATH ###'
            end_mark = '### END UPDATE SYS.PATH ###'
            name = basename(script)
            if name.startswith (package_name):
                target_name = name
            elif wininst:
                target_name = package_name + '_' + name
            else:
                target_name = package_name + '.' + splitext(name)[0]
            target = join(build_dir, target_name)
            if newer(script, target) or 1:
                log.info('Creating %r', target)
                f = open (script, 'r')
                text = f.read()
                f.close()

                i = text.find(start_mark)
                if i != -1:
                    j = text.find (end_mark)
                    if j == -1:
                        log.warn ("%r missing %r line", script, start_mark)
                    new_text = text[:i+len (start_mark)] + script_replace_text + text[j:]
                else:
                    new_text = text

                f = open(target, 'w')
                f.write(new_text)
                f.close()
        config.add_scripts(generate_a_script)

    return config
