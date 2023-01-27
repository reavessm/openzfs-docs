#!/usr/bin/env python3
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2020 George Melikov <mail@gmelikov.ru>
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import logging
import os
import re
import subprocess
import sys

LOG = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

zfs_repo_url = 'https://github.com/openzfs/zfs/'

man_sections = {
    '1': 'User Commands',
    '2': 'System Calls',
    '3': 'C Library Functions',
    '4': 'Devices and Special Files',
    '5': 'File Formats and Conventions',
    '6': 'Games',
    '7': 'Miscellaneous',
    '8': 'System Administration Commands',
}

man_section_dir = 'man'
man_section_name = 'Man Pages'

build_dir = '_build/man'

regex_template = ('<a(?P<href_place> )class=\"Xr\"(?P<title>.*?)>%s'
                  '\((?P<num>[1-9])\)<\/a>')
final_regex = ('<a href="../\g<num>/\g<name>.\g<num>.html" class="Xr"'
               '>\g<name>(\g<num>)</a>')


def add_hyperlinks(out_dir, pages):
    all_pages = []
    for _section, section_pages in pages.items():
        all_pages.extend([
            os.path.splitext(page)[0] for page in section_pages])
    tmp_regex = '(?P<name>' + "|".join(all_pages) + ')'
    html_regex = re.compile(regex_template % tmp_regex, flags=re.MULTILINE)

    for section, pages in pages.items():
        for page in pages:
            file_path = os.path.join(
                out_dir, build_dir, 'man' + section, page + '.html')
            with open(file_path, "r") as f:
                text = f.read()
            new_text = re.sub(html_regex, final_regex, text)
            if text != new_text:
                with open(file_path, "w") as f:
                    LOG.debug('Crosslinks detected in %s, generate',
                              file_path)
                    text = f.write(new_text)


def run(in_dir, out_dir):
    pages = {num: [] for num in man_sections}
    for subdir, dirs, _ in os.walk(in_dir):
        for section in dirs:
            section_num = section.replace('man', '')
            section_suffix = '.' + section_num
            if section_num not in man_sections:
                continue
            out_section_dir = os.path.join(out_dir, build_dir, section)
            os.makedirs(out_section_dir, exist_ok=True)
            for page in os.listdir(os.path.join(subdir, section)):
                if not (page.endswith(section_suffix) or
                        page.endswith(section_suffix + '.in')):
                    continue
                LOG.debug('Generate %s page', page)
                stripped_page = page.rstrip('.in')
                page_file = os.path.join(out_section_dir,
                                         stripped_page + '.html')
                with open(page_file, "w") as f:
                    subprocess.run(
                        ['mandoc', '-T', 'html', '-O', 'fragment',
                         os.path.join(subdir, section, page)], stdout=f,
                        check=True)

                pages[section_num].append(stripped_page)
        break

    man_path = os.path.join(out_dir, man_section_dir)
    os.makedirs(man_path, exist_ok=True)
    with open(os.path.join(man_path, 'index.rst'), "w") as f:
        f.write(
            """.. THIS FILE IS AUTOGENERATED, DO NOT EDIT!

:github_url: {zfs_repo_url}blob/master/man/

{name}
{name_sub}
.. toctree::
    :maxdepth: 1
    :glob:

    */index
            """.format(zfs_repo_url=zfs_repo_url,
                       name=man_section_name,
                       name_sub="=" * len(man_section_name))
        )

    for section_num, section_pages in pages.items():
        if not section_pages:
            continue
        rst_dir = os.path.join(out_dir, man_section_dir, section_num)
        os.makedirs(rst_dir, exist_ok=True)
        section_name = man_sections[section_num]
        section_name_with_num = '{name} ({num})'.format(
            name=section_name, num=section_num)
        with open(os.path.join(rst_dir, 'index.rst'), "w") as f:
            f.write(
                """.. THIS FILE IS AUTOGENERATED, DO NOT EDIT!

:github_url: {zfs_repo_url}blob/master/man/man{section_num}/

{name}
{name_sub}
.. toctree::
    :maxdepth: 1
    :glob:

    *
                """.format(zfs_repo_url=zfs_repo_url,
                           section_num=section_num,
                           name=section_name_with_num,
                           name_sub="=" * len(section_name_with_num),)
            )
        for page in section_pages:
            with open(os.path.join(rst_dir, page + '.rst'), "w") as f:
                f.write(
                    """.. THIS FILE IS AUTOGENERATED, DO NOT EDIT!

:github_url: {zfs_repo_url}blob/master/man/man{section_num}/{name}

{name}
{name_sub}
.. raw:: html

   <div class="man_container">

.. raw:: html
   :file: ../../{build_dir}/man{section_num}/{name}.html

.. raw:: html

   </div>
                    """.format(zfs_repo_url=zfs_repo_url,
                               name=page,
                               build_dir=build_dir,
                               section_num=section_num,
                               name_sub="=" * len(page))
                )
    add_hyperlinks(out_dir, pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('man_dir',
                        help='Man pages dir')
    parser.add_argument('out_dir',
                        help='Sphinx docs dir')
    args = parser.parse_args()

    run(args.man_dir, args.out_dir)


if __name__ == '__main__':
    main()
