import os
import re
import sys
import time
import json
from pysqvd import SQVD
from collections import defaultdict
'''
Simple loading script from directory structure of snappy v3.x.x (rcgp)
RUNFOLDER/<sample>/<RUNID>/BAM+VCF+BEDGRAPH
'''

GROUP = "molpath"
RUNID = "default"
PANEL_ID = "RCGP"
PANEL_VERSION = "4"
WORKFLOW = "dna_germline"
FILE_PATTERNS = (
    re.compile(r'.{8}\.merged\.vcf$'),  # VCF
    re.compile(r'.{8}\.dupemk\.bam$'),  # BAM
    re.compile(r'.{8}\.coverage\.bedgraph$'),  # BEDGRAPH
    re.compile(r'.{8}\.exomedepth\.pdf$'),  # CNV REPORT
    re.compile(r'.{8}\.metricsreport\.pdf$'), # METRICS REPORT
)

def isComplete(files,expected):
    missed_ids = list(range(expected))
    for i,f in files:
        if i in missed_ids:
            missed_ids.remove(i)
    return not missed_ids

def compress_vcf(file):
    if file.endswith('.vcf'):
        newfile = file + '.gz'
        os.system(" ".join(["bgzip -c", file, ">", newfile]))
        return newfile
    return file

def main(host, user, passwd, directory, dwell_time):
    # find files to upload
    sample_files = defaultdict(list)
    sample_study = {}
    for root, dirs, files in os.walk(directory, topdown=False):
        p = root[len(directory):].strip('/').split("/")
        if len(p) >= 2 and p[1] == RUNID:
            sample = p[0]
            # extract panel information and build study object
            if '.config.json' in files and not os.path.islink(os.path.join(root,'.config.json')):
                with open(os.path.join(root, '.config.json')) as f:
                    config = json.load(f)
                    panel = config['ngsAnalysis'].upper()
                    m = re.match(r'^([A-Z]+)(\d+)$',panel)
                    if m:
                        panel_id, panel_version = m.groups()
                        sample_study[sample] = {
                            'study_name': f'{sample}_{panel_id}{panel_version}',
                            'sample_id': sample,
                            'panel_id': panel_id,
                            'panel_version': int(panel_version),
                            'workflow': WORKFLOW,
                            'subpanels': [],
                            'group': GROUP,
                            'dataset_name': ""
                        }
            # match files to upload 
            for f in files:
                for i, pattern in enumerate(FILE_PATTERNS):
                    if pattern.match(f):
                        filepath = os.path.join(root,f)
                        if not os.path.islink(filepath):
                            sample_files[sample].append((i, filepath))
                            break
    print(sample_files)
    print(sample_study)
    
    # automatically logs in and out
    with SQVD(username=user, password=passwd, host=host) as sqvd:
        for sample in sample_files:
            print('Processing',sample)
            upload_files = sample_files[sample]
            # check completeness
            if isComplete(upload_files, len(FILE_PATTERNS)) and sample in sample_study.keys():
                study_object = sample_study[sample]
                print(f"## {study_object['study_name']} ({len(upload_files)} files)")
                # create or fetch study (by name)
                studies = sqvd.rest('study', data={'study_name': study_object['study_name']})
                if len(studies['data']):
                    print(f"Study {study_object['study_name']} already exists! -> Skipping")
                else:
                    # create study
                    study = sqvd.createStudy(study_object)
                    files_to_upload = list(map(lambda x: compress_vcf(x[1]), upload_files))
                    print(files_to_upload)
                    sqvd.upload(files_to_upload, study_object['study_name'], {"skip": "processing"})
                    print(f"Uploaded {len(upload_files)} files for {study_object['study_name']}")
                time.sleep(dwell_time)


if __name__ == "__main__":
    # grab username and password
    user = os.environ.get("SQVDUSER", default="admin")
    passwd = os.environ.get("SQVDPASS", default="Kings123")
    host = os.environ.get("SQVDHOST", default="localhost:3000/sqvd")
    try:
        assert user and passwd and host
        root = sys.argv[1].rstrip('/')
        assert os.path.isdir(root)
    except Exception:
        print("""
            python runLoader.py <RUN_FOLDER> [DWELL_TIME]

            e.g. python runLoader.py /srv/work/analysis/RCP999

            The directory structure must follow snappy's conventions.
            The dwell time specifies how long to wait between uploads. (default: 0s)
            
            Ensure SQVDUSER, SQVDPASS, SQVDHOST env variables are set!
        """)
    else:
        # dwell time between directories
        dwell = 0
        try:
            dwell = int(sys.argv[2])
        except Exception:
            pass
        main(host, user, passwd, root, dwell)
