########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import sys
from ConfigParser import ConfigParser

from cloudify import ctx
# from cloudify.workflows import ctx as workflows_ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

# from cloudify.proxy.client import CTX_SOCKET_URL
# from cloudify.proxy.server import (UnixCtxProxy,
#                                    TCPCtxProxy,
#                                    HTTPCtxProxy,
#                                    StubCtxProxy)

"""
# cloudify.interfaces.logging:
    # configure:
        # implementation: logging.beaver.tasks.configure
        # inputs:
            # [files] to monitor
            # {output_config} for the node.
            # {beaver_config} the general bevear config set by the user.
    # start:
        # implementation: logging.beaver.tasks.start
        # inputs:
            # 'beaver_config_path' allows to pass an arbitrary config file.
            # [additional_arguments] to pass to the cli when executing.
    # stop:
        # implementation: logging.beaver.tasks.stop
    # delete:
        # implementation: logging.beaver.tasks.delete
"""

IS_WINDOWS = os.name == 'nt'


@operation
def configure(output_config, files=None, path=None, beaver_config=None,
              beaver_config_file_path=None, validate=False, **kwargs):
    """Generates configuration for the beaver process.

    :params string files: A list of files to monitor.
    :params dict output_config: A configuration of a beaver output.
    :params dict beaver_config: General beaver level config.
    """
    ctx.logger.info('Generating beaver config....')
    configurator = BeaverConfigurator(
        output_config, files, path, beaver_config, beaver_config_file_path)
    configurator.validate_config()
    configurator.set_main_config()
    configurator.set_additional_config()
    configurator.set_output()
    if path:
        configurator.set_path()
    if files:
        configurator.set_files()
    configurator.write_config_file()


@operation
def start(additional_arguments=None, daemonize=True,
          **kwargs):
    """Starts the beaver process.

    :params string beaver_config_path: A blueprint relative path to a user
     supplied beaver config file.
    :params list additional_arguments: A list of additional arguments to pass
     to beaver's commandline.
    :params bool daemonize: whether to run the process as a daemon.
    """
    config_path = ctx.instance.runtime_properties.get(
        'beaver_config_file_path')
    ctx.logger.info('Starting beaver with config file: {0} and arguments: '
                    '{1}'.format(config_path, additional_arguments))


@operation
def stop(**kwargs):
    """Stops the beaver process.
    """
    pass


@operation
def delete(**kwargs):
    """Deletes the beaver configuration.
    """
    pass


class BeaverConfigurator:
    def __init__(self, output_config, files, path, beaver_config,
                 beaver_config_file_path):
        self.output_config = output_config
        self.files = files
        self.path = path
        self.beaver_config = beaver_config
        self.beaver_config_file_path = beaver_config_file_path
        self.conf = ConfigParser()

    def validate_config(self):
        if self.files:
            if not isinstance(self.files, list):
                raise NonRecoverableError('`files` must be of type list.')
            if len(self.files) < 1:
                raise NonRecoverableError('`files` must contain a path to at '
                                          'least one file.')
        if self.path:
            if not isinstance(self.path, str):
                raise NonRecoverableError('`path` must be of type string.')
        if not self.files and not self.path:
            raise NonRecoverableError(
                'You must either supply `path` or `files` to collect from.')

        if not isinstance(self.output_config, dict):
            raise NonRecoverableError('`output_config` must be of type dict.')

        if self.beaver_config and self.beaver_config_file_path:
            raise NonRecoverableError(
                'Please provide either a beaver config or a config file path.')

    def set_main_config(self):
        self.conf.add_section('beaver')
        self.conf.set('logstash_version', '1')

    def set_files(self):
        files = ','.join(self.files)
        self.conf.set('beaver', 'files', files)

    def set_output(self):
        self._write_config_dict(self.output_config)

    def set_path(self):
        self.conf.set('beaver', 'path', self.path)

    def set_additional_config(self):
        self._write_config_dict(self.beaver_config)

    def _write_config_dict(self, config):
        for key, value in config.items():
            self.conf.set('beaver', key, value)

    def write_config_file(self):
        if IS_WINDOWS:
            config_dir = os.path.join(sys.executable[0], 'beaver')
        else:
            config_dir = os.path.join('/', 'etc', 'beaver')
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError as ex:
                raise NonRecoverableError(
                    'Could not create dir {0} ({1})'.format(
                        config_dir, str(ex)))
        filepath = os.path.join(config_dir, ctx.node.id)
        with open(filepath, 'w') as f:
            self.conf.write(f)
