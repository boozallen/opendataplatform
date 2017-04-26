# Open Data Platform
## Intent
Develop a converged open data platform that can be rapidly deployed and tailored to accelerate solution delivery

## Capabilities
* Package an open source [natural language processing](http://stanfordnlp.github.io/CoreNLP) (NLP) tool suite as a ready-to-use entity extraction capability using [Docker](https://www.docker.com/)
* Package an open source [geocoder library](https://github.com/foursquare/fsqio/tree/master/src/jvm/io/fsq/twofishes) as a ready-to-use geographical coordinate capability using [Docker](https://www.docker.com/)
* Orchestrate a data ingest workflow using [Apache NiFi](https://nifi.apache.org/) templates to leverage the containers described above
* Package the ingest workflow as a ready-to-use data ingest container

## Logical Architecture

![alt text](https://github.com/boozallen/opendataplatform/raw/master/docs/images/logical_arch.png "Logical Architecture")
