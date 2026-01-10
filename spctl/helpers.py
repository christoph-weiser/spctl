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

import os
import re
import subprocess


def create_netlist(schematic, outputdir, xschemrc):
    """ Create a spice netlist from xschem schematic.

    Required inputs:
    ----------------
    schematic (str):        Path to schematic file.
    outputdir (str):        Path where output is generated.
    xschemrc  (str):        Path to xschemrc config file.


    Returns
    ----------------
    netlist_file (str):     Location of the spice netlist
    """
    pwd = os.getcwd()
    rc_location = "/".join(xschemrc.split("/")[:-1])
    os.chdir(rc_location)
    if outputdir == ".":
        outputdir = pwd
    p = subprocess.Popen(["xschem", "-x", "-n", "-q", schematic,
                          "-o", outputdir, "--tcl", "set cmdline_ignore true; set dummy_ignore true",
                          "--rcfile", xschemrc])
    (output, err) = p.communicate()
    p_status = p.wait()
    os.chdir(pwd)
    netlist_name = os.path.basename(schematic).replace(".sch", ".spice")
    netlist_file = outputdir + "/" + netlist_name
    return netlist_file


def parse_configuration(filename):
    """ Parse custom configuration file format.

    Required inputs:
    ----------------
    filename (str):         path to the configuration file.

    Returns
    ----------------
    configuration (dict): Dictionary holding information
                          about the simulation runs evals etc.

    Description
    ----------------
    The custom format look like this:

        :corner
            tt
            ss
            ff
        :temperature
            -20
            27
            85
        :vdd(list, vsource)
            1,2,3
        :mypar(list, param)
            1
            2
            3
        :myextpar(csv, file.txt, param)
            1
            2
            3

    """
    with open(filename, "r") as infile:
        raw = infile.read()
        raw = raw.split("\n")
        data = []
        for line in raw:
            if not re.match(r"\s*#|^\s*$", line):
                data.append(line)
    conf = dict()
    # par: parameter to change
    # t:   specification type: list, csv, str
    # st:  spice type: parameter, voltage source etc.
    for line in data:
        if line[0] == ":":
            par, t, st, path = eval_par_def(line)
            conf[par] = [st, t, path]
            if conf[par][1] == "csv":
                with open(path, "r") as ifile:
                    elements = ifile.read().splitlines()
                conf[par][1] = elements
        else:
            if conf[par][1] in ["list", "corner", "temperature"] or isinstance(conf[par][1], list):
                if conf[par][1] == "list":
                    conf[par][1] = list()
                line = line.strip()
                if "," in line:
                    elements = line.split(",")
                else:
                    elements = [line]
                for elem in elements:
                    conf[par][1].append(elem)
            elif conf[par][1] == "str":
                conf[par][1] = elem
            else:
                raise Exception("specification type not supported")
    return conf


def eval_par_def(line):
    line = line[1:].strip()
    # Defaults
    st = line
    t = "list"
    par = line
    path = None
    # Case when defaults does not apply
    if line not in ["temperature", "corner"]:
        line = line.replace(" ", "") 
        s = line.split("(")
        s[-1] = s[-1].replace(")", "")
        par = s[0]
        spec = s[1].split(",")
        if len(spec) == 2:  # normal
            t = spec[0]
            st = spec[1]
        elif len(spec) == 3: # csv 
            t = spec[0]
            path = spec[1] 
            st = spec[2]
    return par, t, st, path


def path_setup(filename, cwd,  identifier):
    """ Generate names, filepaths etc. for regression test.

    Required inputs:
    ----------------
    filename (str):     .conf file holding simulation details.
    indentifier (str):  unique identifier for result file
    cwd (str):          current working directory


    Returns
    ----------------
    dict {
    name (str):         overall name of the testsetup
    file_sch (str):     file location of the schematic
    file_conf (str):    file location of the test config
    file_res (str):     file location of the result file
    }


    Description
    ----------------
    This function prepares all the variables required to run
    a regression test. It works based on the predefined structure
    that is assumed when building up regession tests.
    This structure likes like this:
    .
    ├── tb_name.sch
    └── tests
        ├── tb_name.conf
        └── results
            └── tb_name_0000000000
                ├── data
                ├── netlists
                │   ├── overview.txt
                │   └── tb_name.spice
                └── summary.csv

    """
    name = os.path.basename(filename).replace(".conf", "")
    name_sch  = name + ".sch"
    name_conf = name + ".conf"
    file_sch  = os.path.dirname(cwd) + "/" + name_sch
    file_conf = cwd + "/" + name_conf
    path_res  = cwd + "/" + "results"
    path_run  = "{}/{}_{}".format(path_res, name, identifier)
    file_sum  = "{}/summary.csv".format(path_run)
    path_net  = "{}/netlists".format(path_run)
    path_dat  = "{}/data".format(path_run)
    file_ovr  = "{}/overview.txt".format(path_net)
    if not os.path.isdir(path_res):
        os.mkdir(path_res)
    if not os.path.isdir(path_run):
        os.mkdir(path_run)
    if not os.path.isdir(path_net):
        os.mkdir(path_net)
    if not os.path.isdir(path_dat):
        os.mkdir(path_dat)
    return {"path_results":       path_res,
            "path_run":           path_run,
            "path_netlists":      path_net,
            "path_data":          path_dat,
            "file_schematic":     file_sch, 
            "file_config":        file_conf, 
            "file_summary":       file_sum, 
            "file_overview":      file_ovr, 
            }


def latest_testresult(filename, location):
    """ Return the latest testresult

    Required inputs:
    ----------------
    filename (str): current file. typically __file__
    location (str): current working directory.


    Returns
    ----------------
    latest (str):       path to the latest result file.


    Description
    ----------------
    This is a helper function to the pytest setup.
    This should be called from a analysis script to get the
    latest result from a results location.
    This assumes a system, where the files are named with a
    timestamp, such that sorting them results in a orderly list.

    """
    path_results = os.path.abspath("{}/../results".format(location))
    name_file = os.path.basename(filename).replace(".py", "")
    folders = sorted(os.listdir(path_results))
    matches = []
    for f in folders:
        if re.match(r"^{}_\d*$".format(name_file), f):
            matches.append(f)
    try:
        latest = sorted(matches)[-1]
    except IndexError:
        raise Exception("No files match the current analysis")
    return path_results + "/" + latest + "/" + "summary.csv"
