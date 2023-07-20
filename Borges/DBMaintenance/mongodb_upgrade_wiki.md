This page provides step-by-step instructions for upgrading the MongoDB instance which serves our various literature mining collections.

Original authors: Kevin Cruse

Many thanks to Tanjin He for his invaluable help in this process

## Summary

The version of MongDB is currently being updated from 3.4 to 5.0 (as of July 2022), which requires many non-trivial steps to ensure full compatibility for future applications. This page documents that process and provides useful tips for those who plan to make a similar upgrade in the future. 

Most information comes from https://www.mongodb.com/docs/manual/tutorial/upgrade-revision/, but there are other resources for our specific situation throughout this page.

## Tutorial

Below is a set of step-by-step instructions to follow for upgrading your version of MongoDB

## Backup

Be sure to backup '''all collections''' before proceeding.

# Installation

## Ubuntu

### Through <code><nowiki>apt-get</nowiki></code>

On the synthesisproject server, MongoDB appears to have been installed via the <code><nowiki>apt</nowiki></code> package manager. This is the [https://www.mongodb.com/docs/v6.0/tutorial/install-mongodb-on-ubuntu/ preferred method] for MongoDB installation from the MongoDB documentation, as well.

Before installing/updating the MongoDB version on Ubuntu, the user should familiarize themselves with the compatibility between MongoDB version and Ubuntu release. For instance, as of August 2022, Ubuntu 20.04 (Focal) is only compatible with MongoDB versions 4.2 (with issues), 4.4, 5.0, and 6.0. 

Before making changes to the MongoDB on the synthesis project server directly (which can be '''dangerous''' as these collections are used in many projects and applications), it is advised that the user practice installing/upgrading on another Ubuntu device or using a virtual machine (such as [https://www.virtualbox.org VirtualBox]... just make sure you allocate enough disk space for the MongoDB download; a 32GB virtual machine should suffice for this). You can also create a docker container. 

1. First grab the appropriate <code><nowiki>apt-key</nowiki></code> for the MongoDB version of interest: 

<code><nowiki>wget -qO - https://www.mongodb.org/static/pgp/server-{version_number}.asc | sudo apt-key add -</nowiki></code>

The version number is usually in <code><nowiki>X.Y</nowiki></code> form, without any patch number.


2. Create a list file for MongoDB in the <code><nowiki>apt</nowiki></code> package manager directory:

<code><nowiki>echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/{version_number} multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-{version_number}.list</nowiki></code>

Again, if you are trying to downgrade or install an earlier version of MongoDB, be wary of support for the currently installed release of Ubuntu. You can check out [https://repo.mongodb.org/apt/ubuntu/ the apt packages for mongo ] to see what versions of MongoDB have apt packages for each Ubuntu release. 


3. Be sure to reload the local packages database

<code><nowiki>sudo apt-get update</nowiki></code>


4. Implement the actual installation

<code><nowiki>sudo apt-get install -y mongodb-org</nowiki></code>


5. Start MongoDB 

<code><nowiki>sudo systemctl start mongod</nowiki></code>


6. Enter the MongoDB CLI with <code><nowiki>mongosh</nowiki></code> (<code><nowiki>mongo</nowiki></code> for versions older than 5.0)

### Through <code><nowiki>.tgz</nowiki></code> Tarball

If you have upgraded Ubuntu too far ahead that the next version of MongoDB is no longer supported (e.g. need to upgrade incrementally to 3.6 next, but Ubuntu is at 20.04), then you will need to install the subsequent MongoDB versions [https://www.mongodb.com/docs/v5.0/tutorial/install-mongodb-on-ubuntu-tarball/ manually via tarball]. There is a bit of modifying and manual file creation that needs to be done, as well. The steps below (adapted from [https://stackoverflow.com/questions/65127611/monogdb-3-4-in-ubuntu-20-04 this stackoverflow post]) are a guide for this process, using version 3.4.24 as an example:

1. If it doesn't exist, create a directory for managing the mongo installation tarballs and binaries... this will be helpful in the upgrading process described below, as well. Create the following directory tree:

<code><nowiki>/mongo_manager/tools/manage_versions/repo/</nowiki></code>


2. Download the appropriate MongoDB tarball (from the [https://www.mongodb.com/try/download/community?tck=docs_server MongoDB download center]). The platform should be some Linux or appropriate Ubuntu system. Place this in the <code><nowiki>/mongo_manager/tools/manage_versions/repo/</nowiki></code> directory.

<code><nowiki>curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-3.4.24.tgz </nowiki></code>


3. Untar the application

<code><nowiki>tar -zxf mongodb-linux-x86_64-3.4.24.tgz</nowiki></code>


4. Copy the binaries over to <code>/usr/bin</code>

<code>cp -r /mongo_manager/tools/manage_versions/repo/mongodb-linux-x86_64-3.4.24/bin/* /usr/bin </code>


5. Create a <code><nowiki>mongodb</nowiki></code> user

<code><nowiki>useradd -r mongodb</nowiki></code>


6. Add a <code><nowiki>systemctl</nowiki></code> service command for <code><nowiki>mongod</nowiki></code>

<code>vim /lib/systemd/system/mongod.service</code>

<pre>
[Unit]
Description=MongoDB Database Server
Documentation=https://docs.mongodb.org/manual
After=network.target

[Service]
User=mongodb
Group=mongodb
RuntimeDirectory=mongod
RuntimeDirectoryMode=0775
RuntimeDirectoryPreserve=yes
ExecStart=/usr/bin/mongod --config /etc/mongod.conf
PIDFile=/var/run/mongod/mongod.pid
# file size
LimitFSIZE=infinity
# cpu time
LimitCPU=infinity
# virtual memory size
LimitAS=infinity
# open files
LimitNOFILE=64000
# processes/threads
LimitNPROC=64000
# locked memory
LimitMEMLOCK=infinity
# total threads (user+kernel)
TasksMax=infinity
TasksAccounting=false

# Recommended limits for for mongod as specified in
# http://docs.mongodb.org/manual/reference/ulimit/#recommended-settings

[Install]
WantedBy=multi-user.target
</pre>


7. Create some other necessary files/folders and provide permission to the <code>mongod</code> user

<pre>
mkdir /data/mongodb
mkdir /var/run/mongod
touch /var/run/mongod/mongod.pid
touch /var/log/mongodb/mongod.log

chown mongodb:mongodb /data/mongodb/
chown mongodb:mongodb /var/run/mongod/mongod.pid
chown mongodb:mongodb /var/log/mongodb/mongod.log
chown mongodb:mongodb /usr/bin/mongo
</pre>


8. Create the configuration file, <code>/etc/mongod.conf</code>

<pre>
# mongod.conf

# for documentation of all options, see:
#   http://docs.mongodb.org/manual/reference/configuration-options/

# Where and how to store data.
storage:
  dbPath: /data/mongodb
#  dbPath: /var/lib/mongodb
  journal:
    enabled: true
#  engine:
#  mmapv1:
#  wiredTiger:

# where to write logging data.
systemLog:
  destination: file
  logAppend: true
  logRotate: reopen
  path: /var/log/mongodb/mongod.log

# network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0


processManagement:
  pidFilePath: /var/run/mongod/mongod.pid

security:
  authorization: "disabled" #if you are starting from scratch
#  authorization: "enabled" #if you already have an existing instance

#operationProfiling:

#replication:

#sharding:

## Enterprise-Only Options:

#auditLog:

#snmp:
</pre>


9. Restart <code>systemctl</code>

<code>systemctl daemon-reload</code>


10. Start the <code>mongod</code> service

<code>systemctl start mongod</code>


11. Check the status (should see "active (running)"; if the service is failing, check the status output for any possible errors... if there is nothing clear, then check /var/log/mongodb/mongod.log for an error)

<code>systemctl status mongod</code>


12. If everything seems to be running, try to enter the CLI with <code>mongo</code>

## Upgrading

### <code>apt-get</code>

If all intermediate revisions are compatible with your OS, then you can just use <code>apt-get</code> to upgrade. If they are not, follow the Binary Swap steps below to catch up to a compatible version, then you can start using <code>apt-get</code> to continue the upgrading process. See the Installation section above for details on an <code>apt-get</code> upgrade (it should be much more straightforward than the binary swap steps below).

### Binary Swap

Upgrading the MongoDB version should be done incrementally (e.g. from 3.4 => 4.0, you should upgrade 3.4 -> 3.6 -> 4.0). This is more straightforward on OSx devices than on Ubuntu, where older versions of MongoDB do not support newer releases of Ubuntu. If you run into authentication issues, you can always go to <code>/etc/mongod.conf</code> and switch <code>security.authorization</code> from <code>"enabled"</code> to <code>"disabled"</code>... just be sure to switch back after completing all the upgrading tasks!

1. Download tarballs of the source packages from the MongoDB distribution page (choose either Linux or Ubuntu tarballs). See <code>/mongo_manager/tools/manage_versions/repo/</code> for tarballs of the previous versions

2. Untar those in the <code>/mongo_manager/tools/manage_version/repo/</code> folder (see Installing above)

3. If your version is later than 3.4, check the Feature Compatibility Version (FCV) value and set it to the current version if needed. If you are downgrading, set this value to the immediately previous version. Check <code>/root/admin_credentials</code> for the admin password. As an example, going from version 4.4 -> 5.0, the FCV should be set to "4.4":

Checking:
<pre>
$ mongo -u admin -p <admin_pwd> --authenticationDatabase admin
MongoDB shell version v4.4
connecting to: mongodb://127.0.0.1:27017
MongoDB server version: 4.4
> use admin
> db.adminCommand({getParameter:1, featureCompatibilityVersion:1})
{ "featureCompatibilityVersion" : "4.2", "ok" : 1 }
</pre>

If you need to set it:
<pre>
> use admin
> db.adminCommand({setFeatureCompatibilityVersion:"4.4"})
{ "ok" : 1 }
</pre>

4. Stop the <code>mongod</code> service

<pre>
$ sudo systemctl stop mongod
</pre>

5. if upgrading from 3.6->4.0 or downgrading from 4.2->4.0, dump the database (<code>/data/mongodb</code>) using <code>mongodump</code> and clear the <code>/data/mongod/</code> folder

<pre>
$ mkdir /data/mongodb_backup/
$ mongodump -u admin -p <admin_pwd> --out /data/mongodb_backup/
$ rm -r /data/mongodb/
</pre>

6. Remove the binaries <code>/usr/bin/mongo*</code> and <code>/usr/bin/bson*</code> (the latter of which will not be present in version 4.4 and after). '''Be very careful with this step so that you do not remove other binaries!'''

<pre>
$ sudo rm -r /usr/bin/mongo*
$ sudo rm -r /usr/bin/bson*
</pre>

7. Copy binaries from the untarred source package's <code>bin</code> folder for target version to <code>/usr/bin/</code>

<pre>
$ sudo cp -r /mongo_manager/tools/manage_versions/repo/mongodb-linux-x86_64-...-x.x.xx/bin/* /usr/bin/
</pre>

8. Restart the <code>mongod</code> service and check to make sure it's running

<pre>
$ sudo systemctl start mongod
$ sudo systemctl status mongod
mongod.service - MongoDB Database Server
     Loaded: loaded (/lib/systemd/system/mongod.service; enabled; vendor preset>
     Active: active (running) since Sun 2022-06-12 01:06:33 PDT; 2 months 27 da>
       Docs: https://docs.mongodb.org/manual
   Main PID: 1387 (mongod)
     Memory: 178.5G
     CGroup: /system.slice/mongod.service
             └─1387 /usr/bin/mongod --config /etc/mongod.conf
</pre>

If there is a failure, check the log for errors in <code>/var/log/mongodb/mongod.log</code>

9. If you needed to <code>mongodump</code> prior to upgrading, restore them using <code>mongorestore</code> (it may be easiest to set <code>security.authorization</code> to <code>disabled</code> in <code>/etc/mongod.conf</code> briefly while you do this... just be sure to restart the systemd service, and enable authorization and restart again after you're finished)

<pre>
$ mongorestore /data/mongodb_backup
</pre>

10. Update the FCV to the current version you just upgraded to (see step 3 for details)

11. After version 4.4, you will need to install <code>mongodb-database-tools</code> (like <code>mongodump</code>, <code>mongorestore</code>) separately. Just follow [https://www.mongodb.com/docs/database-tools/installation/installation-linux/ these] directions 

12. Repeat these steps until you reach the desired version!

## Downgrading

* Basically, do exactly everything above, but in reverse. 

* Make sure to set FCV to the directly previous version and downgrade incrementally

* will need to follow [https://www.mongodb.com/docs/manual/release-notes/4.2-downgrade-standalone/ these] steps to go from 4.2 to 4.0... this requires a mongodump and mongorestore

# Notes

* If you stop the mongod service, then try running a newer version's <code>mongod</code> executable using the same configuration file, then revert back to the old version through <code>systemctl restart mongod</code>, you will need to refresh/create new permissions for the mongod user on a few wiredTiger files

* Might need to add an extra couple of directories to get symbolic link for <code>mongo</code>

* Simply replacing binaries from 3.4 to 3.6 works for this incremental upgrade

* From 3.6 to 4.0, need to check with FCV? => update: can upgrade successfully through <code>mongodump</code> to backup folder, delete the files in <code>/data/mongodb/</code> (make sure you don't delete the directory itself), then replace the binaries with 4.0 binaries, and use <code>mongorestore</code>... data should be restored!

* ran into issues with porting, so needed to make a new container... this led to issues with systemctl, so downloaded a python executable that mimic systemctl [https://github.com/microsoft/WSL/issues/1579]

* for 4.2, use the Bionic (18.04) Ubuntu release tarball

* for 4.4, need to do 

<code>db.adminCommand({setFeatureCompatibilityVersion:"4.2"})</code> 

prior to replacing the binaries. This should be set to "4.4" prior to replacing with the 5.0 binaries, and "5.0" prior to replacing with the 6.0 binaries

* note there are no <code>bson*</code> binaries after version 4.4

* need to install <code>mongosh</code> when using 6.0 (following [https://www.mongodb.com/docs/mongodb-shell/install/ these instructions])

* if you install via apt-get and need to install again, be sure to <code>apt-get purge mongodb-org</code> and <code>apt-get purge</code>

* still need to remove binaries when transitioning from installing via binary swap to <code>apt-get</code>


Docker

* <code>docker run -it -d --privileged=true --name=test_db2 -p 127.0.0.1:27017:27017 -v /home/kcruse/Scratch:/database customized_ubuntu /sbin/init</code>
