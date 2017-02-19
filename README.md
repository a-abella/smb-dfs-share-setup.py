# smb-dfs-share-setup.py
Automated configuration of LVM storage, SMB share on LVM volume, Winbind authentication, and share root FACL owner/group permissions. Written to facilitate the deployment of a department-segregated DFS network storage solution.

A brief glance at the source will show you that there is not much reason this had to be in Python (vs a shell script), however the long-term idea would be to turn this script into an Ansible playbook for smarter deployment and provisioning.
