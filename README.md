# r7insight_lambdaCW
##### AWS Lambda function for sending AWS CloudWatch logs to Rapid 7 in near real-time for processing and analysing

###### Example use cases:
* Forwarding AWS VPC flow Logs
* Forwarding AWS Lambda function logs
* [Forwarding AWS CloudTrail logs](http://docs.aws.amazon.com/awscloudtrail/latest/userguide/send-cloudtrail-events-to-cloudwatch-logs.html)
* Forwarding any other AWS CloudWatch logs

## Obtain log token(s)
1. Log in to your Rapid 7 account
2. Add a new [token based log](https://insightops.help.rapid7.com/docs/token-tcp)

## Deploy the script on AWS Lambda
1. Create a new Lambda function

2. On the "Select Blueprint" screen, press "Skip"

3. Configure function:
   * Give your function a name
   * Set runtime to Python 3.6

4. Upload function code:
      * Create a .ZIP file, containing ```r7insight_lambdaCW.py``` and the folder ```certifi```
        * Make sure the files and ```certifi``` folder are in the **root** of the ZIP archive
      * Choose "Upload a .ZIP file" in "Code entry type" dropdown and upload the archive created in previous step

5. Lambda function handler and role
   * Change the "Handler" value to ```r7insight_lambdaCW.lambda_handler```
   * Create a new basic execution role (your IAM user must have sufficient permissions to create & assign new roles)

6. Set Environment Variables:
   * Token value should match UUID provided by Rapid 7 UI or API
   * Region should be that of your Rapid 7 account

   | Key       | Value      |
   |-----------|------------|
   | region    | eu / us    |
   | token     | token uuid |

7. Allocate resources:
   * Set memory to 128 MB (adjust to your needs)
   * Set timeout to ~2 minutes (adjust to your needs)

8. Enable function:
   * Click "Create function"

## Configure CloudWatch Stream
1. Create a new stream:
   * Select CloudWatch log group
   * Navigate to "Actions / Stream to AWS Lambda"

   ![Stream to Lambda](https://github.com/rapid7/r7insight_lambdaCW/blob/master/doc/step9.png?raw=true)

2. Choose destination Lambda function:
   * Select the AWS Lambda function deployed earlier from drop down menu
   * Click "Next" at the bottom of the page

   ![Select Function](https://github.com/rapid7/r7insight_lambdaCW/blob/master/doc/step10.png?raw=true)

3. Configure log format:
   * Choose the correct log format from drop down menu
   * Specify subscription filter pattern
     * [Please see AWS Documentation for more details](http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/FilterAndPatternSyntax.html)
     * If this is blank / incorrect, only raw data will be forwarded to Rapid 7
     * Amazon provide preconfigured filter patterns for some log types
   * Click "Next" at the bottom of the page

   ![Log Format](https://github.com/rapid7/r7insight_lambdaCW/blob/master/doc/step11.png?raw=true)

4. Review and start log stream
   * Review your configuration and click "Start Streaming" at the bottom of the page

   ![Start stream](https://github.com/rapid7/r7insight_lambdaCW/blob/master/doc/step6.png?raw=true)

5. Watch your logs come in:
   * Navigate to your Rapid 7 account and watch your CloudWatch logs appear
