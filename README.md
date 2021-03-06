# pySQVD

This python module provides a convenience API for SQVD. REST API documentation is included.

> TODO: Remove import url paramter (assets assigned to study should always imported)
> TODO: Add PDF and BW file uploads

## Installation
pySQD requires the `request` module. Compatible with python 2.7 and 3.0+

Install with: `pip install .`

## Features
### DONE
* Authenticate with SQVD (token based)
* GET/POST/DELETE for study,sample,track,panel
* query parameter support for filtering/searching
* upload VCF and BED files (for BAM files use the REST API)
### TODO
* Find tests by state
* Trigger events

## REST endpoints

All endpoints are authenticated and group (user) restricted.
Only users with **_API_** role are being authorised.
Valid methods are GET, POST, DELETE.
GET requests support query paramaters (eg. /api/v1/study?study_name=mystudy)

API root: `/api/v1`

| Resource | Endpoint                   | Methods         | Notes                            |
| -------- | -------------------------- | --------------- | -------------------------------- |
| Study    | /api/v1/study/:id          | GET,POST,DELETE | Studies (tests)                  |
| Sample   | /api/v1/sample/:id         | GET,POST,DELETE | Samples                          |
| Track    | /api/v1/sample/:id         | GET,POST,DELETE | Workflows                        |
| Sample   | /api/v1/sample/:id         | GET,POST,DELETE | Panels and subpanels             |
| VCF      | /api/v1/study/:id/vcf      | POST            | Upload VCF files (VCF v4.2 spec) |
| BED      | /api/v1/study/:id/bed      | POST            | Upload BED files (intervals)     |
| BEDGRAPH | /api/v1/study/:id/bedgraph | POST            | Upload BEDGRAPH (coverage)       |
| BAM      | /api/v1/study/:id/bed      | POST            | Upload BAM files                 |

## File uploads
### Query parameters

The upload endpoints do not automatically parse and import the files into the database. Use `import` query argument to enable file parsing. (eg. `http://localhost:3000/api/v1/study/9zu9BHRGZH2DNSLde/vcf?import=true`). The python wrapper will automatically import VCF files only.

You can assign a data type to each uploaded file with the `type` query parameter. This is useful if multiple BED files are uploaded.

Uploaded files are renamed to the study's name (`study_name`). To override this, supply a `name` query parameter (without file extension).

### Import parsers

| File     | Import action                                            | Status |
| -------- | -------------------------------------------------------- | ------ |
| VCF      | Insert VCFv4.2 variants into database                    | DONE   |
| BED      | Inserts IntervalSet into database                        | DONE   |
| BEDGRAPH | Calculate coverage over target regions                   | WIP    |
| BAM      | Calculate limit of detection based on MQ,BQ and coverage | WIP    |

### Limitations
All uploads are currently limited to 200Mb. Imports of BED files are size limited as they are stored in a single document in the database (BSON limit 16Mb). Split into multiple files to overcome this.


## Examples

### pySQVD

```
from pysqd import SQVD

# configure the API connection
sqvd = SQVD(username=sys.argv[1], password=sys.argv[2], host='127.0.0.1:3000')

# automatically logs in and out
with sqvd:
    # upload files and assign to study
    vcfFile = '/path/to/vcf/file'
    bedFile = '/path/to/bed/file'
    study_id = "9zu9BHRGZH2DNSLde"
    sqvd.upload([vcfFile,bedFile],study_id)

    # get all studies
    allStudies = sqvd.rest('study')

    # search study by name
    studies = sqvd.rest('study',data={'study_name': study['data']['study_name']})

    # get study by id
    studyById = sqvd.rest('study','GET',"9zu9BHRGZH2DNSLde")

    # create new study and sample
    obj = {
      'study_name': 'swampletest',
      'sample_id': 'swample',
      'panel_id': 'RCGP',
      'panel_version': 4,
      'workflow': 'dna_somatic',
      'subpanels': [ 'SEX', 'SG' ],
      'group': 'haemonc'
    }
    study = sqvd.createStudy(obj)
```

### cURL

Authenticate with the REST API. Returns authtication token and userId:

```
curl localhost:3000/api/v1/login -d "username=yourUsername&password=yourDarkestSecrets"
```

Upload VCF file and assign to study:

```
curl -X POST -H "X-User-Id: JDPqFBtgzWRZvMRiv" -H "X-Auth-Token: XI-KvLyHDLCNx9gpXfdR5eVySht2J2mPXBbf5mj_m05" -H "Content-Type: application/gz" --data-binary "@../../web/imports/api/assets/data/cancer.vcf.gz" http://localhost:3000/api/v1/study/9zu9BHRGZH2DNSLde/vcf
```
