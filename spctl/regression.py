# SPCTl - Spice Control
# Copyright (C) 2022 Christoph Weiser
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
import time
import uuid
import itertools
import logging
import spctl

from filelock import FileLock


def create_cases(configfile):
    config = spctl.parse_configuration(configfile)
    cases = [config[x][1] for x in config]
    casekeys = tuple(config.keys())
    casetype = [x[0] for x in config.values()]
    cases_permut = list(itertools.product(*cases))
    cases_permut = [(casekeys, casetype,x) for x in cases_permut]
    return cases_permut, casekeys


def setup(configfile):
    cwd = os.getcwd()
    logtime = str(time.time()).split(".")[0]

    paths = spctl.path_setup(configfile, cwd, logtime)
    cases, casekeys = create_cases(paths["file_config"])

    with open(paths["file_overview"], "w") as ofile: 
        ofile.write("netlist,{}\n".format(",".join(casekeys)))

    with open(paths["file_summary"], "w") as ofile:
        ofile.write("netlist,{},par,val\n".format(",".join(casekeys)))

    return cases, paths


def run_cases(paths, args, result_queue):

    logger = logging.getLogger()
    if not logger.handlers:
        logger.addHandler(QueueHandler(log_queue))
    logger.setLevel(logging.INFO)
    
    logger.info("--------------------")
    logger.info("Testcase")
    logger.info("--------------------")
    for par, val in zip(args[0], args[2]):
        logger.info("{:<14}: {}".format(par,val))

    # Load the circuit from file
    cir = spctl.CircuitSection(paths["file_netlist"])
    ctl = spctl.ControlSection(paths["file_netlist"])

    netlist_uuid = uuid.uuid4().hex

    lines = ctl.lines
    for i,line in enumerate(lines):
        # TODO: this only applies to ngspice
        if re.match("^wrdata", line):
            s = line.split(" ")
            s[1] = "{}/{}.csv".format(paths["path_data"], netlist_uuid)
            line =  " ".join(s)
            lines[i] = line
    ctl.lines = lines

    include = ""
    for par, st, val in zip(args[0], args[1], args[2]):
        if par == "corner":
            include = ".include {}/{}.spice\n".format(paths["path_corners"], val)
        elif par == "temperature":
            uids = cir.filter("type", "temp")
            if len(uids) == 0:
                cir.append(".temp {}".format(val))
            else:
                cir[uids[0]].value = val
        else:
            if st == "param":
                uids = cir.filter("type", st, uids)
                uids = cir.filter("name", par)
            else:
                uids = cir.filter("type", st, uids)
                uids = cir.filter("instance", par)
            for uid in uids:
                cir[uid].value = val

    netlist = "*Netlist \n" + include + cir.netlist + ctl.netlist

    corner_netlist = "{}.spice".format(netlist_uuid)
    vals = ",".join([netlist_uuid, *args[2]])   

    file_case_netlist = "{}/{}".format(paths["path_netlists"], corner_netlist)
    with open(file_case_netlist, "w") as ofile: 
        ofile.write(netlist)

    with open(paths["file_overview"], "a") as ofile: 
        ofile.write("{}\n".format(vals))


    output = spctl.run_simulation(file_case_netlist)
    res = spctl.extract_output_data(output)

    result_queue.put((vals,res))
    return (vals,res)
