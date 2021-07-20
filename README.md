# Cloud-Computing
Implement, test, evaluate, and demonstrate the cloud application(Flask app) using multiple services across Multi-cloud platform-using 
EC2, AWS Lambda, S3, Google cloud platform(GCP).

An application that supports determining the cost of estimating the value of Pi (π) accurate to a specifiable number of digits using a so-called Monte Carlo method.

URL of System: https://cloudcw-786543.ew.r.appspot.com/index.htm 

1) The system uses GAE, AWS Lambda and EC2
2) This system offers a front-end through which the user will provision and terminate resources and receive information output about the runs to estimate Pi's value.
3) This system uses the scalable service AWS Lambda and EC2 to run the main computation code that calculates the incircle values
4) This system has an initialisation page to chose the scalable service, number of resources to be warmed up or provisioned based on scalable service selection
5) This system captures user inputs s, q, d  to run the pi estimation code where runtime and each processed results of resource information is stored for the analysis
6) This system displays the estimation in a chart, a table showing the resource, incircle, shots and rate and a final estimate of pi and history page where all the present and past analysis is stored is only readable and not writable. was unable to append the results to s3 bucket as it was overwriting the entire content. 
7) This system provides the way to zero the analysis without creating or warming up the new resources
8) This system has a terminate function that terminates all the resources after use.

