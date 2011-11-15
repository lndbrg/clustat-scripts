#! /usr/bin/python2
#
# Copyright (C) 2011  Red Hat
#
# Author: Olle Lunderg (olle@redhat.com)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
'''
This module provides interaces for wortking with clustat.
'''
import libxml2
import sys

class ClustatParser(object):
    '''
    A class that makes it easier to work with the output of clustat.
    '''

    def __init__(self, xml, groupnames = None):
        """ A class that makes it easier to work with the output of clustat
        @type xml: string
        @type groupnames: list or none
        """
        self._xml = xml
        self._groupnames = groupnames
        self._tree = libxml2.parseDoc(self._xml)
        self._context = self._tree.xpathNewContext()
        self._localnode, _ = self._xpath('//clustat/nodes/node[@local=1]/@name')
        if self._groupnames is None or len(self._groupnames) < 1:
            self._parsegroupnames()

    def _xpath(self, expression):
        """Takes an xpath expression and executes it on the current context
        @type expression: string
        @return: list
        """
        return [ attr.content for attr in self._context.xpathEval(expression) ]

    def _parsegroupnames(self):
        """Parses all cluster groups from the prvided clustat xml"""
        self._groupnames = self._xpath(
                '//clustat/groups/group[@owner="%s"]/@name' % self._localnode
                )

    def checkstatus(self, wantedstatus):
        """Checks that the output of clustat corresponds with the wanted
        status.
        @type wantedstatus: string
        @return: Tuple(int, string)
        """
        if len(self._groupnames) < 1:
            return (1, "There are no cluster groups to check.")
        for groupname in self._groupnames:
            clusterstatus = self._xpath(
                    '//clustat/groups/group[@name="%s" and @owner="%s"]' \
                            '/@state_str' % (groupname, self._localnode)
                    )
            if len(clusterstatus) < 1:
                return (2, "Could not find cluster group: %s" % groupname)
            clusterstatus = clusterstatus[0]
            if wantedstatus != clusterstatus:
                return (3, "Cluster group %s returned state %s" %
                        (groupname, clusterstatus))
        return (0, "Everything went better than expected!")


if __name__ == '__main__':
    from optparse import OptionParser
    desc = """This script acts as a safe guard against running
cron jobs on non functional clusters (e.g state is not 'started').
If you do not pass any group names the script parses the cluster
group names from the output of clustat.
The script only checks the services that has the local cluster node as an
owner. If the script can not find the service specified it is considered an
error. If the script can not find any services it is considered an error.
If the script encounters a service not in state 'started' it is considered an
error.
If the script encounters any errors it returns an exit code above 0."""
    parser = OptionParser(
            usage = "usage: %prog [options] [GROUP-NAME [GROUP-NAME [...]]]",
            description = desc
            )
    parser.add_option("-f", "--file", dest = "filename",
            help = "Read xml from file instead of clustat", metavar = "FILE")
    parser.add_option("-e", "--executable", dest = "executable",
            help = "Specify path to executable (defaults to /usr/bin/clustat)",
            default = "/usr/bin/clustat", metavar = "EXECUTABLE")
    parser.add_option("-p", "--parameter", dest = "parameter",
            help = "What parameters to be passed to executable" \
            "(defaults to -x)",
            action = "append", metavar = "PARAMETER")
    (options, arguments) = parser.parse_args()

    if not options.parameter:
        options.parameter = ['-x']

    if options.filename:
        stdout = open(options.filename).read()
    else:
        from subprocess import Popen, PIPE
        command = [options.executable]
        command.extend(options.parameter)
        readfrom = Popen(command, stdin = None, stdout = PIPE, stderr = PIPE)
        (stdout, stderr) = readfrom.communicate()

        if stderr or readfrom.returncode:
            print >> sys.stderr, "Clustat returned the following error:\n%s" \
                    % stderr
            sys.exit(readfrom.returncode)

    clustat = ClustatParser(stdout, arguments)
    (exitcode, out) = clustat.checkstatus('started')

    if (exitcode > 0):
        print >> sys.stderr, out

    sys.exit(exitcode)
