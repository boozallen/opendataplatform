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
    logging.basicConfig(level=logging.INFO, filename="/root/cloudera_spark.log", filemode="a+",
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


# Create Spark Service and Roles
logging.info('Creating Spark Service and Roles')
spark = cluster.create_service("Spark", "SPARK_ON_YARN")
spark_jh = spark.create_role("Spark-jh", "SPARK_YARN_HISTORY_SERVER", cloudera_management_server.hostId)
spark_gw = spark.create_role("Spark-gwm", "GATEWAY", cloudera_management_server.hostId)
for i in range(4):
    spark.create_role("Spark-gw" + str(i), "GATEWAY", clients[i].hostId)

# Configure Spark Service
logging.info('Configuring Spark Service')
spark_config = {
    'yarn_service': 'YARN'
}

spark.update_config(spark_config)

# Start Spark
logging.info('Starting Spark Service')
spark.start().wait()

# Redeploy client configs
logging.info('Redeploy client configurations')
cluster.deploy_client_config().wait()

logging.info('Cluster Configuration Completed Successfully')
