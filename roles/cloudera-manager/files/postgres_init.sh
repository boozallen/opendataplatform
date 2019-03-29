#!/bin/bash

# Copyright: (c) 2019, Booz Allen Hamilton
# Booz Allen Public License v1.0 (see LICENSE or http://boozallen.github.io/licenses/bapl)

# Check if Cloudera user exists in Postgres and create user, password and database if not found
if [[ $(su -c "psql -c \"select exists(select 1 from pg_roles where rolname='cloudera_scm')\"" - postgres | head -3 | tail -1 | tr -d '[:space:']) = "f" ]]; then

  # Create Cloudera user, password and database
  su -c "createuser -d -l -r -s cloudera_scm" - postgres
  su -c "psql -c \"ALTER USER cloudera_scm PASSWORD '${1}'\"" - postgres
  su -c "createdb -O \"cloudera_scm\" clouderadb" - postgres

  # Create databases for Cloudera Management Service Services
  su -c "createdb -O \"cloudera_scm\" firehose" - postgres
  su -c "createdb -O \"cloudera_scm\" headlamp" - postgres

  # Create Hive user, password and database
  su -c "createuser -d -l -r -s hiveuser" - postgres
  su -c "psql -c \"ALTER USER hiveuser PASSWORD '${2}'\"" - postgres
  su -c "createdb -O \"hiveuser\" metastore" - postgres

  # Create Hue user, password and database
  su -c "createuser -d -l -r -s hueuser" - postgres
  su -c "psql -c \"ALTER USER hueuser PASSWORD '${3}'\"" - postgres
  su -c "createdb -O \"hueuser\" huedb" - postgres

  # Create Ooozie user, password and database
  su -c "createuser -d -l -r -s oozieuser" - postgres
  su -c "psql -c \"ALTER USER oozieuser PASSWORD '${4}'\"" - postgres
  su -c "createdb -O \"oozieuser\" ooziedb" - postgres

fi

exit 0
