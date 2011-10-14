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

import libxml2
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ClustatParser(object):

    def __init__(self, xml, groupNames=None):
        self._xml = xml
        self._groupNames = groupNames
        self._tree = libxml2.parseDoc(self._xml)
        self._context = self._tree.xpathNewContext()
        self._localNode = [attr.content for attr in
                self._context.xpathEval('//clustat/nodes/node[@local=1]/@name')][0]
        if self._groupNames is None or len(self._groupNames) < 1:
            self._parseGroupNames()

    def _parseGroupNames(self):
        self._groupNames = [attr.content for attr in
                self._context.xpathEval('//clustat/groups/group[@owner="%s"]/@name' % self._localNode)]

    def checkStatus(self, wantedStatus):

        if len(self._groupNames) < 1:
            return (1, "There are no cluster groups to check.")
        for groupName in self._groupNames:
            clusterStatus = [attr.content for attr in
                    self._context.xpathEval('//clustat/groups/group[@name="%s" and @owner="%s"]/@state_str' %
                        (groupName, self._localNode))]
            if len(clusterStatus) < 1:
                return (2, "Could not find cluster group: %s" % groupName)
            clusterStatus = clusterStatus[0]
            if wantedStatus != clusterStatus:
                return (3, "Cluster group %s returned state %s" %
                        (groupName, clusterStatus))
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
            usage="usage: %prog [options] [GROUP-NAME [GROUP-NAME [...]]]",
            description=desc
            )
    parser.add_option("-f", "--file", dest="filename",
            help="Read xml from file instead of clustat", metavar="FILE")
    parser.add_option("-e", "--executable", dest="executable",
            help="Specify path to executable (defaults to /usr/bin/clustat)",
            default="/usr/bin/clustat", metavar="EXECUTABLE")
    parser.add_option("-p", "--parameter", dest="parameter",
            help="What parameters to be passed to executable (defaults to -x)",
            action="append", metavar="PARAMETER")
    (options, arguments) = parser.parse_args()

    if not options.parameter:
            options.parameter = ['-x']

    if options.filename:
        stdout = open(options.filename).read()
    else:
        from subprocess import Popen, PIPE
        command = [options.executable]
        command.extend(options.parameter)
        readFrom = Popen(command, stdin=None, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = readFrom.communicate()

        if stderr:
            print >> sys.stderr, "Clustat returned the following error:\n%s" % stderr
            sys.exit(readFrom.exitcode)

    clustat = ClustatParser(stdout, arguments)
    (exitcode, out) = clustat.checkStatus('started')

    if (exitcode > 0):
        print >> sys.stderr, out

    sys.exit(exitcode)
