#!/usr/bin/env python2

import argparse
import os
import subprocess
import logging
import pexpect

logging.basicConfig()
logger = logging.getLogger('libafl')
logger.setLevel(logging.INFO)

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

    run_parser = subparsers.add_parser('list', help='list all targets')

    return parser.parse_args()

def handle_args(project):
    check()
    args = parse_args()
    if args.command == 'init':
        project.init(args.target)
    elif args.command == 'init_all':
        project.init_all()
    elif args.command == 'build':
        project.build(args.target)
    elif args.command == 'build_all':
        project.build_all()
    elif args.command == 'run':
        project.run(args.target)
    elif args.command == 'list':
        for name in project.targets.iterkeys():
            print name

def check():
    '''Check if afl-fuzz is on the PATH and AFL_PATH is set'''
    pass

def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True)
    except Exception as e:
        print e.output
        raise e

def popen(cmd):
    try:
        return subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print e.output
        raise e

class AflProject(object):
    targets = {}

    def __init__(self, wrapper=None):
        self.wrapper = wrapper

    def run_in_dir(self, target, func):
        cwd = os.getcwd()
        os.chdir(target.path)
        func(target)
        os.chdir(cwd)

    def addTarget(self, name, target):
        self.targets[name] = target

    def build(self, name):
        if name in self.targets:
            target = self.targets[name]
            self.run_in_dir(target, lambda target: run_command(target.build()))
        else:
            raise Exception('Target %s does not exist' % name)

    def build_all(self):
        for name, target in self.targets.iteritems():
            logger.info('Building ' + name)
            self.run_in_dir(target, lambda target: run_command(target.build()))

    def run(self, name, wrapper=None, **kwargs):
        if wrapper == None:
            wrapper = self.wrapper

        logger.info('Running ' + name)
        if name in self.targets:
            cmd = self.targets[name].run(**kwargs)
            logger.info("Running cmd: " + cmd)
            if wrapper != None:
                wrapper.run(cmd)
            else:
                p = pexpect.spawn(cmd, dimensions=(100, 100))
                p.interact()
        else:
            raise Exception('Target %s does not exist' % name)

class Target(object):
    def set_afl_envs(self, cc=None, cxx=None, asan=False, msan=False, harden=True, optimize=True, cflags='', ldflags=''):
        if asan and msan:
            raise Exception('ASAN and MSAN can not be used together')

        result = ''
        if cc:
            result += 'CC=%s ' % cc
        if cxx:
            result += 'CXX=%s ' % cxx
        if asan:
            result += 'AFL_USE_ASAN=1 '
        if msan:
            result += 'AFL_USE_MSAN=1 '
        if harden:
            result += 'AFL_HARDEN=1 '
        if not optimize:
            result += 'AFL_DONT_OPTIMZE=1 '
        if cflags:
            result += 'CFLAGS=%s ' % cflags
        if ldflags:
            result += 'LDFLAGS=%s ' % ldflags

        return result.strip()

    def get(self):
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

        if master is not None and slave is not None:
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

class Tmux:
    def run(self, cmd):
        popen('tmux new-window "%s; bash -i"' % cmd)
        run_command('tmux last-window')
