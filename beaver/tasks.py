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
from ConfigParser import ConfigParser
import tempfile

from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


"""
# cloudify.interfaces.logging:
    # configure:
        # implementation: logging.beaver.tasks.configure
        # inputs:
            # 'beaver_config_path' allows to pass an arbitrary config file.
            # [files] to monitor
            # {output_config} for the node.
            # {beaver_config} the general bevear config set by the user.
    # start:
        # implementation: logging.beaver.tasks.start
        # inputs:
            # [additional_arguments] to pass to the cli when executing.
            # daemonize beaver
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
    destination_config_path = _set_beaver_config_path(ctx.node.id)
    if beaver_config_file_path:
        ctx.download_resource(beaver_config_file_path, destination_config_path)
    else:
        configurator = BeaverConfigurator(
            output_config, files, path, beaver_config, beaver_config_file_path)
        configurator.set_main_config()
        configurator.set_output()
        configurator.set_monitored_paths()
        configurator.set_additional_config()
        configurator.write_config_file(destination_config_path)
    ctx.instance.runtime_properties['config_file'] = destination_config_path


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
    config_file = ctx.instance.runtime_properties.get(
        'beaver_config_file_path')
    if config_file:
        ctx.download_resource(config_file, '')
    ctx.logger.info('Starting beaver with config file: {0} and arguments: '
                    '{1}'.format(config_file, additional_arguments))
    beaver_cmd = ['beaver', '-c', config_file]
    if additional_arguments and not isinstance(additional_arguments, list):
        raise NonRecoverableError(
            '`additional_arguments` must be of type list.')
    beaver_cmd.extend(additional_arguments)
    if daemonize:
        beaver_cmd.append('-d')


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
        self.monitored_files = files
        self.monitored_path = path
        self.beaver_config = beaver_config
        self.beaver_config_file_path = beaver_config_file_path
        self._validate_config()
        self.conf = ConfigParser()

    def _validate_config(self):
        if self.monitored_path:
            if not isinstance(self.monitored_path, str):
                raise NonRecoverableError('`path` must be of type string.')
        if self.monitored_files:
            if not isinstance(self.monitored_files, list):
                raise NonRecoverableError('`files` must be of type list.')
            if len(self.monitored_files) < 1:
                raise NonRecoverableError('`files` must contain a path to at '
                                          'least one file.')
        if not self.monitored_files and not self.monitored_path:
            raise NonRecoverableError(
                'You must either supply `path` or `files` to collect from.')

        if not isinstance(self.output_config, dict):
            raise NonRecoverableError('`output_config` must be of type dict.')

        if self.beaver_config and self.beaver_config_file_path:
            raise NonRecoverableError(
                'Please provide either a beaver config or a config file path.')

    def set_main_config(self):
        self.conf.add_section('beaver')
        self._write('logstash_version', '1')

    def set_monitored_paths(self):
        if self.monitored_files:
            files = ','.join(self.monitored_files)
            self._write('files', files)
        if self.monitored_path:
            self._write('path', self.monitored_path)

    def set_output(self):
        self._write_dict(self.output_config)

    def set_additional_config(self):
        self._write_dict(self.beaver_config)

    def _write(self, key, value):
        self.conf.set('beaver', key, value)

    def _write_dict(self, config):
        for key, value in config.items():
            self._write(key, value)

    def write_config_file(self, destination_config_path):
        with open(destination_config_path, 'w') as f:
            self.conf.write(f)


def _set_beaver_config_path(node_id):
    if os.environ.get('CELERY_WORK_DIR'):
        prefix = os.path.split(os.environ.get('CELERY_WORK_DIR'))[0]
        config_dir = os.path.join(prefix, 'beaver')
    else:
        config_dir = tempfile.mkdtemp(prefix='cloudify-monitoring-')

    if not os.path.isdir(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError as ex:
            raise NonRecoverableError(
                'Could not create dir {0} ({1})'.format(
                    config_dir, str(ex)))
    return os.path.join(config_dir, 'beaver-{0}.conf'.format(node_id))
