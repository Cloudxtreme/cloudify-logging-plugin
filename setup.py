#########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.


from setuptools import setup

setup(
    name='cloudify-logging-plugin',
    version='1.3a7',
    author='Gigaspaces',
    author_email='cloudify@gigaspaces.com',
    packages=['shipper'],
    description='Plugin for handling logs',
    install_requires=[
        'cloudify-plugins-common>=3.3a7'
    ],
    license='LICENSE'
)
