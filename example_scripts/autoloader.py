#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import requests
import hashlib
import json
from datetime import datetime, timedelta
import os
import time
import re
from pysqvd import SQVD

__author__ = "David Brawand"
__credits__ = ['David Brawand']
__license__ = "MIT"
__maintainer__ = "David Brawand"
__email__ = "dbrawand@nhs.net"


if __name__ == "__main__":
    import sys
    if (len(sys.argv) < 2):
        print('test with USERNAME PASSWORD VCF as arguments')
        sys.exit(1)

    vcf_file = sys.argv[1]

    sqvd = SQVD(username=os.getenv("SQVDAPIUSER"),
                password=os.getenv("SQVDAPIPASS"),
                host=os.getenv("SQVDAPIHOST"))

    with sqvd:
        ids = vcf_file.split('.')[0].split('_')
        project = ids[0]
        dna_number = ids[2]
        panel_human = ids[5]
        panel_machine = ids[6]
        sample_id = '_'.join(ids[:7])
        print(project, dna_number, panel_human, panel_machine, sample_id)

        # get track
        track = sqvd.rest('track', data={'_id': "VIRTUAL_SOMATIC"})

        # get panel
        panel = sqvd.rest('panel', data={'panel_id': panel_machine})
        if not panel['data']:
            panel = sqvd.rest('panel', 'POST', {
                "panel_id": panel_machine,
                "panel_name": panel_human,
                "panel_description": panel_human,
                "group": "virtual",
                "reference_set_id": "grch37",
                "track_id": "VIRTUAL_SOMATIC"
            })

        # create the study
        obj = {
            'study_name': sample_id,
            'dataset_name': 'virtual',
            'sample_id': dna_number,
            'panel_id': panel_machine,
            'panel_version': 1,
            'workflow': track['data'][0]['name'],
            'subpanels': [],
            'group': 'virtual'
        }
        print(obj)
        try:
            study = sqvd.createStudy(obj)
            print('CREATED STUDY/SAMPLE:', study['_id'], study['sample_id'])
        except:
            studies = sqvd.rest('study', 'GET', {"study_name": sample_id})
            study = studies['data'][0]
        else:
            # upload the file
            uploaded = sqvd.upload([vcf_file], study['study_name'])
            print('UPLOADED', uploaded)

        # create virtual report
        print('Create virtual report if not exists')

        url = "http://"+os.getenv('SQVDAPIHOST')+'/graphql/'
        mutation = """mutation($autoreport: AutoReport!) {
            reportStudy(autoreport: $autoreport)
        }"""
        variables = {
            'autoreport': {
                'study_id': study['_id'],
                'process': 'QCI'
            }
        }

        headers = {'authorization': sqvd.session.headers['X-Auth-Token']}
        r = requests.post(url,
                          json={'query': mutation, 'variables': variables},
                          headers=headers)
        result = json.loads(r.text)
        if 'error' in result.keys():
            print('ERROR', result['error'])

        if 'data' in result.keys():
            print(r.status_code, result['data'])
        else:
            print("NO DATA")
        print("BYE")

