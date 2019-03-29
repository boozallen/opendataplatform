#!/bin/python

# Copyright: (c) 2019, Booz Allen Hamilton
# Booz Allen Public License v1.0 (see LICENSE or http://boozallen.github.io/licenses/bapl)

# Configure Cloudera cluster for ODP using Python API client
# See http://cloudera.github.io/cm_api/docs/python-client/ for more details.

from cm_api.api_client import ApiResource
from cm_api.endpoints.cms import ClouderaManager
from cm_api.endpoints.services import ApiServiceSetupInfo
import ConfigParser
import time
import logging
import sys

# Setup logger and log file
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="/root/cloudera_deploy.log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")

# Read properties file containing host names of servers
logging.info('Reading and parsing properties file')
config = ConfigParser.ConfigParser()
config.read('/root/cloudera.ini')

# Set variables from properties file
cloudera_manager_server_api = config.get('MANAGER', 'management_server_api')
cloudera_manager_server = config.get('MANAGER', 'management_server')
management_console_username = config.get('MANAGER', 'management_console_username')
management_console_password = str(sys.argv[1])
hosts_from_file = config.items('HOSTS')
hosts = [cloudera_manager_server]
for host in hosts_from_file:
    hosts.append(host[1])
cloudera_user = config.get('USERS', 'aws_user')
cloudera_user_key = config.get('USERS', 'aws_user_ssh_key')
cloudera_mgmt_service_db = config.get('CLOUDERA_MGMT_SERVICE', 'clouderadb')
cloudera_mgmt_service_user = config.get('CLOUDERA_MGMT_SERVICE', 'clouderadbuser')
cloudera_mgmt_service_pwd = str(sys.argv[2])
cloudera_mgmt_service_type = config.get('CLOUDERA_MGMT_SERVICE', 'clouderadbtype')
cloudera_mgmt_service_host = config.get('CLOUDERA_MGMT_SERVICE', 'clouderadbhost')
cloudera_manager_repo = config.get('REPOS', 'cloudera_manager_repo')
cloudera_manager_repo_gpg = config.get('REPOS', 'cloudera_manager_repo_gpg')
cdh_parcel_repo = config.get('PARCELS', 'parcel_repo_url')
cdh_parcel_version = config.get('PARCELS', 'cdh_parcel_version')
kafka_parcel_repo = config.get('PARCELS', 'kafka_parcel_repo')
kafka_parcel_version = config.get('PARCELS', 'kafka_parcel_version')
api_version = config.get('CLOUDERA_PROPERTIES', 'api_version')

# Set API client and ClouderaManager object
logging.info('Setting initial Cloudera API Resource object with default user')
api = ApiResource(cloudera_manager_server_api, username="admin", password="admin", version=api_version)
cloudera_manager = ClouderaManager(api)

# Create new admin user and delete default admin user
logging.info('Creating new admin user')
api.create_user(management_console_username, management_console_password, ["ROLE_ADMIN"])

logging.info('Setting Cloudera API Resource object using new user')
api = ApiResource(cloudera_manager_server_api, username=management_console_username, password=management_console_password, version=api_version)
cloudera_manager = ClouderaManager(api)

logging.info('Deleting default admin user')
api.delete_user("admin")

# Read SSH key to variable
logging.info('Reading SSH key for Cloudera Manager and Agents')
keyfile = open(cloudera_user_key, "r")
id_rsa = keyfile.read().rstrip('\n')
keyfile.close()

# Install Cloudera Manager Agent on other servers
logging.info('Installing Cloudera Manager Agent on management and host servers')
cloudera_manager.host_install(user_name=cloudera_user,
                 host_names=hosts,
                 private_key=id_rsa,
                 cm_repo_url=cloudera_manager_repo,
                 gpg_key_custom_url=cloudera_manager_repo_gpg,
                 java_install_strategy="NONE"
                 ).wait()

# Create and start the Cloudera Management Service
logging.info('Creating Cloudera Management Service')
try:
    mgmt_setup = ApiServiceSetupInfo()
    mgmt = cloudera_manager.create_mgmt_service(mgmt_setup)
except Exception:
    mgmt = cloudera_manager.get_service()

logging.info('Creating EVENTSERVER role if it does not exist')
try:
    mgmt.create_role("mgmt-es", "EVENTSERVER", cloudera_manager_server)
except Exception:
    logging.info('Role mgmt-es already exists, continuing...')

logging.info('Creating SERVICEMONITOR role if it does not exist')
try:
    mgmt.create_role("mgmt-sm", "SERVICEMONITOR", cloudera_manager_server)
except Exception:
    logging.info('Role mgmt-sm already exists, continuing...')

logging.info('Creating HOSTMONITOR role if it does not exist')
try:
    mgmt.create_role("mgmt-hm", "HOSTMONITOR", cloudera_manager_server)
except Exception:
    logging.info('Role mgmt-hm already exists, continuing...')

logging.info('Creating ALERTPUBLISHER role if it does not exist')
try:
    mgmt.create_role("mgmt-ap", "ALERTPUBLISHER", cloudera_manager_server)
except Exception:
    logging.info('Role mgmt-ap already exists, continuing...')

# Used by HOSTMONITOR and SERVICEMONITOR
mgmt_hm_config = {
    'firehose_database_host': cloudera_mgmt_service_host,
    'firehose_database_user': cloudera_mgmt_service_user,
    'firehose_database_password': cloudera_mgmt_service_pwd,
    'firehose_database_type': cloudera_mgmt_service_type,
    'firehose_database_name': 'firehose'
}

logging.info('Updating role configurations')
for group in mgmt.get_all_role_config_groups():
    if group.roleType == "HOSTMONITOR":
        group.update_config(mgmt_hm_config)
    if group.roleType == "SERVICEMONITOR":
        group.update_config(mgmt_hm_config)

logging.info('Starting the Cloudera Manager service')
mgmt.start().wait()

# Update the Parcels repo
logging.info('Updating the remote parcels repo')
cm_config = api.get_cloudera_manager().get_config(view='full')
repo_urls = cdh_parcel_repo + ',' + kafka_parcel_repo
api.get_cloudera_manager().update_config({'REMOTE_PARCEL_REPO_URLS': repo_urls})
time.sleep(10)

# Download the CDH Parcel
logging.info('Downloading the CDH parcel')
cluster_name = 'Open Data Platform'
cluster = api.create_cluster(cluster_name, version='CDH5')
cluster.add_hosts(hosts)
cdh_parcel = cluster.get_parcel('CDH', cdh_parcel_version)
cdh_parcel.start_download()
while True:
  cdh_parcel = cluster.get_parcel('CDH', cdh_parcel_version)
  if cdh_parcel.stage == 'DOWNLOADED':
    break
  if cdh_parcel.state.errors:
    raise Exception(str(cdh_parcel.state.errors))
  logging.info('Parcel download progress: %s / %s', cdh_parcel.state.progress, cdh_parcel.state.totalProgress)
  time.sleep(15) # check again in 15 seconds

logging.info('Downloaded CDH parcel version %s on cluster %s', cdh_parcel_version, cluster_name)

# Download the Kafka Parcel
logging.info('Downloading the Kafka parcel')
kafka_parcel = cluster.get_parcel('KAFKA', kafka_parcel_version)
kafka_parcel.start_download()
while True:
  kafka_parcel = cluster.get_parcel('KAFKA', kafka_parcel_version)
  if kafka_parcel.stage == 'DOWNLOADED':
    break
  if kafka_parcel.state.errors:
    raise Exception(str(kafka_parcel.state.errors))
  print "progress: %s / %s" % (kafka_parcel.state.progress, kafka_parcel.state.totalProgress)
  time.sleep(15) # check again in 15 seconds

print "Downloaded KAFKA parcel version %s on cluster %s" % (kafka_parcel_version, cluster_name)

# Distribute CDH Parcel to hosts
logging.info('Distributing CDH Parcel to hosts')
cdh_parcel.start_distribution()
while True:
  cdh_parcel = cluster.get_parcel('CDH', cdh_parcel_version)
  if cdh_parcel.stage == 'DISTRIBUTED':
    break
  if cdh_parcel.state.errors:
    raise Exception(str(cdh_parcel.state.errors))
  logging.info('Parcel distribution progress: %s / %s', cdh_parcel.state.progress, cdh_parcel.state.totalProgress)
  time.sleep(15) # check again in 15 seconds

logging.info('Distributed CDH parcel version %s on cluster %s', cdh_parcel_version, cluster_name)

# Distribute KAFKA Parcel to agents
logging.info('Distributing Kafka parcel to hosts')
kafka_parcel.start_distribution()
while True:
  kafka_parcel = cluster.get_parcel('KAFKA', kafka_parcel_version)
  if kafka_parcel.stage == 'DISTRIBUTED':
    break
  if kafka_parcel.state.errors:
    raise Exception(str(kafka_parcel.state.errors))
  print "progress: %s / %s" % (kafka_parcel.state.progress, kafka_parcel.state.totalProgress)
  time.sleep(15) # check again in 15 seconds

print "Distributed KAFKA parcel version %s on cluster %s" % (kafka_parcel_version, cluster_name)

# Activate Parcels
logging.info('Activating CDH and Kafka Parcels')
cdh_parcel.activate()
kafka_parcel.activate()
logging.info('Cloudera download and distribution complete')
