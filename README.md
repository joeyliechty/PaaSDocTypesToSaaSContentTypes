# PaaSDocTypesToSaaSContentTypes
script to assist migrating from PaaS to SaaS

preparation:
install a few python libraries with pip
requests
PyYaml
argparse

generate a token from the saas instance and add to script constant "TOKEN"
set NAMESPACE constant to match your paas namespace

usage example:
python3 PaaSNamespace2SaaSContentType.py --si {{saas-instance-name}} --inputfile {{exported-namespace-yaml-node}} --project {{core/development}}
