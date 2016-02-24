## Camunda Cockpit Commandline Client

The cockit client allows bulk operations on process instances using the [REST
API provided by the process engine][1]. Possible operations are

 - Listing process instances (`--list` / `-l`)
 - Increasing job retries (`--retry` / `-r`)
 - Canceling process instances (`--cancel` / `-c`)

The process instances to operate on can be selected by

 - Process instance id (`--process-instance-id` / `-i`)
 - Part of an error message from a failed job (`--message` / `-m`)
 - Time range (`--from-timestamp` and `--to-timestamp`, both in ISO-8601 format)

For login currently only the cookie based authorization of the camunda cockpit is
supported.

The base url and process engine name have to be configured in a configuration
file. The script tries to read the configuration from the following two places:

 - the user's home directory as `~/.cockpit-client.yaml`
 - relative to this python script as `cockit-client.yaml`

Example configuration file:

    live:
        url: 'https://live.example.com/camunda'
        engines: [engine1, engine2, engine3, engine4]
    staging:
        url: 'https://staging.example.com/camunda'
        engines: [engine1, engine2]
        verify: '/path/to/certificate.pem'

Here there are four process engines running for the live instance. The
process engine used can be specified using the `--shard` flag on the command
line, or the operation can be executed on all process engines of an
environment using the `--all` flag.

If the url is using https without a certificate known to the [python requests
library][2] a path to a certificate can also be specified in this configuration
file.

 [1]: https://docs.camunda.org/manual/7.4/reference/rest/
 [2]: http://docs.python-requests.org/en/master/user/advanced/#ca-certificates
