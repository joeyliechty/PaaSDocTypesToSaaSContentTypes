import requests
import argparse
import yaml
import sys
import json
from pprint import pprint

parser = argparse.ArgumentParser(description='parse a yaml namespace and PUT to a saas instance')
parser.add_argument('--si', action="store", required=True, help="subdomain of saas instance")
parser.add_argument('--inputfile', action="store", required=True, help="yaml namespace file")
parser.add_argument('--project', action="store", required=True, default="core", help="core/development")
parser.add_argument('--namespace', action="store", required=True, help="input project namespace")
parser.add_argument('--token', action="store", required=True, help="token")
parser.add_argument('--dryrun', action='store_true')
parser.add_argument('--no-dryrun', dest='dryrun', action='store_false')
parser.set_defaults(feature=True)
args = parser.parse_args()
# generate token from SaaS instance
TOKEN = args.token
# namespace from input file
NAMESPACE = args.namespace

# these lookup tables map the hipposysedit:type property to the applicable type and displayType for the contentTypeMGMT API
DOC_TYPE_TO_CONTENT_TYPE = {
  "selection:BooleanRadioGroup": "Boolean",
  "CalendarDate": "Date",
  "Double": "Number",
  "Docbase": "Link",
  "DynamicDropdown": "SelectableString",
  "StaticDropdown": "SelectableString",
  "selection:RadioGroup": "SelectableString",
  "Long": "Integer",
  "OpenUiString": "OpenUiExtension",
  "Text": "String",
  "hippogallerypicker:imagelink": "Link",
  "hippo:mirror": "Link",
  "hippo:resource": "Link",
  "hippostd:html": "Html",
  "selection:listitem": "SelectableString",
}

CONTENT_TYPE_TO_DISPLAY_TYPE = {
  "Boolean": "Checkbox",
  "CalendarDate": None,
  "Double": None,
  "Docbase": "AnyLink",
  "DynamicDropdown": "Dropdown",
  "SelectableString": "Dropdown",
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

def hasDevelopmentProjectWithContentTypeChanges(contentTypeName):
  getContentTypeEndpoint = contentTypeAPI + "/{}".format(contentTypeName)
  response = requests.get(contentTypeAPI, headers=headers)
  if response.status_code == 404 and "no development project" in response.text:
    return False
  else:
    return True

def containsFieldGroup(fields):
  for f in fields:
    if f['type'] == "FieldGroup":
      return True
  return False

def getFieldGroupNames(fields):
  fieldGroupNames = []
  for f in fields:
    if f['type'] == "FieldGroup":
      fieldGroupNames.append(f['name'])
  return fieldGroupNames

def contentTypeExists(contentTypeName):
  getContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  response = requests.get(contentTypeAPI, headers=headers)
  for x in response.json():
    if x["name"].lower() == contentTypeName.lower():
      return True
  return False

def createContentType(contentTypeName, contentType, fields):
  createUpdateContentTypeEndpoint = "https://{}.bloomreach.io/management/contenttypes/v1/{}/{}".format(args.si, args.project, contentTypeName)
  if containsFieldGroup(fields):
    for fg in getFieldGroupNames(fields):
      if not contentTypeExists(fg):
        print("FieldGroup {} does not yet exist, skipping...".format(fg))
        return False
  if contentTypeExists(contentTypeName):
    print("ContentType {} already exists, skipping...".format(contentTypeName))
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
      "name": contentTypeName,
      "fields": fields
    }
    print(payload)
    response = requests.put(createUpdateContentTypeEndpoint, json=payload, headers=headers)
    print(response.status_code)

def parseFieldsFromYamlObject(nodetypeRoot, editorTemplatesRoot):
  fields = []
  for k,v in nodetypeRoot.items():
    if k.startswith("/"):
      required = False
      if v.get('hipposysedit:mandatory') == 'true':
        required = True
      field = {
        "name": k[1:],
        "required": required,
        "type": v.get('hipposysedit:type'),
        "presentation": {
          "layoutColumn": 1,
        }
      }
      # handle type edgecases
      if DOC_TYPE_TO_CONTENT_TYPE.get(field['type']):
        field['type'] = DOC_TYPE_TO_CONTENT_TYPE[field['type']]
        if CONTENT_TYPE_TO_DISPLAY_TYPE.get(field['type']):
          field['presentation']['displayType'] = CONTENT_TYPE_TO_DISPLAY_TYPE[field['type']]
      # handle hints and captions
      for etrItem in editorTemplatesRoot.items():
        if type(etrItem[1]) is dict and etrItem[0] == k:
          if etrItem[1].get('hint') != '':
            field['presentation']['hint'] = etrItem[1].get('hint')
          if etrItem[1].get('caption') != '':
            field['presentation']['caption'] = etrItem[1].get('caption')
        # we found a standard field mapping to display type
      if CONTENT_TYPE_TO_DISPLAY_TYPE.get(v['hipposysedit:type']):
        field['presentation']['displayType'] = CONTENT_TYPE_TO_DISPLAY_TYPE[v['hipposysedit:type']]
        if field['presentation']['displayType'] == 'RadioGroup':
          field['presentation']['inValues'] = ['True', 'False']
      # we found a inherited compound type / fieldgroup
      elif v['hipposysedit:type'].startswith(NAMESPACE):
        field['type'] = "FieldGroup"
        field['fieldGroupType'] = field['name']
      fields.append(field)
  return fields

if __name__ == "__main__":
  FieldGroups = []
  Documents = []
  if args.dryrun:
    print("DRY RUN MODE ENABLED: DISABLE TO COMMIT TO SAAS INSTANCE\nTHESE ARE THE POTENTIAL FIELDS")
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
              fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'], value['/editor:templates']['/_default_'])
              FieldGroups.append([contentTypeName, fields])
            elif "{}:basedocument".format(NAMESPACE) in value['/hipposysedit:nodetype']['/hipposysedit:nodetype']['hipposysedit:supertype']:
              fields = parseFieldsFromYamlObject(value['/hipposysedit:nodetype']['/hipposysedit:nodetype'], value['/editor:templates']['/_default_'])
              Documents.append([contentTypeName, fields])
    except yaml.YAMLError as exc:
      print(exc)
  if hasDevelopmentProjectWithContentTypeChanges('foobar'):
    NODRYRUNOK = True
  else:
    print("There is not a development project with content type changes, please create one in the UI first.\nExiting Script.")
    sys.exit()

  # if we cancel the dry run, create in SaaS
  if NODRYRUNOK and not args.dryrun:
    print("Creating Field Groups:")
    for fg in FieldGroups:
      createContentType(fg[0], "FieldGroup", fg[1])
    print("Creating Document Types:")
    for d in Documents:
      createContentType(d[0], "Document", d[1])
  elif args.dryrun:
    for fg in FieldGroups:
      print("{}\n{}".format(fg[0],fg[1]))
    for d in Documents:
      print("{}\n{}".format(d[0],d[1]))

