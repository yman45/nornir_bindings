Nornir bindings and operations
==============================

This repository consist of different operations and bindings written using Nornir.

Bindings
--------

 * tors\_vrf\_check - check different aspects of VRF status on a switch (written for ToR switches)
    and prints out assumption on its operability; works on full inventory

Operations
----------

 * check\_interfaces - consist of functions to get admin/oper state of interface list, assigned IP
    addresses and number of learned neighbors (IP neighbors, meaning ARP and NDP)
 * check\_mac\_table - grab and count number of MAC addresses learned on interface
 * check\_vrf\_status - check for VRF presence on a switch, build list of assigned interfaces and
    check for status of BGP sessions in that VRF

More information
----------------

Currently more information can be find in function docstrings.

Requirements
------------

_nornir_ and all of it dependencies (see requirements.txt). For tests _pytest_ is required.

Written by
----------

Yakov Shiryaev in 2018.
