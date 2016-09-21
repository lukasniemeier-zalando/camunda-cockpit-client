#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import getpass
import argparse
import json
import yaml
import os

class BasicAuth:

    def create(args):
        username = args.username
        if username is None:
            username = input('User Name: ')

        password = args.password
        if password is None:
            password = getpass.getpass('Password: ')

        return BasicAuth(username, password)

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def login(self, session):
        session.admin_post('/login/cockpit', username=self.username, password=self.password)

    def logout(self, session):
        session.admin_post('/logout')

class OAuth:

    def create(args):
        token = args.token
        if token is None:
            token = input('Token: ')

        return OAuth(token)

    def __init__(self, token):
        self.token = token

    def login(self, session):
        session.headers.update({'Authorization': 'Bearer {}'.format(self.token)})

    def logout(self, session):
        pass


class Client:

    def __init__(self, session, base, engine, auth, verify = True):
        self.base = base
        self.engine = engine
        self.auth = auth
        self.session = session
        self.verify = verify
        self.content_json_headers = {'Content-Type': 'application/json'}
        self.session.headers.update({'Accept': 'application/json, */*;q=0.9'})

    def _merge_dict(self, dict1, dict2):
        result = {}
        result.update(dict1)
        result.update(dict2)
        return result

    def login(self):
        self.auth.login(self.session)

    def logout(self):
        self.auth.logout(self.session)

    def api_get(self, api, **params):
        req = self.session.get('%s/engine/%s%s' % (self.base, self.engine, api), params=params, verify=self.verify)
        req.raise_for_status()
        return req

    def api_put_json(self, api, json_data):
        req = self.session.put('%s/engine/%s%s' % (self.base, self.engine, api),
                               headers=self.content_json_headers, data=json.dumps(json_data), verify=self.verify)
        req.raise_for_status()
        return req

    def api_delete(self, api):
        req = self.session.delete('%s/engine/%s%s' % (self.base, self.engine, api), verify=self.verify)
        req.raise_for_status()
        return req

    def admin_post(self, api, **data):
        req = self.session.post('%s/api/admin/auth/user/%s%s' % (self.base, self.engine, api), 
                                data=data, verify=self.verify)
        return req

    def get_statistics(self):
        statistics = self.api_get(self.base, self.engine, '/process-definition/statistics', incidents=True)
        return statistics.json()

    def _join_incidents_with_jobs(self, incidents, jobs):
        job_by_execution = dict((job['executionId'], job) for job in jobs)
        return [self._merge_dict(incident, job_by_execution[incident['executionId']]) for incident in incidents if incident['executionId'] in job_by_execution]

    def _filter_by_timestamp(self, failed_jobs, from_timestamp, to_timestamp):
        return [failed_job for failed_job in failed_jobs if (from_timestamp is None or from_timestamp
                < failed_job['incidentTimestamp']) and (to_timestamp is None or to_timestamp
                > failed_job['incidentTimestamp'])]

    def _filter_by_message(self, failed_jobs, message_pattern):
        return [failed_job for failed_job in failed_jobs if message_pattern is None or re.search(message_pattern, failed_job['exceptionMessage'] or '') or re.search(message_pattern, failed_job['incidentMessage'] or '')]


    def get_incidents(self, process_instance_id=None, activity_id=None):
        incidents = self.api_get('/incident', incidentType='failedJob', processInstanceId=process_instance_id,
                                 activityId=activity_id)
        return incidents.json()

    def get_jobs(self, process_instance_id=None):
        jobs = self.api_get('/job', withException='true', processInstanceId=process_instance_id)
        return jobs.json()

    def get_failed_jobs(self, message_filter=None, from_timestamp=None, to_timestamp=None, process_instance_id=None):
        incidents = self.get_incidents(process_instance_id)
        jobs = self.get_jobs(process_instance_id)
        failed_jobs = self._join_incidents_with_jobs(incidents, jobs)
        return self._filter_by_message(self._filter_by_timestamp(failed_jobs, from_timestamp, to_timestamp), message_filter)

    def show_failed_jobs(self, message_filter=None, from_timestamp=None, to_timestamp=None, process_instance_id=None):
        row_format = \
                '{processEngine:8}{incidentTimestamp:24}{processDefinitionKey!s:24}{activityId:40}{processInstanceId:64}{exceptionMessage}'

        failed_jobs = self.get_failed_jobs(message_filter, from_timestamp, to_timestamp, process_instance_id)

        if len(failed_jobs) > 0:
            print(row_format.format(processEngine='Engine', incidentTimestamp='Timestamp', activityId='Activity',
                                    processDefinitionKey='Process', processInstanceId='Process Instance Id',
                                    executionId='Execution Id', exceptionMessage='Exception Message'))

            for job in failed_jobs:
                job.update({'processEngine': self.engine})
                print(row_format.format(**job))

    def retry_jobs(self, message_filter=None, from_timestamp=None, to_timestamp=None, process_instance_id=None):
        jobs = self.get_failed_jobs(message_filter, from_timestamp, to_timestamp, process_instance_id)
        for job in jobs:
            self.api_put_json('/job/%s/retries' % (job['id'], ), json_data={'retries': 1})
            print('resolved incident for process instance %s execution %s and job %s' % (job['processInstanceId'],
                    job['executionId'], job['id']))

    def cancel_process_instance(self, process_instance_id):
        parent_instances = self.api_get('/process-instance/', subProcessInstance=process_instance_id)
        try:
            self.api_delete('/process-instance/%s' % (process_instance_id, ))
            print('canceled process instance id %s' % (process_instance_id, ))
        except requests.exceptions.HTTPError as e:
            print("could not cancel process instance %s - %s" % (process_instance_id, e))


        for parent in parent_instances.json():
            self.cancel_process_instance(parent['id'])

    def cancel_process_instances(self, message_filter=None, from_timestamp=None, to_timestamp=None,
                                 process_instance_id=None):
        jobs = self.get_failed_jobs(message_filter, from_timestamp, to_timestamp, process_instance_id)
        for job in jobs:
            self.cancel_process_instance(job['processInstanceId'])

CONFIG_PATH = os.path.expanduser('~/.cockpit-client.yaml')
CONFIG_PATH_FALLBACK = os.path.join(os.path.dirname(__file__), 'cockpit-client.yaml')

def load_config():
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as configfile:
            return yaml.load(configfile)
    else:
        with open(CONFIG_PATH_FALLBACK, 'r') as configfile:
            return yaml.load(configfile)

def main():

    environments = load_config()

    parser = argparse.ArgumentParser(description='cockpit client')

    names = parser.add_mutually_exclusive_group(required=True)
    names.add_argument('-n', '--name', '-s', '--shard', help='which process engine to execute on')
    names.add_argument('-a', '--all', action='store_true', help='execute on all process engines')

    parser.add_argument('-e', '--environment', choices=environments.keys())
    parser.add_argument('-u', '--username', nargs='?')
    parser.add_argument('-p', '--password', nargs='?')
    parser.add_argument('-t', '--token', nargs='?')

    filters = parser.add_argument_group()
    filters.add_argument('-i', '--process-instance-id')
    filters.add_argument('-m', '--message', help='error message pattern')
    filters.add_argument('--from-timestamp', '--from', help='from timestamp in iso format (2016-02-23T09:00:00)')
    filters.add_argument('--to-timestamp', '--to', help='to timestamp in iso format (2016-02-23T12:30:00)')

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('-c', '--cancel', action='store_true', help='cancel process instances')
    action.add_argument('-C', '--cancel-process-instance', action='store_true',
                        help='cancel a single process instance regardless of incidents')
    action.add_argument('-r', '--resolve', '--retry', action='store_true', help='resolve incidents and retry jobs')
    action.add_argument('-l', '--list', action='store_true', help='view list of failed jobs')

    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    has_message_or_time = args.message is not None or args.from_timestamp is not None or args.to_timestamp is not None

    if args.process_instance_id:
        if has_message_or_time:
            parser.error('--process-instance-id does not support additional filters')

    if args.resolve or args.cancel:
        if args.process_instance_id is None and not has_message_or_time:
            parser.error('--resolve or --cancel require a filter')

    if args.cancel_process_instance and args.process_instance_id is None:
        parser.error('--cancel-process-instance requires a process instance id')

    environment = environments[args.environment]

    if args.all:
        engines = environment['engines']
    elif not args.name in environment['engines']:
        parser.error('please specify a valid process engine name using --name or use --all to run on all process engines')
    else:
        engines = [args.name]

    auth = OAuth.create(args) if environment['auth'] == 'oauth' else BasicAuth.create(args)

    base_url = environments[args.environment]['url']
    verify = environments[args.environment].get('verify', True)

    process_instance_id = None
    if args.process_instance_id:
        process_instance_id = args.process_instance_id

    message_pattern = None
    if args.message:
        message_pattern = re.compile(args.message)

    from_timestamp = None
    if args.from_timestamp:
        from_timestamp = args.from_timestamp
        if args.verbose:
            print('Filtering from timestamp %s' % (from_timestamp, ))

    to_timestamp = None
    if args.to_timestamp:
        to_timestamp = args.to_timestamp
        if args.verbose:
            print('Filtering to timestamp %s' % (to_timestamp, ))

    session = requests.Session()

    for engine in engines:

        if args.verbose:
            print('Running on process engine %s' % (engine, ))

        client = Client(session, base_url, engine, auth, verify)
        client.login()

        try:
            if args.list:
                client.show_failed_jobs(message_pattern, from_timestamp, to_timestamp, process_instance_id)
            elif args.resolve:
                client.retry_jobs(message_pattern, from_timestamp, to_timestamp, process_instance_id)
            elif args.cancel:
                client.cancel_process_instances(message_pattern, from_timestamp, to_timestamp, process_instance_id)
            elif args.cancel_process_instance:
                client.cancel_process_instance(process_instance_id)
        finally:

            client.logout()


main()
