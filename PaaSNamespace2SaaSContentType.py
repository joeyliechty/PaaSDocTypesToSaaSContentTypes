import requests
import argparse
import yaml
import sys
import json
from pprint import pprint

parser = argparse.ArgumentParser(description='parse and slice a csv properly')
parser.add_argument('--si', action="store", required=True, help="subdomain of saas instance")
parser.add_argument('--inputfile', action="store", required=True, help="yaml namespace file")
parser.add_argument('--project', action="store", required=True, default="core", help="core/development")
args = parser.parse_args()
# generate token from SaaS instance
TOKEN = "add-token-here"
NAMESPACE = "myproject"
# this lookup table maps the hipposysedit:type property to the applicable basic displayType for the contentTypeMGMT API
CONTENT_TYPE_TO_DISPLAY_TYPE = {
  "Boolean": "Checkbox",
  "String": "Simple",
  "Date": None,
  "Html": None,
}
print("Processing {} namespace into SaaS instance {}, project: {}\n".format(args.inputfile, args.si, args.project))

contentTypeAPI = "https://{}.bloomreach.io/management/contenttypes/v1/{}".format(args.si, args.project)
headers = {
  "accept": "application/json",
  "content-type": "application/json",
  "x-auth-token": TOKEN
}

def contentTypeExists(contentTypeName):
  getContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  response = requests.get(contentTypeAPI, headers=headers)
  for x in response.json():
    if x["name"].lower() == contentTypeName.lower():
      return True
  return False

def createContentType(contentTypeName, contentType, fields=[]):
  createUpdateContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  if contentTypeExists(contentTypeName):
    print("{} already exists, skipping...".format(contentTypeName))
    return False
  else:
    # edit this data structure for the fields/etc
    payload = {
      "presentation": {
        "layout": 'one-column',
        "displayName": contentTypeName
      },
      "type": contentType,
      "enabled": True,
      "name": contentTypeName.lower().replace(" ", "-"),
      "fields": fields
    }
    response = requests.put(createUpdateContentTypeEndpoint, json=payload, headers=headers)
    print(response.status_code)
    print(response.text)

def parseFieldsFromYamlObject(nodetypeRoot):
  fields = []
  for k,v in nodetypeRoot.items():
    print("key: {}\nvalue: {}\n\n".format(k,v))
    if k.startswith("/"):
      required = False
      if v['hipposysedit:mandatory'] == "true":
        required = True
      field = {
        "name": k[1:],
        "required": required,
        "type": v['hipposysedit:type'],
        "presentation": {
          "caption": k[1:],
          "hint": "placeholder",
          "layoutColumn": 1,
        }
      }
      if CONTENT_TYPE_TO_DISPLAY_TYPE[v['hipposysedit:type']] != None:
        field['presentation']['displayType'] = CONTENT_TYPE_TO_DISPLAY_TYPE[v['hipposysedit:type']]
      fields.append(field)
  return fields

# identify custom compounds (type: FieldGroup)
FieldGroups = []
# create custom compounds
# identify doctypes (type: Document)
Documents = []
# create doctypes
with open(args.inputfile, "r") as stream:
  try:
    yaml = yaml.safe_load(stream)
    for key, value in yaml['/{}'.format(NAMESPACE)].items():

      # contentTypeName
      if key.startswith('/'):
        contentTypeName = key[1:]
      # layout - one-column, etc
      # passthru for now

      # iterate fields
        if '/hipposysedit:nodetype' in value.keys() and '/hipposysedit:nodetype' in value['/hipposysedit:nodetype'].keys():
          if "hippo:compound" in value['/hipposysedit:nodetype']['/hipposysedit:nodetype']['hipposysedit:supertype']:
            # iterate field object
            fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'])
            print("Creating FieldGroup: {}".format(contentTypeName))
            createContentType(contentTypeName, "FieldGroup", fields)
          elif "{}:basedocument".format(NAMESPACE) in value['/hipposysedit:nodetype']['/hipposysedit:nodetype']['hipposysedit:supertype']:
            fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'])
            print("Creating Document: {}".format(contentTypeName))
            createContentType(contentTypeName, "Document", fields)
          print("=================\n")
  except yaml.YAMLError as exc:
    print(exc)



print("Creating Documents:")
