#!/usr/bin/python

import boto3
import json
from json2html import *

# Create SES client
ses = boto3.client('ses')

# Read the json data file
file = open("data.json", "r")
jsondata = file.read()
#print(jsondata)

# Read html file which has json rendering
html_file = open("index.html", "r")
htmldata = html_file.read()
#print(htmldata)

# Update SES template
response = ses.update_template(
  Template = {
    'TemplateName' : 'AggConfigRuleTemplate1',
    'SubjectPart'  : 'Non-Compliance Config Rules Report for {{ AggregatorName }} Business Unit',
    'TextPart'     : 'Non Compliance Aggregator ',
    'HtmlPart'     : htmldata
  }
)
print("Updated the template ...")
print(response)

# Send email using a template
response = ses.send_templated_email(
    Source='indukuriv@gmail.com',
    Destination={
        'ToAddresses': [
            'indukuriv@gmail.com',
        ],
    },
    Template='AggConfigRuleTemplate1',
    TemplateData=jsondata
)
print("Sent email ...")
print(response)

