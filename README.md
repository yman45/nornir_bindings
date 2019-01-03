Nornir bindings and operations
==============================

This repository consist of different operations and bindings written using Nornir.

Runner
------

The implied method to run bindings is by executing utils/runner.py and giving it 
_HOSTNAME_ of a single host to run binding with. If host isn't in inventory, runner will allow 
you to interactively add it. But it can't add new groups. Run it with --help for more 
information.

Bindings
--------

 * tors\_vrf\_check - check different aspects of VRF status on a switch (written for ToR switches)
    and prints out assumption on its operability; works on full inventory
 * switch\_interfaces\_check - gather different states and characteristics of interfaces on a host

Operations
----------

 * check\_interfaces - consist of functions to get admin/oper state of interface list, assigned IP
    addresses, number of learned neighbors (IP neighbors, meaning ARP and NDP) and other interace
    information (description, speed, duplex, load, etc.)
 * check\_mac\_table - grab and count number of MAC addresses learned on interface
 * check\_vrf\_status - check for VRF presence on a switch, build list of assigned interfaces and
    check for status of BGP sessions in that VRF

More information
----------------

Currently more information can be find in function docstrings.
First binding was written as part of a blog post that can be found
[here](http://dvjourney.yman.site/2018/09/30/network-automation-with-nornir/).

Compatibilty
------------

All code is targeted Cisco NX-OS 6 and Huawei VRPv8 V200 if not stated otherwise. Though it may 
work on other code versions.

Requirements
------------

_click_, _nornir_ and all of the dependencies (see requirements.txt). For tests _pytest_ is 
required.

Written by
----------

Yakov Shiryaev, 2018-2019.
