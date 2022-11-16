
# PaaSDocTypesToSaaSContentTypes
This script can assist with migrating Bloomreach Content Types from PaaS to SaaS
## Preparation:
### Install python libraries
This script is written in Python.
You will need to install a few python libraries with pip.
`requests, PyYaml, argparse`
typically this can be done like `pip install {{library}}` but ymmv.

### Generate a token from the saas instance
After logging into the SaaS environment, navigate to Setup > brXM API token management.
Click the "+ API Token" button and give it all the read/write credentials, for simplicity.
You wont use them all for this script, but it is simpler.
Save the token for when invoking the script, it will look like a UUID.

### Create a development project
This script requires a development project (with content type changes) to be created in the SaaS environment.
After logging into the SaaS instance, navigate to "Projects"
Give it any name you wish, and tick both the "development project" and "include content type changes" boxes.
If you see that the "include content type changes" tickbox is grayed out, that means a development project with content type changes already exists.
You can only have one active per SaaS instance.
Consider if you would like to use the existing one, or delete it and create a new one.

### Export your namespace from the PaaS instance
In your PaaS environment, navigate to `/cms/console`
Expand the `hippo:namespaces` node on the left nav.
There are many namespaces in any PaaS environment, but we will only want to be exporting one at a time for this process.
Right click your entity's namespace, and click "YAML Export"
Click "Download ZIP" in the popup modal window.
Extract the zip file and note the location of the resultant `.yaml` file.

## Invoke the script
This script does a few things:
1. parses a yaml namespace from a PaaS instance
2. translates those definitions into payloads for the ContentType Mgmt API of a SaaS instance
3. PUTs those payloads to the appropriate API endpoint

Note: There is a "dry run" mode that should be ran first to appropriately investigate the payloads which will create content types in the target SaaS instance.
EXTRA IMPORTANT NOTE: Once you *mint* a content type in a SaaS instance, it cannot be removed, hidden, or otherwise purged from the system. *USE THE DRY RUN MODE*. Test it out in a sandbox environment before you run this on your main instance. **I cannot stress that enough.**

usage example:
```
python3 PaaSNamespace2SaaSContentType.py
  --si {{saas instance name}}
  --inputfile {{path to exported namespace yaml file}}
  --project {{core / development}}
  --token {{token from saas environment}}
  --namespace {{namespace from exported yaml}}
  --dryrun # use --no-dryrun to commit to SaaS instance
```
