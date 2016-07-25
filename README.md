# libafl [![PyPI](https://img.shields.io/pypi/v/libafl.svg?maxAge=2592000)]()

A library for compiling binaries and running them from python code. This library is not for fuzzing python code. This library is still in development, expect bugs and breaking API changes.

## Installation

```
pip install libafl
```

## Usage

First define a `Target`. A target has three methods, `init` for downloading/extracting/patching a package, `build` for building it, and `run` for running it. All three are optional. There is a special target for AFL targets call `AflTarget`.

``` python
class LibfooAflTarget(libafl.AflTarget):
    # The root directory for our fuzzing project. In this case, the location of
    # this script
    root_path = os.path.dirname(os.path.realpath(__file__))

    # The directory our target's source code will be located in
    src_dir = 'libfoo-afl'

    # Pass any constructor arguments to the super class
    def __init__(self, *args, **kwargs):
        super(LibarchiveAflTarget, self).__init__(*args, **kwargs)

    # Extract the included tar file and move to the directory with the correct
    # name
    def init(self):
        if not os.path.isdir(self.src_dir):
            subprocess.check_output(['tar', '-xf', 'libfoo-0.0.1.tar.gz'])
            shutil.move('libfoo-0.0.1', self.src_dir)

    # Build both the library and a test program with AFL instrumentation
    def build(self):
        # AflTarget provides this method and includes other options as well
        envs = self.set_afl_envs(cc='afl-gcc')
        env = dict(os.environ, **envs)
        subprocess.check_output(
            './configure && make',
            shell=True,
            env=env,
        )
        os.chdir(self.root_path);
        subprocess.check_output(
            ('afl-gcc libfootest.c -I %s/include -L %s/libs -o libfootest-afl') %
            (self.src_dir, self.src_dir),
            shell=True,
            env=env,
        )
```

Create a new `AflProject` and register all targets:

``` python
class LibfooProject(libafl.AflProject):
    def __init__(self, wrapper=None):
        super(LibarchiveProject, self).__init__(wrapper)

        self.addTarget('afl', LibarchiveAflTarget('input', 'output', './libfootest-afl', '@@'))
```

Now you can run functions manually:

``` python
project = LibfooProject()
project.build('afl') # or project.build_all() to build all targets
project.run('afl')
```

Or use the builtin command line interface:

``` python
libafl.handle_args(LibfooProject(libafl.TmuxWrapper()))
```

Note in this example we used the `TmuxWrapper`, which will launch fuzzers in new `tmux` windows. You can write your own wrappers for other programs (like `screen`).

The command line interface provides the following options:

```
vagrant@vagrant-ubuntu-trusty-64:/vagrant/libafl/libarchive$ ./libarchive-afl.py -h
usage: libarchive-afl.py [-h] {init,init_all,build,build_all,run,list} ...

positional arguments:
  {init,init_all,build,build_all,run,list}
    init                initialize a target
    init_all            initialize all targets
    build               build a target
    build_all           build all targets
    run                 run a target
    list                list all targets

optional arguments:
  -h, --help            show this help message and exit
```

More examples can be seen in my [afl-scripts](https://github.com/gsingh93/afl-scripts) repo. See the source for full function signatures and all available methods.

## Why

I kept rewriting scripts for compiling/running binaries with AFL, and the number of configurations I wanted to compile with kept increasing (32 bit/64 bit versions, ASAN/no ASAN, gcov instrumentation, no AFL instrumentation, etc.).

This library is an attempt to remove the boiler plate from writing AFL fuzzing scripts, which will make it easier to test different configurations, and save these configurations for later use, or for sharing with others.
