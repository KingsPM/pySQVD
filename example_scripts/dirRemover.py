import os
import re
import sys
from pysqvd import SQVD

'''
Deletes studies created from a directory stucture.
Essentially rolls back a dirLoader call.
root/<group>/workflow/panelid+version/sample/BAM+VCF+BEDGRAPH
'''

def main(host, user, passwd, directory):
  # configure the API connection
  sqvd = SQVD(username=user, password=passwd, host=host)

  # automatically logs in and out
  with sqvd:
    for root, dirs, files in os.walk(directory,topdown=False):
      p = root[len(directory):].strip('/').split("/")
      if len(p) == 4:
        # get study
        group, workflow, panel, sample = p
        if panel and sample:
          ## create study object
          study_name = f'{sample}_{panel}'
          print(f"## {study_name}")
          ## create or fetch study (by name)
          study = sqvd.deleteStudy(study_name)
          if study:
            print(f'Deleted {study_name}.')
          else:
            print(f"Study {study_name} NOT deleted!")

if __name__ == "__main__":
  # grab username and password
  user = os.environ.get("SQVDUSER", default="admin")
  passwd = os.environ.get("SQVDPASS", default="Kings123")
  host = os.environ.get("SQVDHOST", default="localhost:3000/sqvd")
  try:
    assert user and passwd and host
    root = sys.argv[1].rstrip('/')
    assert os.path.isdir(root)
  except:
    print("""
      python dirRemover.py <DIRECTORY>

      The directory structure must be like GROUP/WORKFLOW/TESTANDVERSION/SAMPLE/files.
      eg. genetics/dna_somatic/SWIFT1/ACCRO/*.(vcf.gz|bam|bed|bedgraph)

      Ensure SQVDUSER, SQVDPASS, SQVDHOST env variables are set!
    """)
  else:
    main(host,user,passwd,root)
