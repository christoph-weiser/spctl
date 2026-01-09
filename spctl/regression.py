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


def file_writer(queue, filename):
    """
    Listens for messages on the queue and writes them to a file.
    Solely responsible for file I/O to avoid race conditions.
    """
    # Open with 'a' (append) and buffering=1 (line-buffered) for 2026 reliability
    with open(filename, "a", encoding="utf-8", buffering=1) as f:
        while True:
            # This blocks until an item is available
            result = queue.get()
            # Check for the sentinel value to exit
            if result == "exit":
                break
            vals = result[0]
            res  = result[1]
            for k in res:
                f.write("{},{},{}\n".format(vals, k, res[k]))
            f.flush() # Ensures data is saved even if the system crashes


def run_cases(paths, args, result_queue, simulator):

    logger = logging.getLogger()
    if not logger.handlers:
        logger.addHandler(QueueHandler(log_queue))
    logger.setLevel(logging.INFO)
    
    logger.info("--------------------")
    logger.info("Testcase")
    logger.info("--------------------")
    for par, val in zip(args[0], args[2]):
        logger.info("{:<14}: {}".format(par,val))


    # Get unqique id for netlist
    netlist_uuid = uuid.uuid4().hex

    # Load the circuit from file
    cir = spctl.CircuitSection(paths["file_netlist"])

    if simulator == "ngspice":
        ctl = spctl.ControlSection(paths["file_netlist"])
        lines = ctl.lines
        for i,line in enumerate(lines):
            # TODO: this only applies to ngspice
            if re.match("^wrdata", line):
                s = line.split(" ")
                s[1] = "{}/{}.csv".format(paths["path_data"], netlist_uuid)
                line =  " ".join(s)
                lines[i] = line
        ctl.lines = lines
    elif simulator == "xyce":
        if "print" in cir.element_types():
            for p in cir.prints:
                if "file" in p.args:
                    p.args["file"] = "{}/{}.csv".format(paths["path_data"], netlist_uuid)
        
    include = ""
    for par, st, val in zip(args[0], args[1], args[2]):
        if par == "corner":
            include = ".include {}/{}.spice\n".format(paths["path_corners"], val)
        elif par == "temperature":
            # TODO this ngspice specific
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

    netlist = "*Netlist \n" + include + cir.netlist
    if simulator == "ngspice":
        netlist = netlist + ctl.netlist

    case_netlist = "{}.spice".format(netlist_uuid)
    vals = ",".join([netlist_uuid, *args[2]])   

    file_case_netlist = "{}/{}".format(paths["path_netlists"], case_netlist)
    with open(file_case_netlist, "w") as ofile: 
        ofile.write(netlist)

    with open(paths["file_overview"], "a") as ofile: 
        ofile.write("{}\n".format(vals))

    if simulator == "ngspice":
        output = spctl.ngspice.run_simulation(file_case_netlist)
        res = spctl.ngspice.extract_output_data(output)
    elif simulator == "xyce":
        output = spctl.xyce.run_simulation(file_case_netlist)
        res = spctl.xyce.extract_output_data(output)

    result_queue.put((vals,res))
