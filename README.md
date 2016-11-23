## Camunda Cockpit Command-Line Client

The [Camunda Cockpit web application][2] enables easy resolution of isolated incidents. However, it's much more common to have many incidents arise simultaneously, along with similar exceptions messages — for example, "Read timed out." Retrying multiple incidents using the Cockpit web app is very cumbersome. That's why we've created this command line client, which simplifies bulk-handling of incidents using Camunda Process Engine's [REST API][1].

 **Featured operations**. This tool supports the following:

 - Listing process instances (`--list` / `-l`)
 - Increasing job retries (`--retry` / `-r`)
 - Canceling process instances (`--cancel` / `-c`)

Select **process instances** to operate on with these:

 - Process instance id (`--process-instance-id` / `-i`)
 - Part of an error message from a failed job (`--message` / `-m`)
 - Time range (`--from-timestamp` and `--to-timestamp`, both in ISO-8601 format)

###Development Status
####Login/Configuration

This tool supports cookie-based authorization of the Camunda Cockpit and [OAuth](https://oauth.net/). Configure the base url and process engine name in a configuration file. The script tries to read the configuration from the following two places:

 - the user's home directory, as `~/.cockpit-client.yaml`
 - relative to this Python script, as `cockit-client.yaml`

The authors have tested and used the following script/configuration file in production with version 7.1 and 7.4 of the Camunda engine. In this example, four process engines run for the live instance:

    live:
        url: 'https://live.example.com/engine-rest'
        engines: [engine1, engine2, engine3, engine4]
        auth: 'oauth'
    staging:
        url: 'https://staging.example.com/camunda'
        api-path: 'api/engine'
        engines: [engine1, engine2]
        verify: '/path/to/certificate.pem'

Here, you could either specify the process engine using the `--shard` flag on the command line, or use the `--all` flag to execute the operation on all process engines of an environment.

If the url uses HTTPS without a certificate known to the [Python request library][3], you can specify a path to a certificate in this configuration file.

###Contributing to Camunda Cockpit Command-Line Client
This project welcomes feedback and contributions. Feel free to claim something from our ["Help Wanted"](https://github.com/zalando/SwiftMonkey) items, or pitch an idea of your own. And take a look at our [Contributor guidelines](https://github.com/zalando/camunda-cockpit-client/blob/master/CONTRIBUTING.md) for info and updates about our process.

###License
This project uses the [Apache license, version 2](https://github.com/zalando/camunda-cockpit-client/blob/master/LICENSE).

 [1]: https://docs.camunda.org/manual/7.4/reference/rest/
 [2]: https://camunda.org/features/cockpit/
 [3]: http://docs.python-requests.org/en/master/user/advanced/#ca-certificates
