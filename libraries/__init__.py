#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper - Add this folder to Python search path for libraries loading."""


def initialize():
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))


initialize()
