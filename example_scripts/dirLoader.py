import os
import re
import sys
import time
from pysqvd import SQVD

'''
Simple loading script from directory structure
root/<group>/workflow/panelid+version/sample/BAM+VCF+BEDGRAPH
'''

def main(host, user, passwd, directory, dwell_time):
    # configure the API connection
    sqvd = SQVD(username=user, password=passwd, host=host)

    # automatically logs in and out
    with sqvd:

        for root, dirs, files in os.walk(directory, topdown=False):
            p = root[len(directory):].strip('/').split("/")
            if len(p) == 4:
                # get files
                jsns = list([f for f in files if f.endswith('.json')])
                bams = list([f for f in files if f.endswith('.bam')])
                vcfs = list([f for f in files if f.endswith('.vcf.gz')])
                beds = list([f for f in files if f.endswith('.bed')])
                bedg = list([f for f in files if f.endswith('.bedgraph')])
                bigw = list([f for f in files if f.endswith('.bw')])
                upload_files = list([f'{root}/{f}' for f in
                                     jsns + bams + vcfs + beds + bedg + bigw])
                # get study
                group, workflow, panel, sample = p
                m = re.match(r'([A-Za-z]+)(\d+)$', panel)
                if m and upload_files:
                    # create study object
                    panel_name, panel_version = m.groups()
                    study_name = f'{sample}_{panel}'
                    study_object = {
                        'study_name': study_name,
                        'sample_id': sample,
                        'panel_id': panel_name,
                        'panel_version': int(panel_version),
                        'workflow': workflow,
                        'subpanels': [],
                        'group': group,
                        'dataset_name': ""
                    }
                    print(f"## {study_name} ({len(upload_files)} files)")
                    # create or fetch study (by name)
                    try:
                        study = sqvd.createStudy(study_object)
                        sqvd.upload(upload_files, study_name)
                        print(f'Uploaded {len(upload_files)} files for {study_name}')
                    except:
                        studies = sqvd.rest('study', data={'study_name': study_name})
                        study = studies['data'][0]
                        print(f"Study {study_name} already exists! -> Skipping")
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
            python dirLoader.py <DIRECTORY>

            The directory structure must be like GROUP/WORKFLOW/TESTANDVERSION/SAMPLE/files.
            eg. genetics/dna_somatic/SWIFT1/ACCRO/*.(vcf.gz|bam|bed|bedgraph)

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
