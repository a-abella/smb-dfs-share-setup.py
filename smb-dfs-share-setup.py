#!/usr/bin/env python

# smb-dfs server configurator
# Antonio Abella - 2/9/2017

# Automated configuration of LVM storage, SMB share on LVM volume,
# Winbind authentication, and share root FACL owner/group permissions

import os
import socket
import subprocess

os.system('clear')
print ''

# Check for prereqs
paths = ['/etc/samba/smb.conf', '/etc/krb5.conf', '/usr/bin/ssm']
depswitch = 0
for path in paths:
    if not os.path.exists(path):
        print 'ERROR: Missing file', path
        depswitch = 1
    else:
        print path, 'found! Proceeding with setup.'

if depswitch == 1:
    print '\nPlease resolve the missing dependencies. Did you create this server with the correct kickstart (//net-path/to/kickstart/smb-dfs/smb-dfs-kick.ks)?\n'
    quit()

# Check for second drive for LVM
if not os.path.exists('/dev/sdb'):
    print 'ERROR: Missing device /dev/sdb'
    print '\nPlease create the missing device. Note: CentOS will not recognize a new virtual hard disk until the system has been rebooted.\n'
    quit()

# Prompt for host-specific input
varDomain = 'DOMAIN'
varHostname = raw_input('\nEnter system hostname[' + socket.gethostname() +'] ')
varSharename = raw_input('Enter samba shared folder name [SHARENAME] ')
print "\nFor reference, Samba access groups are located in OU domain.tld/path/to/Security Groups/SMB DFS\n"
varShareaccess = raw_input('Enter the AD group name that should have access to the share [SMB_SHARENAME] ')
varShareowner = raw_input('Enter the AD account name that should own the share directory [SMBADMINUSER] ')
varSharegroup = raw_input('Enter the AD group name that should own the share directory [SMBADMINGROUP] ')

if not varHostname:
	varHostname = socket.gethostname()

if not varSharename:
	varSharename = 'SHARENAME'

if not varShareaccess:
	varShareaccess = 'SMB_SHARENAME'

if not varShareowner:
	varShareowner = 'SAMBAADMINUSER'

if not varSharegroup:
	varSharegroup = 'SAMBAADMINGROUP'


shareAccessTwoSlash = varDomain + '\\' + varShareaccess
shareAccessFourSlash = varDomain + '\\\\' + varShareaccess
shareOwnerTwoSlash = varDomain + '\\' + varShareowner
shareOwnerFourSlash = varDomain + '\\\\' + varShareowner
shareGroupTwoSlash = varDomain + '\\' + varSharegroup
shareGroupFourSlash = varDomain + '\\\\' + varSharegroup

print '\nBeginning setup...\n'

# Retrieve site-specific DC
print 'Getting site DC...',

# Use our IP's second octet to identify DC in same site
sitePrefixDC = {'1':'10.1.0.1', '2':'10.2.0.1'}
myIpAddress = socket.gethostbyname(socket.gethostname())
myDC = sitePrefixDC[myIpAddress.split('.')[1]]
print 'Done.'

# Create the share path and set security
print 'Creating share path...',
os.system('mkdir -p /share/' + varSharename)
print 'Done.'

# Write the SMB.conf file with provided input
print 'Writing smb.conf...',
smbConfFile = """[global]
#--authconfig--start-line--
# Generated by authconfig on 2016/09/20 16:02:58
# DO NOT EDIT THIS SECTION (delimited by --start-line--/--end-line--)
# Any modification may be deleted or altered by authconfig in future
workgroup = DOMAIN
password server = {0}
realm = DOMAIN.TLD
security = ads
idmap config * : range = 16777216-33554431
template shell = /sbin/nologin
kerberos method = secrets only
winbind use default domain = false
winbind offline logon = false
#--authconfig--end-line--
netbios name = {3}
# log files split per-machine:
log file = /var/log/samba/log.%m
# maximum size of 50KB per log file, then rotate:
max log size = 50
passdb backend = tdbsam
load printers = no
printcap name = /dev/null
printing = bsd
disable spoolss = yes
##
## Shares defined here
##
[{1}]
comment = {1} Department share
path = /share/{1}
vfs objects = acl_tdb
public = yes
read only = no
valid users = @DOMAIN\{2} @DOMAIN\SAMBAADMINGROUP
force group = +DOMAIN\{2}
create mask = 2770
force create mode = 2770
directory mask = 2770
force directory mode = 2770""".format(myDC, varSharename, varShareaccess, varHostname.upper())

smbFile = open('/etc/samba/smb.conf' , 'w')
smbFile.write( smbConfFile )
smbFile.close()
print "Done."

# Join the domain for domain user authentication on share
print "Joining the DOMAIN domain...\n"
os.system('net ads join -U DOMAIN\\\\SERVICEACCOUNT\%PASSWORD')
print "\nDone."
print "Note: Remember to add host to DNS!\n"

# Create logical volume
print "Creating share volume...\n"
os.system('ssm create -n ' + varSharename + '_share --fstype ext4 -p sharepool00 /dev/sdb /share/' + varSharename)
os.system('chmod 755 /share/' + varSharename)
print 'Done.\n'

# Enable winbind authentication
print 'Setting share directory ownership...\n'
os.system('systemctl start winbind')
os.system('authconfig --enablewinbind --enablewinbindauth --enablewinbindkrb5 --updateall')
getUser = subprocess.check_output('wbinfo -i ' + shareOwnerFourSlash, shell=True)
getUid = getUser.split(':')[2]
getGroup = subprocess.check_output('wbinfo --group-info ' + shareGroupFourSlash, shell=True)
getGid = getGroup.split(':')[2]
os.system('chown ' + getUid + ':' + getGid + ' /share/' + varSharename)
print '\nDone.\n'

# Add logical volume to fstab
print 'Adding share to fstab...',
fsEntry = "/dev/mapper/sharepool00-" + varSharename + "_share\t/share/" + varSharename + "\t\text4\t\tdefaults\t0 0\n"
fstabFile = open('/etc/fstab', 'ab')
fstabFile.write(fsEntry)
fstabFile.close()
print "Done.\n"

# Start and enable processes
print "Starting processes...",
os.system('systemctl restart winbind')
os.system('systemctl start nmb')
os.system('systemctl start smb')
print "Done.\n"
print "Adding processes to startup...\n"
os.system('systemctl reenable winbind')
os.system('systemctl enable nmb')
os.system('systemctl enable smb')
print "Done.\n"

print "\n\nInitial setup is complete. Please proceed with post-configure procedures:"
print "\n * Create DNS A record for " + varHostname + ".DOMAIN.TLD"
print " * Create initial share subdirectories and change their ownership to the correct folder group."
print " * Create the Nagios Alert for " + varHostname
print " * Add \\\\" + varHostname + ".DOMAIN.TLD\\" + varSharename + " to the smb-dfs namespace folders on CORP-DC.\n\n"
