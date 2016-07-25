libafl
======

A library for compiling binaries and running them from python code. This library is not for fuzzing python code.

# Installation

```
pip install libafl
```

# Usage

TODO

# Why

I kept rewriting scripts for compiling/running binaries with AFL, and the number of configurations I wanted to compile with kept increasing (32 bit/64 bit versions, ASAN/no ASAN, gcov instrumentation, no AFL instrumentation, etc.).

This library is an attempt to remove the boiler plate from writing AFL fuzzing scripts, which will make it easier to test different configurations, and save these configurations for later use, or for sharing with others.
