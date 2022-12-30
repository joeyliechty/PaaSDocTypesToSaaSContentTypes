import requests
import argparse
import yaml
import sys
import json
from pprint import pprint
import os

parser = argparse.ArgumentParser(description='parse a yaml namespace and PUT to a saas instance')
parser.add_argument('--sourceDomain', action="store", required=True, help="subdomain of source saas instance")
parser.add_argument('--targetDomain', action="store", required=True, help="subdomain of target saas instance")
parser.add_argument('--sourceToken', action="store", required=True, help="token")
parser.add_argument('--targetToken', action="store", required=True, help="token")

parser.add_argument('--project', action="store", required=False, default="development", help="core/development")
parser.add_argument('--prefix', action="store", required=False, help="namespace prefix (for multi-tenant SaaS instances)")
parser.add_argument('--delta', action="store_true", required=False, help="if used, will merely show the delta between the source and target environments.")

parser.add_argument('--dryrun', action='store_true')
parser.add_argument('--no-dryrun', dest='dryrun', action='store_false')
parser.set_defaults(feature=True)
args = parser.parse_args()

# generate tokens from SaaS instances
SOURCETOKEN = args.sourceToken
TARGETTOKEN = args.targetToken

sourceContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}".format(args.sourceDomain, args.project)
targetContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}".format(args.targetDomain, args.project)
sourceHeaders = {
  "accept": "application/json",
  "content-type": "application/json",
  "x-auth-token": SOURCETOKEN
}
targetHeaders = {
  "accept": "application/json",
  "content-type": "application/json",
  "x-auth-token": TARGETTOKEN
}

def hasDevelopmentProjectWithContentTypeChanges():
  getContentTypeEndpoint = targetContentTypeEndpoint + "/anythingHere"
  response = requests.get(getContentTypeEndpoint, headers=targetHeaders)
  if response.status_code == 404 and "no development project" in response.text:
    return False
  else:
    return True

def getAllContentTypes(sourceContentTypeEndpoint):
  response = requests.get(sourceContentTypeEndpoint, headers=sourceHeaders)
  if response.status_code == 200:
    return response.json()
  else:
    print("status code {}: is your token active?".format(response.status_code))
  return False

def containsFieldGroup(fields):
  for f in fields:
    if f['type'] == "FieldGroup":
      return True
  return False

def getFieldGroupNames(fields):
  fieldGroupNames = []
  for f in fields:
    if f['type'] == "FieldGroup":
      fieldGroupNames.append(f['fieldGroupType'])
  return fieldGroupNames

def contentTypeExists(contentTypeName):
  getContentTypeEndpoint = targetContentTypeEndpoint + "/{}".format(contentTypeName)
  print(getContentTypeEndpoint)
  response = requests.get(getContentTypeEndpoint, headers=targetHeaders)
  if response.status_code == 200:
    responseJson = response.json()
    if responseJson["name"].lower() == contentTypeName.lower():
      return True
  else:
    print("status code {}: is your token active?".format(response.status_code))
  return False

def createContentType(jsonBlob):
  j = jsonBlob
  createUpdateContentTypeEndpoint = targetContentTypeEndpoint + "/{}".format(j['name'])
  # first, if it exists already, skip it.
  if contentTypeExists(j['name']):
    print("skip:\t{}\t{}\talready exists in target instance".format(j['type'], j['name']))
    return False
  # then, if it contains fieldgroups which do not yet exist, skip it.
  if containsFieldGroup(j['fields']):
    for fg in getFieldGroupNames(j['fields']):
      if not contentTypeExists(fg):
        print("FieldGroup {} does not yet exist, skipping {}...".format(fg, j['name']))
        return False
  response = requests.put(createUpdateContentTypeEndpoint, json=j, headers=targetHeaders)
  print("STATUS CODE: {}".format(response.status_code))
  print("RESPONSE TEXT: {}".format(response.text))
  return response

if __name__ == "__main__":
  print("Migrating content types from {} into {}\n".format(args.sourceDomain, args.targetDomain))
  if args.dryrun:
    print("DRY RUN MODE ENABLED: DISABLE TO COMMIT TO SAAS INSTANCE\nTHESE ARE THE POTENTIAL CONTENT TYPES")
  if hasDevelopmentProjectWithContentTypeChanges():
    NODRYRUNOK = True
  else:
    print("There is not a development project with content type changes, please create one in the UI first.\nExiting Script.")
    sys.exit()

  # if we cancel the dry run, create in SaaS
  alljson = getAllContentTypes(sourceContentTypeEndpoint)
  if NODRYRUNOK and not args.dryrun:
    for jsonBlob in alljson:
      print(jsonBlob['name'])
      if ":" not in jsonBlob['name']:
        createContentType(jsonBlob)
  elif args.dryrun:
    for jsonBlob in alljson:
      pprint(jsonBlob)