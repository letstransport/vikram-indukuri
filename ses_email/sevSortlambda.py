import json
import re
import boto3
from botocore.exceptions import ClientError

RULE_NAME_REGEX = '-(.*?)-'
ses_client = boto3.client('ses', region_name="us-east-1")
config_client = boto3.client('config')

# Lambda handler function

def lambda_handler(event, context):
    # pylint: disable=unused-argument
    generate_reports()

def is_prod_environment():
    """Returns True if running in dev environment otherwise False"""
    return False
    # return 'HOME' in os.environ and os.environ.get('ENVIRONMENT') == 'PROD'

# This is the main function that retrieves the data and emails the reports

def swap(arr, index1, index2):
  temp = arr[index1]
  arr[index1] = arr[index2]
  arr[index2] = temp
  return arr

def generate_reports():
    with open('rule_info.json', 'r') as fp:
        ruleinfo_data = json.load(fp)

    aggregators = get_aggregator_data('BusinessUnit')
    print('Got list of BU aggregators')
    for aggregator in aggregators:
        agg_rules_obj = {}
        agg_rules_obj['BusinessUnit'] = get_aggregator_business_unit(aggregator)
        agg_rules_obj['AggregatorName'] = aggregator['AggregatorName']
        agg_rules_obj['AggregatorRules'] = []
        resources_by_rule_name = {}

        for rule in aggregator['AggregatorRules']:
            rule_name = rule['ConfigRuleName']
            account_id = rule['AccountId']
            aws_region = rule['AwsRegion']
            if re.findall(RULE_NAME_REGEX, rule_name) != []:
                base_rule_name = re.findall(RULE_NAME_REGEX, rule_name)[0]
            rule_resources = resources_by_rule_name.get(base_rule_name, [])
            paginator = config_client.get_paginator('get_aggregate_compliance_details_by_config_rule')

            for page in paginator.paginate(ConfigurationAggregatorName=aggregator['AggregatorName'],
                                           ConfigRuleName=rule_name,
                                           ComplianceType='NON_COMPLIANT',
                                           AccountId=account_id,
                                           AwsRegion=aws_region):

                for eval_result in page['AggregateEvaluationResults']:
                    result = eval_result['EvaluationResultIdentifier']['EvaluationResultQualifier']
                    result['AccountId'] = account_id
                    result['AwsRegion'] = aws_region
                    rule_resources.append(result)
            resources_by_rule_name[base_rule_name] = rule_resources

        for rule in resources_by_rule_name:
            rule_data = {'rule': rule, 'resources': resources_by_rule_name[rule]}
            if rule in ruleinfo_data:
                rule_info = ruleinfo_data[rule]
                rule_data["name"] = rule_info['name']
                rule_data["description"] = rule_info['description']
                rule_data["severity"] = rule_info["severity"]
            agg_rules_obj['AggregatorRules'].append(rule_data)

        print("line 73")
        AggregatorRulesArr = agg_rules_obj.get('AggregatorRules')
        AggregatorRulesArrLength = len(AggregatorRulesArr)
        l = 0
        h = AggregatorRulesArrLength - 1
        m = 0
        print("line 79")
        while (m <= h):
            severity = AggregatorRulesArr[m].get('severity')
            if severity == 'Medium':
                m += 1
            elif severity == 'High':
                AggregatorRulesArr = swap(AggregatorRulesArr, l, m)
                l = l + 1
                m = m + 1
            elif severity == 'Low':
                AggregatorRulesArr = swap(AggregatorRulesArr, m, h)
                h = h - 1
        print("line 91")        
        agg_rules_obj['AggregatorRules'] = AggregatorRulesArr
        print("line 93")
        print(json.dumps(agg_rules_obj))
#        updated_agg_rules_obj = appending_rule_data(agg_rules_obj)
#        print("Appended output :" + updated_agg_rules_obj)
#        print("Appended output :" + json.dumps(agg_rules_obj,indent=4))
        print(f"Sending report for {get_aggregator_business_unit(aggregator)}")
#        send_email(aggregator, json.dumps(agg_rules_obj))
        print(f"Sent report for {get_aggregator_business_unit(aggregator)}")
#        json.dump(updated_agg_rules_obj, outfile, indent=4)

#        break
"""
def appending_rule_data(agg_rules_obj):
    with open('rule_info.json', 'r') as fp:
        ruleinfo_data = json.load(fp)

    for agg_rule in agg_rules_obj['AggregatorRules']:
        for rule_name, value_data in ruleinfo_data.items():
#            print(value_data)
            if agg_rule['rule'] == rule_name:
                for key, value in value_data.items():
                    print(value)
                    agg_rule[key] = value
    return json.dumps(agg_rules_obj)
"""
def get_aggregator_data(aggregator_level):
    """
    Parameters:
    aggregatorLevel (string): filter by either Pillar or BusinessUnit.

    Returns a list of aggregators and their rules that were evaluated as non compliant
    """
    aggregator_rule_list = []
    aggregators = get_aggregators()

    for aggregator in aggregators:
        config_rules = []
        aggregator_name = aggregator['AggregatorName']
        tags = aggregator['Tags']

        if tags['AggregateLevel'] != aggregator_level:
            continue

        aggregator_info = {}
        aggregator_info['AggregatorName'] = aggregator_name
        aggregator_info['Tags'] = tags

        paginator = config_client.get_paginator('describe_aggregate_compliance_by_config_rules')
        for page in paginator.paginate(ConfigurationAggregatorName=aggregator_name, Filters={'ComplianceType': 'NON_COMPLIANT'}):
            config_rules.extend(page['AggregateComplianceByConfigRules'])

        aggregator_info['AggregatorRules'] = config_rules
        aggregator_rule_list.append(aggregator_info)
    return aggregator_rule_list

# This function returns a list of aggregators and their tags.
def get_aggregators():
    """Returns a list of AWS Config rule aggregators"""
    aggregators = []
    for page in config_client.get_paginator('describe_configuration_aggregators').paginate():
        for aggregator in page['ConfigurationAggregators']:
            name = aggregator['ConfigurationAggregatorName']
            aggregator_arn = aggregator['ConfigurationAggregatorArn']
            tags = get_tags_for_resource(aggregator_arn)
            aggregators.append({'AggregatorName': name, 'Tags': tags})
    return aggregators

# Returns the tags for a resource
def get_tags_for_resource(arn):
    """Parameters:
    arn (string): The arn of the resource
    """
    resp = config_client.list_tags_for_resource(ResourceArn=arn)
    tags = {tags['Key']: tags['Value'] for tags in resp['Tags']}
    return tags

# Gets the contact address associated with an aggregator
def get_aggregator_email_contact(aggregator):
    if is_prod_environment():
        return aggregator['Tags']['DevOpsContact']
    return DEBUG_EMAIL_DESTINATION

# Gets aggregator BU
def get_aggregator_business_unit(aggregator):
    return aggregator['Tags']['BusinessUnit']
