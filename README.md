# r7insight_lambdaCW
##### AWS Lambda function for sending AWS CloudWatch logs to Rapid 7 in near real-time for processing and analysing

###### Example use cases:
* Forwarding AWS VPC flow Logs
* Forwarding AWS Lambda function logs
* [Forwarding AWS CloudTrail logs](http://docs.aws.amazon.com/awscloudtrail/latest/userguide/send-cloudtrail-events-to-cloudwatch-logs.html)
* Forwarding any other AWS CloudWatch logs

## Obtain log token(s)
1. Log in to your Rapid 7 account
1. Add a new [token based log](https://insightops.help.rapid7.com/docs/token-tcp)

## Deploy the script on AWS Lambda
1. Create a new Lambda function using the "Author from scratch" option

1. Configure function:
   * Give your function a name
   * Set runtime to Python 3.9
   * Leave other options to default

1. Upload function code:
      * Create a .ZIP file, containing ```r7insight_lambdaCW.py``` and the folder ```certifi```
        * Make sure the files and ```certifi``` folder are in the **root** of the ZIP archive
        * Note if you download the .ZIP file directly from GitHub, the contents are inside a subfolder
      * Choose "Upload a .ZIP file" in "Code entry type" dropdown and upload the archive created in previous step

1. Lambda function handler
   * Change the "Handler" value to ```r7insight_lambdaCW.lambda_handler```

1. Set Environment Variables:
   * Token value should match UUID provided by Rapid7 UI or API
   * Region should be that of your Rapid7 account

   |         Key         |                                                   Value                                                   |
   | ------------------- | --------------------------------------------------------------------------------------------------------- |
   | region              | eu / us / etc                                                                                             |
   | token\*             | token uuid                                                                                                |
   | token_secret_name\* | the name of a [secrets manager](https://aws.amazon.com/secrets-manager/) secret containing the token uuid |

   \* Only one of the `token` or `token_secret_name` environment variables should be set. If you use `token_secret_name`, be sure to grant `secretsmanager:GetSecretValue` to the lambda function's execution role.

1. Optional configuration (adjust to your needs):
   * Increase memory
   * Increase timeout

1. Deploy the lambda function
   * At this point you can validate the configuration by sending a test event
   * Select "configure test event" and use "cloudwatch-logs" as the template
   * Send the test event and verify that its contents are forwarded to your log

## Configure CloudWatch Stream
1. Create a new stream:
   * Select CloudWatch log group
   * Navigate to "Subscription filters / Create Lambda subscription filter"

   ![Stream to Lambda](https://github.com/rapid7/r7insight_lambdaCW/blob/master/doc/stream_to_lambda.png?raw=true)

1. Choose destination Lambda function:
   * Select the AWS Lambda function deployed earlier from the dropdown menu
   * Optionally configure log formatting and filtering, if needed
     * [Please see AWS Documentation for more details](http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/FilterAndPatternSyntax.html)
     * If this is blank or incorrect, only raw data will be forwarded to Rapid7
     * Amazon provide preconfigured filter patterns for some log types

1. Review and start log stream
   * Review your configuration and click "Start streaming" at the bottom of the page

1. Watch your logs come in:
   * Navigate to your Rapid7 account and watch your CloudWatch logs appear
