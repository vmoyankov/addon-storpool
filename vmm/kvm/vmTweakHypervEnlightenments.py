#!/usr/bin/env python

# -------------------------------------------------------------------------- #
# Copyright 2015-2017, StorPool (storpool.com)                               #
#                                                                            #
# Licensed under the Apache License, Version 2.0 (the "License"); you may    #
# not use this file except in compliance with the License. You may obtain    #
# a copy of the License at                                                   #
#                                                                            #
# http://www.apache.org/licenses/LICENSE-2.0                                 #
#                                                                            #
# Unless required by applicable law or agreed to in writing, software        #
# distributed under the License is distributed on an "AS IS" BASIS,          #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.   #
# See the License for the specific language governing permissions and        #
# limitations under the License.                                             #
#--------------------------------------------------------------------------- #

#
# Credits: Todor Tanev <tt@storpool.com>
#
# vmTweakHypervEnlightenments.py <XMLfile>
#
# add the following line after cat >$domain in remotes/vmm/kvm/deploy
#  "$(dirname $0)/vmTweakHypervEnlightenments.py" "$domain"


import sys
import syslog
import xml.etree.ElementTree as ET
import xml.dom.minidom
#import ipdb; ipdb.set_trace() # BREAKPOINT

dbg = 0
thrnum = u'1'

if dbg:
	syslog.openlog('vmTweakVirtioHypervEnlightenments.py', syslog.LOG_PID)

def format_xml(elem, level=0, indent="    "):
    nl = "\n" + indent * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = nl + indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = nl
        for elem in elem:
            format_xml(elem, level+1, indent)
        if not elem.tail or not elem.tail.strip():
            elem.tail = nl
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = nl


xmlFile = sys.argv[1]

doc = ET.parse(xmlFile)
domain = doc.getroot()
vm_name = domain.find("name").text

# add iothreads
iothreads = ET.SubElement(domain, "iothreads")
iothreads.text = thrnum

# configure all drives to use thread 1
for disk in domain.findall('devices/disk'):
    # only vd* disks
    target = disk.find('target')
    dev = target.get('dev')
    if dev is None or dev[:2] != 'vd':
        continue
    disk_drv = disk.find('driver[@io="native"]')
    if disk_drv is not None:
        disk_drv.set('iothread', thrnum)


new_driver = ET.Element('driver', iothread=thrnum)

# check existing disk controllers model virtio-scsi
# or create new controller if not exist
# add <driver iothred="..."> to each disk controller
# or set iothread attribute to <driver> if exists
controllers = domain.findall('devices/controller[@model="virtio-scsi"]')
for controller in controllers:
    driver = controller.find('driver')
    if driver is None:
        controller.append(new_driver)
    else:
        driver.set('iothread', thrnum)
if len(controllers) == 0 :
    devices = domain.find('devices')
    controller = ET.SubElement(devices, 'controller',
            type='scsi', model='virtio-scsi')
    controller.append(new_driver)


# Add clock and timers to windows VMs
# It is possible to recognize windows VMs by the availability of /domain/featrues/hyperv entry
if domain.find('features/hyperv') is not None:
    clock = domain.find('clock')
    if clock is None:
        clock = ET.SubElement(domain, 'clock', offset='utc')
    ET.SubElement(clock, "timer", name='hypervclock', present="yes")
    ET.SubElement(clock, "timer", name='rtc', tickpolicy='catchup')
    ET.SubElement(clock, "timer", name='pit', tickpolicy='delay')
    ET.SubElement(clock, "timer", name='hpet', present='no')

format_xml(domain, indent='    ')
doc.write(xmlFile)
