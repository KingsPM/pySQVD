#!/usr/bin/env python
from __future__ import print_function
from six import string_types
from six.moves.urllib.parse import urlencode
import requests
import hashlib
import json
from datetime import datetime, timedelta
import os
import time
import re

__author__ = "David Brawand"
__credits__ = ['David Brawand']
__license__ = "MIT"
__maintainer__ = "David Brawand"
__email__ = "dbrawand@nhs.net"


class ApiError(Exception):
    """Exception raised for errors in or while using the SQVD API"""

    def __init__(self, message):
        super(ApiError, self).__init__(message)


def safeKeys(iterable):
    """recursively substitutes $./ characters from json keys for MongoDB

    :param iterable: obj or collection
    :type iterable: object/array.
    :returns: like input.
    """
    if type(iterable) is dict:
        for key in iterable.keys():
            newKey = key.replace('.', '-').replace('$', '£')
            iterable[newKey] = iterable.pop(key)
            if type(iterable[newKey]) is dict or type(iterable[newKey]) is list:
                iterable[newKey] = safeKeys(iterable[newKey])
    elif type(iterable) is list:
        for item in iterable:
            item = safeKeys(item)
    return iterable


def weekdaysFromNow(days):
    """Returns a datetime object with the number of weekdays added.

    :param days: Weekdays to add.
    :type days: int.
    :returns:  datetime.
    """
    startdate = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while days > 0:
        startdate += timedelta(days=1)
        if startdate.weekday() >= 5:  # next if weekend
            continue
        days -= 1
    return startdate


class SQVD(object):

    def __init__(self, username, password, host, version='v1'):
        """creates pySQVD class

        :param username: SQVD username.
        :type username: str.
        :param password: Plain text password
        :type password: str.
        :param host: SQVD hostname
        :type host: str.
        :param version: API version
        :type version: str.
        """
        self.host = host
        self.url = 'http://'+"/".join([host, 'api', version])
        self.session = None
        self.userid = None
        self.username = username
        self.password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def __enter__(self):
        assert self.login()
        return self

    def __exit__(self, *args):
        self.logout()

    def __str__(self):
        return '<SQVD  '+self.username+'@'+self.url+(' authenticated >' if self.session else ' >')

    def login(self, username=None, password=None):
        """Creates session with authentication headers and sets username and userid

        :param username: SQVD username.
        :type username: str.
        :param password: Plain text password
        :type password: str.
        :returns:  bool -- true if sucessful
        """
        if username:
            self.username = username
        if password:
            self.password = hashlib.sha256(
                password.encode('utf-8')).hexdigest()

        try:
            r = requests.post(self.url+'/login', data={
                'username': self.username,
                'password': self.password,
                'hashed': True
            })
        except Exception as e:
            print >> sys.stderr, 'EXCEPTION', e
            raise

        try:
            self._checkResponse(r)
            auth = r.json()['data']
        except:
            return
        self.userid = auth['userId']
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Auth-Token": auth['authToken'], "X-User-Id": auth['userId']})
        return True

    def logout(self):
        """Closes the session, logs out and unsets userid

        :returns:  bool -- true if sucessful
        """
        if self.session and self.username:
            self.session.close()
            if self.session.post(self.url+'/logout').status_code == 200:
                self.userid = None
                return True

    def _checkResponse(self, response):
        """checks if 200 and API returns success, else prints error message

        :param response: the API response object
        :type response: Response object.
        :returns:  bool -- true if sucessful
        :raises: ApiError with reason
        """
        if response.status_code in [200]:
            return True
        raise ApiError(response.reason)

    def rest(self, collection, op='GET', data=None, json=None):
        """This function does something.

        :param collection: collection/resource name.
        :type collection: string
        :param op: HTTP method
        :type op: STRING.
        :param data: Form Data
        :type data: dict/string.
        :param json: JSON Data, keys are sanitized for mongoDB
        :type json: dict/json.
        :returns: response object.
        """
        baseUrl = [self.url, collection]
        if op == 'GET':
            if isinstance(data, string_types):
                baseUrl.append(data)
            elif isinstance(data, dict):
                baseUrl[-1] += '?' + \
                    '&'.join(map(lambda k: str(k)+'=' +
                                 str(data[k]), data.keys()))
            r = self.session.request(op, '/'.join(baseUrl))
        elif op == 'DELETE':
            baseUrl.append(data)
            r = self.session.request(op, '/'.join(baseUrl))
        elif op == 'POST':
            r = self.session.request(
                op, '/'.join(baseUrl), data=data, json=safeKeys(json))
        # check if successful
        if self._checkResponse(r):
            return r.json()

    def createStudy(self, x, find=False):
        """Creates a new study and sample if doesnt exist, validates track and panel

        :param x: Dictionary with study/sample information.
        :type x: dict -- [study_name, sample_id, panel_id, panel_version, workflow, subpanels, group]
        :param find: If study cannot be created find and return
        :type find: bool -- default False
        :returns:  dict -- the study document.
        :raises: AssertionError on conflicts
        """
        now = datetime.now().replace(microsecond=0)

        newstudy = {
            'study_name': x['study_name'],
            "subpanels": x['subpanels'],
            "group": x["group"],
            "createdBy": self.userid,
            'requested': now.isoformat()
        }
        newsample = None

        # check panel and subpanels
        try:
            panel = self.rest(
                'panel', data={k: x[k] for k in ('panel_id', 'panel_version')})
            assert len(panel['data']) == 1
            assert set(x['subpanels']) <= set(
                map(lambda x: x['subpanel_id'], panel['data'][0]['subpanels']))
            duedate = weekdaysFromNow(int(panel['data'][0]['tat']))
        except AssertionError:
            raise ApiError('panel or subpanels not found')
        except:
            raise
        else:
            newstudy['panel_id'] = panel['data'][0]['_id']
            newstudy['subpanels'] = x['subpanels']
            newstudy['reportdue'] = duedate.isoformat()
        # check if track exists
        try:
            track = self.rest('track', data={'name': x['workflow']})
            assert len(track['data']) == 1
        except AssertionError:
            raise ApiError('Workflow not found')
        except:
            raise
        else:
            newstudy['track_id'] = track['data'][0]['_id']

        # check if study already exists (returns if find enabled)
        try:
            study = self.rest(
                'study', data={k: x[k] for k in ('study_name', 'group')})['data']
            assert len(study) == 0
        except AssertionError:
            if find and len(study) == 1:
                return study[0]
            else:
                raise ApiError('study exists')
        except:
            raise

        # check sample
        try:
            sample = self.rest(
                'sample', data={k: x[k] for k in ('sample_id', 'group')})
            assert len(sample['data']) <= 1
        except AssertionError:
            raise ApiError('ambiguous sample name')
        except:
            raise

        # create sample or get _id
        try:
            _id = self.rest('sample', 'POST', data={
                "group": x['group'],
                "sample_id": x['sample_id'],
                "received": now.isoformat(),
                "bookedBy": self.userid
            })['data']['_id'] if not sample['data'] else sample['data'][0]['_id']
        except:
            raise
        else:
            newstudy["sample_id"] = _id

        return self.rest('study', 'POST', newstudy)['data']

    def upload(self, files, study_name, parse=True):
        """Adds a file to a study (imports VCFs, uploads BEDs)

        :param files: file paths
        :type files: [str]
        :param study_name: The study name
        :type study_name: str
        :param parse: parse/import the added file
        :type parse: bool

        :returns: list of tuples (file, json response)
        :raises: AttributeError, AssertionError, KeyError
        """
        # get study
        study = self.rest('study', data={'study_name': study_name})
        try:
            assert len(study['data']) == 1
        except AssertionError:
            print('ERROR: found multiple studies named {}'.format(study_name))
            return
        except:
            raise
        else:
            results = []
            for fi in files:
                # get filename
                m = re.search(r'\.(.[^\.]+)(\.gz)?$', fi)
                if m:
                    filetype = m.group(1)
                    if os.path.isfile(fi) and m and filetype in ['vcf', 'bed', 'bedgraph', 'bam', 'pdf']:
                        url = '/'.join([self.url, 'study',
                                        study['data'][0]['_id'], filetype])
                        # set query parameters
                        # add filename
                        url += '?%s' % (
                            urlencode({'filename': fi.split('/')[-1]}))
                        url += '&import=true' if parse else ''  # import all recognised files
                        # read file
                        with open(fi, 'rb') as fh:
                            data = fh.read()
                        # post request
                        r = self.session.request('POST',
                                                 url,
                                                 headers={
                                                     'Content-Type': 'application/octet-stream'},
                                                 data=data)
                        if self._checkResponse(r):
                            results.append((fi, r.json()))
                    else:
                        print('ERROR: {} is not valid file'.format(
                            os.path.basename(fi)))
                else:
                    print('ERROR: {} is an unsupported format'.format(
                        os.path.basename(fi)))
            return results


if __name__ == "__main__":
    import sys
    if (len(sys.argv) < 4):
        print('test with USERNAME PASSWORD VCF as arguments')
        sys.exit(1)

    sqvd = SQVD(username=sys.argv[1],
                password=sys.argv[2], host='127.0.0.1:3000')
    with sqvd:
        # get all studies
        studies = sqvd.rest('study')
        print('studies', studies)
        print('STUDIES:', len(studies['data']), studies['userid'],
              studies['requested'], str(studies['querytime'])+'ms')

        # post study
        data = {
            "study_name": "XXXXXX",
            "sample_id": "XXXXXX",
            "panel_id": "XXXXXX",
            "subpanels": [],
            "group": "molpath",
            "requested": "2018-03-26T08:11:49Z",
            "reportdue": "2018-03-28T23:00:00Z",
            "track_id": "SOMATIC",
            "dataset_id": "XXXXXX"
        }
        study = sqvd.rest('study', 'POST', data)
        print('CREATED STUDY:', study['data']['_id'])

        # show sample count
        print("STUDYCOUNT:", len(sqvd.rest('study')['data']))

        # get document
        print('GET BY ID:', len(
            sqvd.rest('study', 'GET', study['data']['_id'])['data']))

        # with query parameters
        study = sqvd.rest(
            'study', data={'study_name': study['data']['study_name']})
        print('GET BY NAME:', len(study['data']))

        # delete this study
        print('DELETE:', len(
            sqvd.rest('study', 'DELETE', study['data'][0]['_id'])['data']))

        # create study
        obj = {
            'study_name': 'apitest',
            'sample_id': 'apitest',
            'panel_id': 'TEST',
            'panel_version': 1,
            'workflow': 'somatic',
            'subpanels': ['FULL'],
            'group': 'precmed'
        }
        study = sqvd.createStudy(obj)
        print('CREATED STUDY/SAMPLE:', study['_id'], study['sample_id'])

        # test upload
        uploaded = sqvd.upload(sys.argv[3:], 'apitest')
        print('UPLOADED:', len(uploaded))

        # remove study and sample
        sqvd.rest('study', 'DELETE', study['_id'])
        sqvd.rest('sample', 'DELETE', study['sample_id'])
