# Open Data Platform
The Open Data Platform (ODP) is an open-source data management platform that can be rapidly deployed and tailored to accelerate Big Data and Cloud-scale solution delivery. The Bootstrap repository features an Ansible Playbook that automates the deployment of a 5-server Hadoop cluster on Amazon Web Services (AWS) Elastic Compute Cloud (EC2) instances that are managed by either HortonWorks or Cloudera.

# Table of Contents
* [Requirements](#requirements)
* [Setup Instructions](#setup-instructions)
  * [Ansible Host Setup](#ansible-host-setup)
  * [HortonWorks Deployment](#hortonworks-deployment)
  * [Cloudera Deployment](#cloudera-deployment)
* [Deploy Using a Local Repository](#deploy-using-a-local-repository)
* [External Resources](#external-resources)

# Requirements
1. The following are installed locally or on Linux VM:
  * [Ansible](http://docs.ansible.com/ansible/latest/intro_installation.html "Ansible Installation Documentation") (2.4 or later)
  * [Python](https://www.python.org/downloads/ "Python Download Documentation") (2.7 or later)
  * [python-boto](http://boto.cloudhackers.com/en/latest/ "Python Boto Documentation") (Python 2.x) [python-boto](http://boto3.readthedocs.io/en/latest/ "Python Boto Documentation") (Python 3.x)
2. AWS IAM user has permissions to launch EC2 Instances
3. AWS Security Groups are set up to allow for communication between EC2 instances

# Setup Instructions
## Ansible Host Setup
1. Set `AWS_ACCESS_KEY` and `AWS_SECRET_ACCESS_KEY` as environment variables for user running Ansible
```bash
export AWS_ACCESS_KEY_ID=aws_access_key_id
export AWS_SECRET_ACCESS_KEY=aws_secret_access_key
```
2. AWS private key from the key pair is saved as `~/.ssh/id_rsa` for user running Ansible (`id_rsa` should be the filename of the key, **not** the directory - there is no extension for the key)
  * **Notice:** It is **extremely** important that the AWS SSH key for Ansible is saved as `~/.ssh/id_rsa`
  * It is best practice to set permissions of `0400` on id_rsa files (read-only to file owner)
3. Clone the Open Data Platform repo to the Ansible host and `cd` to the repo base directory
4. Use Ansible Vault to encrypt the properties file. The Ansible Vault password entered in this step will be needed to edit the properties file and to run the Ansible Playbook.
```bash
ansible-vault encrypt group_vars/all
```
5. Use Ansible Vault to edit `group_vars/all` and configure AWS Settings for `aws_user`, `aws_access_mode`, `aws_unique_identifier`, `aws_image`, `aws_region`, `aws_subnet_id`, `aws_security_group`, `aws_keypair`, `aws_device_name`, `aws_instance_type`, `aws_management_server_volume_size`, and `aws_client_server_volume_size`. Further details and example values for these properties can be found in the `group_vars/all` file comments.
```bash
ansible-vault edit group_vars/all
```
  * AMI Image ID for RHEL7 can be found in AWS console by clicking 'Launch Instance' under the 'Quick Start' tab
  * AMI Image ID for CentOS 7 can be found on the [CentOS Wiki](https://wiki.centos.org/Cloud/AWS "CentOS Wiki")
  * We have verified that the following AMIs work:
    * RHEL-7.4_HVM_GA-20170808-x86_64-2-Hourly2-GP2 (ami-c998b6b2)
    * CentOS Linux 7 x86_64 HVM EBS 1602-b7ee8a69-ee97-4a49-9e68-afaee216db2e-ami-d7e1d2bd.3 (ami-6d1c2007)
  * Region, Subnet, Security Group and Key Pair should be available from your AWS administrator
  * We recommend allocating at least 50 GB of primary disk space

## HortonWorks Deployment

### Components Installed via Ambari
The [HortonWorks](https://docs.hortonworks.com/HDPDocuments/HDP2/HDP-2.6.3/index.html "HortonWorks Data Platform Documentation") deployment installs the following services in [Ambari](https://docs.hortonworks.com/HDPDocuments/Ambari/Ambari-2.6.0.0/index.html "Ambari Documentation"):
  * HDFS
  * YARN
  * MapReduce2
  * Tez
  * Hive
  * Oozie
  * Zookeeper
  * Kafka
  * Spark
  * Zeppelin Notebook

### Topology of HortonWorks Deployment
The specific components of each [HortonWorks](https://docs.hortonworks.com/HDPDocuments/HDP2/HDP-2.6.3/index.html "HortonWorks Data Platform Documentation") service are installed using the following default topology:
* **Master Node (Ambari Server)**: HDFS NameNode, HDFS Client, HDFS DataNode, Kafka Broker, HBase RegionServer, HBase Client, Zeppelin Master, Oozie Server, Spark Client, Tez Client, History Server, Node Manager
* **Client Node 1**: HDFS SecondaryNameNode, HDFS Client, HDFS DataNode, Kafka Broker, HBase Master, HBase RegionServer, HBase Client, ZooKeeper server, Spark JobHistory Server, Hive WebHCat Server, Spark Client, Tez Client,
* **Client Node 2**: HDFS Client, HDFS DataNode, Kafka Broker, HBase RegionServer, HBase Client, MySQL Server, Hive MetaStore, Hive Server, Resource Manager, App Timeline Server, ZooKeeper Client, Spark Client, Tez Client, MapReduce2 Client
* **Client Nodes 3 & 4**: HDFS Client, HDFS DataNode, Kafka Broker, HBase Client, ZooKeeper Client, Spark Client, Hive Client, Oozie Client, Tez Client, Yarn Client, MapReduce2 Client

### Steps to Provision HortonWorks Stack
1. Execute the following command from the repo base directory:
```bash
ansible-playbook --vault-id @prompt provision_hortonworks.yml
```
*Note: The `.retry` files do not work. You can re-run the scripts.*

2. When the playbook has completed execution, Ansible will print a message specifying the URL to access the Ambari console.

## Cloudera Deployment

### Components Installed in Cloudera
The [Cloudera](https://www.cloudera.com/documentation/enterprise/latest.html "Cloudera Enterprise Documentation") deployment installs the following services in Cloudera Manager:
  * HBase
  * HDFS
  * Hive
  * Hue
  * Spark
  * Kafka
  * Oozie
  * YARN (MapReduce2 included)
  * Zookeeper

### Topology of Cloudera Deployment
The specific components of each [Cloudera](https://www.cloudera.com/documentation/enterprise/latest.html "Cloudera Enterprise Documentation") service are installed using the following default topology:
 * **Master Server (Cloudera Manager)**: Cloudera Management Service, HBase RegionServer, HDFS DataNode, Hive Metastore Server, HiveServer2, Hue Server,Oozie Server, YARN NodeManager, Spark JobHistory Server, Spark Server
 * **Client 1**: HBase Thrift Server, HBase Region Server, HDFS Data Node, YARN Node Manager, YARN ResourceManager, ZooKeeper Server, Spark Server
 * **Client 2**: HBase REST Server, HBase RegionServer, HDFS DataNode, Hue Load Balancer, YARN ResourceManager, ZooKeeper Server, Spark Server
 * **Client 3**: HBase Master, HBase RegionServer, HDFS SecondaryNameNode, HDFS DataNode, YARN JobHistory Server, YARN NodeManager, ZooKeeper Server, Spark Server
 * **Client 4**: HBase RegionServer, HDFS NameNode, HDFS DataNode, Hive WebHCat Server, Kafka Broker, YARN NodeManager, Spark Server

### Steps to Provision Cloudera Stack
1. Edit the `group_vars/all` file and create PostgreSQL database passwords by setting the values for `cloudera_db_password`, `hive_metastore_db_password`, `hue_db_password`, and `oozie_db_password`.
2. Execute the following command from the repo base directory:
```bash
ansible-playbook --vault-id @prompt provision_cloudera.yml
```
*Note: The `.retry` files do not work. If the scripts failed during provisiong the AWS instances you can re-run the scripts. If they failed during the python script setup of cloudera, you will need to delete your EC2 instances and try again.*

3. When the playbook has completed execution, Ansible will print a message specifying the URL to access the Cloudera Manager console.

# Deploy Using a Local Repository
In certain cases, such as AWS environments with very limited bandwidth, it may be necessary to set up a local instance of the HortonWorks or Cloudera repositories. In order to do this, first start by creating a new EC2 instance to host the repositories, and then use the `reposync` utility to clone all necessary repositories. Finally, update the `group_vars/all` properties to point to the local repositories.

## Configure Repository Server
1. Provision a new EC2 instance using either the Red Hat or CentOS AMI. Ensure the instance is of size t2.medium or larger.
2. SSH into the instance and become the `root` user.
3. Execute the following commands to disable SELinux, install the Apache httpd web server, wget, and createrepo utility:
```bash
setenforce 0
yum -y install httpd wget createrepo
systemctl start httpd
systemctl enable httpd
mkdir /var/www/html/repos
```

## Clone the HortonWorks Repositories
Execute the following commands to create a full mirror of the Ambari, HDP, and HDP-Utils repositories:
```bash
cd /etc/yum.repos.d
wget http://public-repo-1.hortonworks.com/ambari/centos7/2.x/updates/2.5.2.0/ambari.repo http://public-repo-1.hortonworks.com/HDP/centos7/2.x/updates/2.6.2.14/hdp.repo
cd /var/www/html/repos
nohup reposync -r ambari-2.5.2.0 -r HDP-2.6.2.14 -r HDP-UTILS-1.1.0.21 &
createrepo ambari-2.5.2.0
createrepo HDP-2.6.2.14
createrepo HDP-UTILS-1.1.0.21
```

## Clone the Cloudera Repositories
Execute the following commands to create a full mirror of the Cloudera Manager repository and to create a partial mirror of the parcels repository that only pulls the necessary artifacts:
```bash
cd /etc/yum.repos.d
wget https://archive.cloudera.com/cm5/redhat/7/x86_64/cm/cloudera-manager.repo
cd /var/www/html/repos
nohup reposync -r cloudera-manager &
mkdir cloudera-parcels
cd cloudera-parcels
nohup wget http://archive.cloudera.com/cdh5/parcels/5.13.0.29/CDH-5.13.0-1.cdh5.13.0.p0.29-el7.parcel http://archive.cloudera.com/cdh5/parcels/5.13.0.29/manifest.json &
cd /var/www/html/repos
createrepo cloudera-manager
createrepo cloudera-parcels
```

## Update Ansible Properties to Use Local Repositories
Edit the `group_vars/all` file and update the following properties, inserting the private IP address of the EC2 instance being used to host the repositories in place of `repo_server_private_ip`:
 * For HortonWorks:
```bash
ambari_repo_7: http://repo_server_private_ip/repos/ambari-2.5.2.0
hdp_repo_7: http://repo_server_private_ip/repos/HDP-2.6.2.14
hdp_utils_repo_7: http://repo_server_private_ip/repos/HDP-UTILS-1.1.0.21
```
 * For Cloudera:
```bash
cloudera_manager_repo: http://repo_server_private_ip/repos/cloudera-manager
cloudera_parcel_repo: http://repo_server_private_ip/repos/cloudera-parcels
```


# External Resources
  * NiFi Resources
    * We are using ODP NiFi Version 0.1.0
  * Elastic
    * We are using Elastic version 6.6.0
  * kibana  
    * We are using Kibana version 6.6.0
  * Ansible Resources
    * [Ansible Homepage](https://www.ansible.com/ "Ansible")
    * [Ansible Installation Documentation](http://docs.ansible.com/ansible/latest/intro_installation.html "Ansible Installation Documentation")
    * [Ansible Vault Documentation](https://docs.ansible.com/ansible/2.4/vault.html "Ansible Vault Documentation")
    * [Python Download Documentation](https://www.python.org/downloads/ "Python Download Documentation")
    * [Python Boto Documentation](http://boto3.readthedocs.io/en/latest/ "Python Boto Documentation")
  * HortonWorks Resources
    * [HortonWorks Homepage](https://hortonworks.com/ "HortonWorks")
    * [HortonWorks Data Platform Documentation](https://docs.hortonworks.com/HDPDocuments/HDP2/HDP-2.6.3/index.html "HortonWorks Data Platform Documentation")
    * [Ambari Documentation](https://docs.hortonworks.com/HDPDocuments/Ambari/Ambari-2.6.0.0/index.html "Ambari Documentation")
  * Cloudera Resources
    * [Cloudera Homepage](https://www.cloudera.com/ "Cloudera")
    * [Cloudera Enterprise Documentation](https://www.cloudera.com/documentation/enterprise/latest.html "Cloudera Enterprise Documentation")
  * Amazon Web Services Resources
    * [Amazon Web Services Homepage](https://aws.amazon.com/ "Amazon Web Services (AWS)")
    * [Amazon Web Services Elastic Compute Cloud (EC2)](https://aws.amazon.com/ec2/?nc2=h_m1 "Elastic Compute Cloud (EC2)")
