#!/bin/python

# Copyright: (c) 2019, Booz Allen Hamilton
# Booz Allen Public License v1.0 (see LICENSE or http://boozallen.github.io/licenses/bapl)

from cm_api.api_client import ApiResource
from cm_api.endpoints.cms import ClouderaManager
from cm_api.endpoints.services import ApiService
import json
import time
import math
import ConfigParser
import logging
import sys

# Setup logger and log file
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="/root/cloudera_configure.log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")

# Read properties file containing host names of servers
logging.info('Reading properties file')
config = ConfigParser.ConfigParser()
config.read('/root/cloudera.ini')

# Set variables from properties file
logging.info('Setting variables from properties file')
cloudera_manager_server_api = config.get('MANAGER', 'management_server_api')
cloudera_management_server_fqdn = config.get('MANAGER', 'management_server')
management_console_username = config.get('MANAGER', 'management_console_username')
management_console_password = str(sys.argv[1])
hive_metastore_db_host = config.get('CLOUDERA_PROPERTIES', 'hive_metastore_db_host')
hive_metastore_db_name = config.get('CLOUDERA_PROPERTIES', 'hive_metastore_db_name')
hive_metastore_db_password = str(sys.argv[2])
hive_metastore_db_user = config.get('CLOUDERA_PROPERTIES', 'hive_metastore_db_user')
hue_db_host = config.get('CLOUDERA_PROPERTIES', 'hue_db_host')
hue_db_name = config.get('CLOUDERA_PROPERTIES', 'hue_db_name')
hue_db_password = str(sys.argv[3])
hue_db_user = config.get('CLOUDERA_PROPERTIES', 'hue_db_user')
oozie_db_host = config.get('CLOUDERA_PROPERTIES', 'oozie_db_host')
oozie_db_name = config.get('CLOUDERA_PROPERTIES', 'oozie_db_name')
oozie_db_password = str(sys.argv[4])
oozie_db_user = config.get('CLOUDERA_PROPERTIES', 'oozie_db_user')
api_version = config.get('CLOUDERA_PROPERTIES', 'api_version')

# Get Cloudera Manager, config, and ODP Cluster
logging.info('Retrieving Cloudera Manager service and cluster instance')
api = ApiResource(cloudera_manager_server_api, 7180, management_console_username, management_console_password, version=api_version)
cloudera_manager = ClouderaManager(api)
cloudera_manager_config = api.get_cloudera_manager().get_config(view='full')
cluster_name = 'Open Data Platform'
cluster = api.get_cluster(cluster_name)

# Retrieve all ApiHost objects, locate the management server and add others to clients
logging.info('Retrieving all hosts from cluster')
hosts = api.get_all_hosts()
clients = []
for host in hosts:
    # Suppress Clock Offset warning that incorrectly states chrony is not working
    host.update_config({'host_health_suppression_host_clock_offset': 'true'})

    # Separate Cloudera Manager Server from agents
    if host.hostname == cloudera_management_server_fqdn:
        cloudera_management_server = host
    else:
        clients.append(host)

num_data_nodes = len(clients) + 1 # Every node is a datanode, so sum # clients with mgmt server

# Create Zookeeper Service
logging.info('Creating Zookeeper Service')
zookeeper = cluster.create_service("ZooKeeper", "ZOOKEEPER")
for i in range(1,4):
    zookeeper_server = zookeeper.create_role("ZooKeeper-sv" + str(i), "SERVER", clients[i].hostId)

# Pause to allow ZooKeeper to initialize
time.sleep(20)

# Start ZooKeeper
logging.info('Starting ZooKeeper Service')
zookeeper.start().wait()



# Create Kafka Service and Roles
logging.info('Creating Kafka Service and Roles')
kafka = cluster.create_service("Kafka", "KAFKA")
kafka_server = kafka.create_role("Kafka-gwm", "GATEWAY", cloudera_management_server.hostId)
for i in range(4):
    kafka.create_role("Kafka-gw" + str(i), "GATEWAY", clients[i].hostId)
kafka_broker = kafka.create_role("Kafka-broker", "KAFKA_BROKER", clients[0].hostId)

# Configure Kafka Service
logging.info('Configuring Kafka Service')
kafka_config = { 'zookeeper_service': 'ZooKeeper' }
kafka.update_config(svc_config=kafka_config)

# Start Kafka
logging.info('Starting Kafka Service')
kafka.start().wait()

# Create HDFS Service and Roles
logging.info('Creating HDFS Service and Roles')
hdfs = cluster.create_service("HDFS", "HDFS")
namenode = hdfs.create_role("HDFS-namenode", "NAMENODE", clients[0].hostId)
secondary_namenode = hdfs.create_role("HDFS-snn", "SECONDARYNAMENODE", clients[1].hostId)
gateway = hdfs.create_role("HDFS-gw", "GATEWAY", clients[2].hostId)
hdfs.create_role("HDFS-dnm", "DATANODE", cloudera_management_server.hostId)
for i in range(4):
    hdfs.create_role("HDFS-dn" + str(i), "DATANODE", clients[i].hostId)

# Configure HDFS Service and Roles
logging.info('Configuring HDFS Service and Roles')
hdfs_config = { 
    'dfs_umaskmode': '002',
    'zookeeper_service': 'ZooKeeper' 
}
# Cloudera recommends the number of NameNode handlers and service handlers be at
# least equal to ln(# datanodes) * 20. Compute this value and round up to nearest int.
handler_count = int(math.ceil(math.log1p(num_data_nodes - 1) * 20))
namenode_config = {
    'dfs_name_dir_list': '/dfs/nn',
    'dfs_namenode_handler_count': handler_count,
    'dfs_namenode_service_handler_count': handler_count
}
secondary_namenode_config = { 'fs_checkpoint_dir_list': '/dfs/snn' }
datanode_config = { 'dfs_data_dir_list': '/dfs/dn' }
gateway_config = { 'dfs_client_use_trash': 'true' }

hdfs.update_config(svc_config=hdfs_config)

for role in hdfs.get_all_role_config_groups():
    if role.roleType == "NAMENODE":
        role.update_config(namenode_config)
    elif role.roleType == "SECONDARYNAMENODE":
        role.update_config(secondary_namenode_config)
    elif role.roleType == "DATANODE":
        role.update_config(datanode_config)
    elif role.roleType == "GATEWAY":
        role.update_config(gateway_config)

# Format NameNode
logging.info('Formatting HDFS NameNode')
hdfs.format_hdfs("HDFS-namenode")

# Allow NameNode formatting to complete
time.sleep(20)

# Start HDFS
logging.info('Starting HDFS Service')
hdfs.start().wait()

# Create HDFS /tmp directory
logging.info('Creating HDFS /tmp directories')
hdfs.create_hdfs_tmp()


# Create HBase Service and Roles
logging.info('Creating HBase Service and Roles')
hbase = cluster.create_service("HBase", "HBASE")
hbase_master = hbase.create_role("HBase-master", "MASTER", clients[1].hostId)
hbase.create_role("HBase-regionserverm", "REGIONSERVER", cloudera_management_server.hostId)
for i in range(4):
    hbase.create_role("HBase-regionserver" + str(i), "REGIONSERVER", clients[i].hostId)
hbase_restserver = hbase.create_role("HBase-restserver", "HBASERESTSERVER", clients[2].hostId)
hbase_thriftserver = hbase.create_role("HBase-thriftserver", "HBASETHRIFTSERVER", clients[3].hostId)

# Configure HBase Service
logging.info('Configuring HBase Service')
hbase_config = {
    'hdfs_service': 'HDFS',
    'zookeeper_service': 'ZooKeeper',
    'hbase_enable_replication': 'true'
}
hbase.update_config(svc_config=hbase_config)

# Start HBase
logging.info('Starting HBase Service')
hbase.start().wait()

# Create HBase root directory
logging.info('Creating HBase root directory')
hbase.create_hbase_root()

# Create YARN Service and Roles
logging.info('Creating YARN Service and Roles')
yarn = cluster.create_service("YARN", "YARN")
resourcemanager = yarn.create_role("YARN-rm", "RESOURCEMANAGER", clients[3].hostId)
jobhistory = yarn.create_role("YARN-jh", "JOBHISTORY", clients[1].hostId)
yarn_gateway = yarn.create_role("YARN-gw", "GATEWAY", clients[2].hostId)
yarn.create_role("YARN-nmm", "NODEMANAGER", cloudera_management_server.hostId)
for i in range(4):
    yarn.create_role("YARN-nm" + str(i), "NODEMANAGER", clients[i].hostId)

# Configure YARN Service
logging.info('Configuring YARN Services')
yarn_config = {
    'hdfs_service': 'HDFS',
    'zookeeper_service': 'ZooKeeper'
}
yarn_nodemanager_config = { 'yarn_nodemanager_local_dirs': '/yarn' }
yarn_gateway_config = { 'mapred_submit_replication': num_data_nodes }
yarn.update_config(svc_config=yarn_config)

for role in yarn.get_all_role_config_groups():
    if role.roleType == "NODEMANAGER":
        role.update_config(yarn_nodemanager_config)
    elif role.roleType == "GATEWAY":
        role.update_config(yarn_gateway_config)

# Create YARN JobHistory directory and remote app log directory
logging.info('Create YARN JobHistory directory and remote app log directory')
yarn.create_yarn_job_history_dir()
yarn.create_yarn_node_manager_remote_app_log_dir()

# Allow YARN JobHistory directory and remote app log directory creation to complete
time.sleep(20)

# Start YARN
logging.info('Starting YARN Service')
yarn.start().wait()

# Create Hive Service and Roles
logging.info('Creating Hive Service and Roles')
hive = cluster.create_service("Hive", "HIVE")
hive_server = hive.create_role("Hive-server", "HIVESERVER2", cloudera_management_server.hostId)
hive_metastore = hive.create_role("Hive-metastore", "HIVEMETASTORE", cloudera_management_server.hostId)
hive_webhcat = hive.create_role("Hive-webhcat", "WEBHCAT", clients[0].hostId)
hive.create_role("Hive-gatewaym", "GATEWAY", cloudera_management_server.hostId)
for i in range(4):
    hive.create_role("Hive-gateway" + str(i), "GATEWAY", clients[i].hostId)

# Configure Hive Service
logging.info('Configuring Hive Service')
hive_config = {
    'hive_metastore_database_user': hive_metastore_db_user,
    'hive_metastore_database_type': 'postgresql',
    'hive_metastore_database_host': hive_metastore_db_host,
    'hive_metastore_database_password': hive_metastore_db_password,
    'hive_metastore_database_name': hive_metastore_db_name,
    'hive_metastore_database_port': '5432',
    'hive_metastore_database_auto_create_schema': 'true',
    'hbase_service': 'HBase',
    'mapreduce_yarn_service': 'YARN',
    'zookeeper_service': 'ZooKeeper'
}
hive_server_config = { 'hiveserver2_spark_executor_cores': '4' }
hive.update_config(svc_config=hive_config)

for role in hive.get_all_role_config_groups():
    if role.roleType == "HIVESERVER2":
        role.update_config(hive_server_config)

# Create Hive user directory
logging.info('Creating Hive user directory in HDFS')
hive.create_hive_userdir()

# Allow Hive HDFS directory creation to complete
time.sleep(20)

# Create Hive database
logging.info('Creating Hive Metastore database')
hive.create_hive_metastore_tables()

# Allow Hive Metastore database creation to complete
time.sleep(40)

# Start Hive
logging.info('Starting Hive Service')
hive.start().wait()

# Create Oozie Service and Roles
logging.info('Creating Oozie Service and Roles')
oozie = cluster.create_service("Oozie", "OOZIE")
oozie_server = oozie.create_role("Oozie-sv", "OOZIE_SERVER", cloudera_management_server.hostId)

# Configure Oozie Services
logging.info('Configuring Oozie Service and Roles')
oozie_config = {
    'hive_service': 'Hive',
    'mapreduce_yarn_service': 'YARN',
    'zookeeper_service': 'ZooKeeper'
}
oozie_server_config = {
    'oozie_database_password': oozie_db_password,
    'oozie_database_type': 'postgresql',
    'oozie_database_user': oozie_db_user,
    'oozie_database_host': oozie_db_host,
    'oozie_database_name': oozie_db_name
}

oozie.update_config(svc_config=oozie_config)

for role in oozie.get_all_role_config_groups():
    if role.roleType == "OOZIE_SERVER":
        role.update_config(oozie_server_config)

# Create Oozie database tables
logging.info('Creating Oozie database tables')
oozie.create_oozie_db()

# Start Oozie
logging.info('Starting Oozie Service')
oozie.start().wait()


# Create Hue Service and Roles
logging.info('Creating Hue Services and Roles')
hue = cluster.create_service("Hue", "HUE")
hue_server = hue.create_role("Hue-sv", "HUE_SERVER", cloudera_management_server.hostId)
hue_lb = hue.create_role("Hue-lb", "HUE_LOAD_BALANCER", clients[2].hostId)

# Configure Hue Service
logging.info('Configuring Hue Service')
hue_config = {
    'database_host': hue_db_host,
    'database_name': hue_db_name,
    'database_password': hue_db_password,
    'database_port': '5432',
    'database_type': 'postgresql',
    'database_user': hue_db_user,
    'hive_service': 'Hive',
    'hue_webhdfs': 'HDFS-namenode',
    'oozie_service': 'Oozie',
    'zookeeper_service': 'ZooKeeper'
}
hue.update_config(svc_config=hue_config)

# Start Hue
logging.info('Starting Hue Service')
hue.start().wait()

# Redeploy client configs
logging.info('Redeploy client configurations')
cluster.deploy_client_config().wait()

logging.info('Stopping cluster')
cluster.stop().wait()

# # Perform cluster first run
logging.info('Starting cluster')
cluster.start().wait()

logging.info('Cluster Configuration Completed Successfully')
