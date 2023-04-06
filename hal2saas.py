import json
import argparse

parser = argparse.ArgumentParser(description='parse a halapi content endpoint and export batch import ready for a saas instance')
parser.add_argument('--source', action="store", required=True, help="location of source file")
parser.add_argument('--target', action="store", required=True, help="location of target file")
parser.set_defaults(feature=True)
args = parser.parse_args()

SOURCEFILE = args.source
TARGETFILE = args.target

# DOCSCHEMA = {
#     "contentType": "",
#     "displayName": "",
#     "fields": [],
#     "name": "",
#     "path": "",
#     "system": null,
#     "type": "document"
# }
# FIELDSCHEMA = {
#     "name": "",
#     "value": []
# },

OUTPUT_FIELDTYPES = [
  "String",
  "Boolean",
  "Integer",
  "Number",
  "Date",
  "Html",
  "RichText",
  "Link",
  "SelectableString",
  "EmbeddedResource",
  "Taxonomy",
  "FieldGroup",
  "GroupOfFieldGroups",
  "SelectableFieldGroup",
  "OpenUiExtension",
]

def getFieldType(field):
  # input - a HAL API field value
  # output - a valid batch import API field type

  if type(field) is dict and 'content' in field.keys():
    return "Html"

  if type(field) is str:
    return "String"

  if type(field) is list:
    return "FieldGroup"

  if type(field) is dict and '_meta' in field.keys() and 'type' in field['_meta'].keys() and 'hippo:mirror' in field['_meta']['type']:
      return "Link"

  if type(field) is int:
    return "Integer"

  if type(field) is bool:
    return "Boolean"

  if type(field) is float:
    return "Number"

def main():
  with open(SOURCEFILE) as data_file:
    data = json.load(data_file)
    targetfile = open(TARGETFILE, "w")
    for doc in data['_embedded']['documents']:
      
      # init target doc structure
      targetdoc = {}
      
      # determine doctype
      doctype = doc['_meta']['type']
      if doctype.startswith('staples'):

        # set document properties
        targetdoc['contentType'] = doc['_meta']['type'].replace('staplesconnect', 'rde')
        targetdoc['path'] = doc['_meta']['path']
        targetdoc['name'] = doc['_meta']['path'].split("/")[-1]
        targetdoc['displayName'] = doc['_meta']['name']
        targetdoc['type'] = "document"

        # create field list / iterate fields
        targetdoc['fields'] = []
        for k,v in doc.items():
          field = {}
          # process non 'meta' fields (no underscore _)
          if not k.startswith("_"):

            # field name is always the key
            field = {"name": k}

            # we have a straight string value, nothing else to do with this field
            if getFieldType(v) == "String":
              field['value'] = [v]

            # we have a dictionary with content (html field)
            elif getFieldType(v) == "Html":
              field['value'] = [v['content']]

            # we have an array (multi-value field)
            elif getFieldType(v) == "FieldGroup":
              #todo - handle fieldgroups
              #field['value'] = [v['content']]
              pass
            # maybe an image
            elif type(v) is dict and '_meta' in v.keys():

              # for sure an image
              if 'type' in v['_meta'].keys() and u'mirror' in v['_meta'].keys() and 'imagelink' in v['_meta']['type']:
                  field['value'] = v['_meta']['mirror']['path']

              # link to another document
              elif 'type' in v['_meta'].keys() and 'hippo:mirror' in v['_meta']['type']:
                pass

            # pass through value to field
            else:
              field['value'] = [v]
            targetdoc['fields'].append(field)
        targetfile.write(json.dumps(targetdoc))
        targetfile.write("\n")
    targetfile.close()

if __name__ == '__main__':
  main()

