from distutils.core import setup
from distutils.extension import Extension

ext_modules = []
cmdclass = {}
try:
    # try building the scheduler as shared object, if cython is installed
    from Cython.Distutils import build_ext
    ext_modules = [Extension("schedulers", ["pycpa_taskchain/schedulers.py"]),
            Extension("path_analysis", ["pycpa_taskchain/path_analysis.py"])]
    cmdclass = {'build_ext': build_ext}
    print "Cython available, building as CPython extension"
except ImportError:
    pass

setup(
    name='pycpa_taskchain',
    version='devel',
    description='pyCPA task-chain analysis extension',
    author='Johannes Schlatow',
    author_email='schlatow@ida.ing.tu-bs.de',
    license='proprietary',
    packages= ['taskchain'],
    cmdclass = cmdclass,
    ext_modules = ext_modules
)
