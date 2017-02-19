# smb-dfs-share-setup.py
Automated configuration of LVM storage, SMB share on LVM volume, Winbind authentication, and share root FACL owner/group permissions. Written to facilitate the deployment of a department-segregated DFS network storage solution.

A brief glance at the source will show you that there is not much reason this had to be in Python (vs a shell script), however the long-term idea would be to turn this script into an Ansible playbook for smarter deployment and provisioning.

This utility is pretty tightly integrated with my organization's network storage design, so I can't imagine it would serve any passerby much good. Anyone is certainly free to take this and make it their own, however. 
