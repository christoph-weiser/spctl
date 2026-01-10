# SPCTL - Spice Control
# Copyright (C) 2026 Christoph Weiser
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import datetime
import subprocess
import spatk


class ControlSection():
    """ Ngspice control section from file or string. """
    def __init__(self, netlist, is_filename=True):
        if is_filename:
            with open(netlist, "r") as ifile:
                self._netlist = ifile.read()
        else:
            self._netlist = netlist
        self._netlist = extract_control(self._netlist, as_str=False)

    def __str__(self):
        return self.netlist

    def __add__(self, other):
        return self.netlist + str(other)

    @property
    def lines(self):
        """ Lines of control section netlist """
        return self._netlist

    @lines.setter
    def lines(self, arg):
        if isinstance(arg, str):
            self._netlist = arg.split("\n")
        elif isinstance(arg, list): 
            self._netlist = arg
        else:
            raise Exception("control list must be str or list")

    @property
    def netlist(self):
        """ Simulation ready circuit netlist """
        return "\n".join(self._netlist)

    def write(self, filename):
        """ Write the control netlist to file

        Required inputs:
        ----------------
        filename (str):     Name of the output file.
        """
        with open(filename, "w") as ofile:
            ofile.write("* Netlist written: {}\n".format(datetime.datetime.now()))
            ofile.write(self.netlist)


class CircuitSection(spatk.Circuit):
    """ CircuitSection represents a spice netlist.

    Required inputs:
    ----------------
    netlist  (str):     spice netlist or path to a spice netlist.


    Optional inputs:
    ----------------
    is_netlist (bool):  Indicator if netlist is a filepath or actual netlist.
                        Default assumes a path.

    Description
    ----------------
    The Circuit section is a high-level object of any ordinary spice netlist.
    The object allows however to filter the netlist elements by their type
    arguments and ports.

        filename:       When read from file filename, otherwise this can be
                        used a identfier and will be writen to the first line
                        of the netlist object.

        parsed_circuit: This variable holds a string with the original netlist
                        even before variable subsitution.


        circuit:        A list of all the netlist elements in a dict fashion
                        with "instance", "type",  "ports",  "args" keys.

        netlist:        A spice netlist generated from the "circuit" list/dict.
    """

    def __init__(self, *args, **kwargs):
        super(CircuitSection, self).__init__(*args, **kwargs)


def extract_control(netlist, skip_plots=True, as_str=True):
    """ Extract control section from a xschem exported netlist.

    Required inputs:
    ----------------
    netlist (str, list):    Spice netlist from which to extract
                            the circuit information.

    Optional inputs:
    ----------------
    skip_plots (bool):      Skip plot statements.
    as_str (bool):          Return netlist as string or otherwise
                            as a list.

    Returns
    ----------------
    netlist_extract (list): List of lines containing control section
                            elements.
    """
    if isinstance(netlist, str):
        netlist = netlist.split("\n")
    inside_control_code = False
    netlist_extract = []
    for line in netlist:
        if re.match(r"\.control", line):
            inside_control_code = True
        if inside_control_code:
            if skip_plots:
                if not re.match("^plot.*|^gnuplot.*", line):
                    netlist_extract.append(line)
            else:
                netlist_extract.append(line)
        if re.match(".endc", line):
            inside_control_code = False
    if as_str:
        netlist_extract = "\n".join(netlist_extract)

    return netlist_extract


def extract_output_data(output):
    """ Extract results from ngspice output.

    Required inputs:
    ----------------
    output (list):      ngspice output

    Returns
    ----------------
    resutls (dict):     pairs of variable name and value
    """
    results = {}
    for line in output:
        if re.match(".* = .*", line):
            var = line.split("=")[0].strip()
            val = line.split("=")[-1].strip()
            if not var == "Doing analysis at TEMP":
                results[var] = float(val)
    return results


def run_simulation(netlist):
#     """ Run a spice netlist with ngspice

#     Required inputs:
#     ----------------
#     netlist(str, list):     netlist to be run


#     Returns
#     ----------------
#     output(list):           list of strings with the output
#                             generated by ngpsice.
#     """
    command = ["ngspice", "-b", netlist]
    result = subprocess.run(
        command, 
        capture_output=True, 
        text=True, 
        check=False )
    return (result.stdout.splitlines(), result.stderr.splitlines())
