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
parser.add_argument('--dryrun', action="store", required=False, default=True, help="use false to commit the result to the SaaS instance")
args = parser.parse_args()
# generate token from SaaS instance
TOKEN = "add-token-here"
NAMESPACE = "myproject"

# this lookup table maps the hipposysedit:type property to the applicable displayType for the contentTypeMGMT API
CONTENT_TYPE_TO_DISPLAY_TYPE = {
  "Boolean": "Checkbox",
  "selection:BooleanRadioGroup": "RadioGroup",
  "CalendarDate": None,
  "Double": None,
  "Docbase": "AnyLink",
  "DynamicDropdown": "Dropdown",
  "Long": None,
  "OpenUiString": None,
  "selection:RadioGroup": None,
  "StaticDropdown": None,
  "String": "Simple",
  "Text": "Text",
  "Date": None,
  "Html": None,
  "hippostd:html": None,
  "hippogallerypicker:imagelink": "ImageLink",
  "hippo:resource": "AnyLink",
  "hippo:mirror": "AnyLink",
  "selection:listitem": None,
}

print("Processing {} namespace into SaaS instance {}, project: {}\n".format(args.inputfile, args.si, args.project))

contentTypeAPI = "https://{}.bloomreach.io/management/contenttypes/v1/{}".format(args.si, args.project)
headers = {
  "accept": "application/json",
  "content-type": "application/json",
  "x-auth-token": TOKEN
}

def containsFieldGroup(fields):
  for f in fields:
    if f['type'] == "FieldGroup":
      return True
  return False

def contentTypeExists(contentTypeName):
  getContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  response = requests.get(contentTypeAPI, headers=headers)
  for x in response.json():
    if x["name"].lower() == contentTypeName.lower():
      return True
  return False

def createContentType(contentTypeName, contentType, fields):
  createUpdateContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  if contentTypeExists(contentTypeName):
    print("{} already exists, skipping...".format(contentTypeName))
    return False
  elif containsFieldGroup(fields) and not contentTypeExists(fieldGroup):
    print("{} does not yet exist, skipping...".format(contentTypeName))
    return False
  else:
    # edit this data structure for the fields/etc
    payload = {
      "presentation": {
        # hardcoding one-column for now for simplicity.
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

with open(args.inputfile, "r") as stream:
  try:
    yaml = yaml.safe_load(stream)
    for key, value in yaml['/{}'.format(NAMESPACE)].items():

      # contentTypeName
      if key.startswith('/'):
        contentTypeName = key[1:]
        # iterate fields
        if '/hipposysedit:nodetype' in value.keys() and '/hipposysedit:nodetype' in value['/hipposysedit:nodetype'].keys():
          if "hippo:compound" in value['/hipposysedit:nodetype']['/hipposysedit:nodetype']['hipposysedit:supertype']:
            # iterate field object
            fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'])
            print("FieldGroup: {}".format(contentTypeName))
            if args.dryrun:
              print("DRY RUN MODE ENABLED: DISABLE TO COMMIT TO SAAS INSTANCE\nTHESE ARE THE POTENTIAL FIELDS")
              print(fields)
            else:
              createContentType(contentTypeName, "FieldGroup", fields)
          elif "{}:basedocument".format(NAMESPACE) in value['/hipposysedit:nodetype']['/hipposysedit:nodetype']['hipposysedit:supertype']:
            fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'])
            print("Document: {}".format(contentTypeName))
            if args.dryrun:
              print("DRY RUN MODE ENABLED: DISABLE TO COMMIT TO SAAS INSTANCE\nTHESE ARE THE POTENTIAL FIELDS")
              print(fields)
            else:
              createContentType(contentTypeName, "Document", fields)
  except yaml.YAMLError as exc:
    print(exc)
