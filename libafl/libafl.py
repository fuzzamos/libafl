#!/usr/bin/env python2

from abc import ABCMeta, abstractmethod

import argparse
import logging
import os
import pexpect
import subprocess
import time

logging.basicConfig()
logger = logging.getLogger('libafl')

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    init_parser = subparsers.add_parser('init', help='initialize a target')
    init_parser.add_argument(
        'target',
        metavar='TARGET',
        help='the target to initialize',
    )

    subparsers.add_parser('init_all', help='initialize all targets')

    build_parser = subparsers.add_parser('build', help='build a target')
    build_parser.add_argument(
        'target',
        metavar='TARGET',
        help='the target to build',
    )

    subparsers.add_parser('build_all', help='build all targets')

    run_parser = subparsers.add_parser('run', help='run a target')
    run_parser.add_argument(
        'target',
        metavar='TARGET',
        help='the target to run',
    )
    run_parser.add_argument(
        '--master',
        action='store_true',
        help='run this fuzzer as the master',
    )

    run_parser.add_argument(
        '--slave',
        metavar='N',
        help='run N slave fuzzers',
    )

    run_parser = subparsers.add_parser('list', help='list all targets')

    return parser.parse_args()

def handle_args(project):
    check()
    args = parse_args()

    try:
        if args.command == 'init':
            project.init(args.target)
        elif args.command == 'init_all':
            project.init_all()
        elif args.command == 'build':
            project.build(args.target)
        elif args.command == 'build_all':
            project.build_all()
        elif args.command == 'run':
            project.run(
                args.target,
                **{'master': args.master, 'slave': args.slave})
        elif args.command == 'list':
            for name in project.targets.iterkeys():
                print name
    except subprocess.CalledProcessError as e:
        print e.output
        raise e

def check():
    '''Check if afl-fuzz is on the PATH'''
    binary = which('afl-fuzz')
    if binary == None:
        raise Exception('Could not find afl-fuzz binary, update your PATH')
    else:
        logger.info('Using ' + binary)

def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

class AflProject(object):
    targets = {}

    def __init__(self, wrapper=None):
        self.wrapper = wrapper

    def run_in_dir(self, target, path, func):
        cwd = os.getcwd()
        os.chdir(path)
        func(target)
        os.chdir(cwd)

    def addTarget(self, name, target):
        self.targets[name] = target

    def init(self, name):
        if name in self.targets:
            logger.info('Intializing ' + name)
            target = self.targets[name]
            self.init_target(target)
        else:
            raise Exception('Target %s does not exist' % name)

    def init_all(self):
        for name, target in self.targets.iteritems():
            logger.info('Intializing ' + name)
            self.init_target(target)

    def init_target(self, target):
        self.run_in_dir(
            target,
            target.root_path,
            lambda target: target.init(),
        )

    def build(self, name):
        if name in self.targets:
            logger.info('Building ' + name)
            target = self.targets[name]
            self.build_target(target)
        else:
            raise Exception('Target %s does not exist' % name)

    def build_all(self):
        for name, target in self.targets.iteritems():
            logger.info('Building ' + name)
            self.build_target(target)

    def build_target(self, target):
        path = os.path.join(target.root_path, target.src_dir)
        self.run_in_dir(
            target,
            path,
            lambda target: target.build(),
        )

    def run(self, name, wrapper=None, **kwargs):
        cwd = os.getcwd()

        if wrapper == None:
            wrapper = self.wrapper

        logger.info('Running ' + name)
        if name in self.targets:
            target = self.targets[name]
            os.chdir(target.root_path)
            cmd = target.run(**kwargs)
            logger.info("Running cmd: " + cmd)
            if wrapper != None:
                wrapper.run(cmd)
            else:
                p = pexpect.spawn(cmd, dimensions=(100, 100))
                p.interact()
        else:
            os.chdir(cwd)
            raise Exception('Target %s does not exist' % name)

        os.chdir(cwd)

class Target(object):
    __metaclass__ = ABCMeta

    def set_afl_envs(self, cc=None, cxx=None, asan=False, msan=False, harden=True, optimize=True, cflags=None, ldflags=None):
        if asan and msan:
            raise Exception('ASAN and MSAN can not be used together')

        result = {}
        if cc:
            result['CC'] = cc
        if cxx:
            result['CXX'] = cxx
        if asan:
            result['AFL_USE_ASAN'] = '1'
        if msan:
            result['AFL_USE_MSAN'] = '1'
        if harden:
            result['AFL_HARDEN'] = '1'
        if not optimize:
            result['AFL_DONT_OPTIMIZE'] = '1'
        if cflags:
            result['CFLAGS'] = cflags
        if ldflags:
            result['LDFLAGS'] = ldflags

        return result

    def init(self):
        pass

    def build(self):
        pass

    def run(self):
        pass

class AflTarget(Target):
    def __init__(self, input_dir, output_dir, binary, binary_args, afl_args=''):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.binary = binary
        self.binary_args = binary_args
        self.afl_args = afl_args

    def run(self, **kwargs):
        if not os.path.exists(self.input_dir):
            os.mkdir(self.input_dir)
            print 'Put a test case in "%s"' % self.input_dir
            exit(1)

        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        master = kwargs.get('master')
        slave = kwargs.get('slave')

        if master and slave is not None:
            raise Exception('Master and slave flag can not be used together')

        fuzzer_name = os.path.basename(self.binary)
        if master:
            fuzzer_name += '0'
            self.afl_args += ' -M ' + fuzzer_name
        elif slave:
            fuzzer_name += str(slave)
            self.afl_args += ' -S ' + fuzzer_name

        return (
            'afl-fuzz -T %s -i %s -o %s %s %s %s' %
            (fuzzer_name, self.input_dir, self.output_dir, self.afl_args,
             self.binary, self.binary_args)
        )

class Wrapper:
    __metaclass__ = ABCMeta

    @abstractmethod
    def run():
        pass

class TmuxWrapper(Wrapper):
    def run(self, cmd):
        subprocess.Popen('tmux new-window "%s; bash -i"' % cmd, shell=True)
        time.sleep(0.5)
        subprocess.check_output(['tmux', 'last-window'])
