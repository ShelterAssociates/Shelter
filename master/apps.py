#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Apps Page for master app"""

from django.apps import AppConfig


class MasterAppConfig(AppConfig):
    """Used for app configuration"""

    name = 'master'

    def ready(self):
        """Imports the signals file into django.apps"""
        import master.signals
            