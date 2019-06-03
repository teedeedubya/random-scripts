#!/usr/bin/env python3                                                                                                                                                                                                                        
#  -*- coding: utf-8 -*-                                                                                                                                                                                                                      

import argparse, sys, boto3, pprint
import logging
from atlassian import Confluence

def count(my_list, my_key):
    if my_key not in my_list:
        return '0'
    else:
        return str(len(my_list[my_key]))

parser = argparse.ArgumentParser(description='Show all EC2 and RDS instances in your AWS account, grouped by VPC.')
parser.add_argument('--region', dest='region', help='Limit to a single region')
args = parser.parse_args()

logging.basicConfig()
logger = logging.getLogger('logger')


session = boto3.Session(profile_name='REPLACE WITH AWS KEY ALIAS', region_name='us-east-1')

regions = session.get_available_regions('ec2')


confluence = Confluence(
            url='https://confluence.example.com',
            username='twelder',
            password='*******************')

#confluenceHTML='<div class="table-wrap"><table class="confluenceTable" resolved=""><colgroup><col><col><col><col></colgroup><tbody>'
confluenceHTML='<div class="table-wrap"><table class="confluenceTable" resolved=""><tbody>'


for region in regions:
#    print("Region: " + region)
    if (not args.region) or (args.region == region):
        ec2client = session.client('ec2', region)
        rdsclient = session.client('rds', region)

        instances = {}
        dbs = {}

        ec2_instances = ec2client.describe_instances(Filters=[ { 'Name': 'instance-state-name', 'Values': [ 'running' ] } ])
        for reservation in ec2_instances['Reservations']:
            for instance in reservation['Instances']:
		instance_name =	instance['InstanceId']
		instance_type =	instance['InstanceType']
                instance_private_ip = instance['PrivateIpAddress']
 
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
			instance_name =	instance['InstanceId'] + ' (' +	tag['Value'] + ')'
                if instance['VpcId'] in instances:
                    instances[instance['VpcId']].append('<tr><td class="confluenceTd">' + instance_name + '</td>')
                    instances[instance['VpcId']].append('<td class="confluenceTd">' + instance_type + '</td>')
                    instances[instance['VpcId']].append('<td class="confluenceTd">' + instance_private_ip + '</td></tr>')
                else:
                    instances[instance['VpcId']] = ['<tr><td class="confluenceTd">' + instance_name + '</td>' ]
                    instances[instance['VpcId']].append('<td class="confluenceTd">' + instance_type + '</td>')
                    instances[instance['VpcId']].append('<td class="confluenceTd">' + instance_private_ip + '</td></tr>')

        db_instances = rdsclient.describe_db_instances()
        for db_instance in db_instances['DBInstances']:
            if 'DBSubnetGroup' in db_instance:
                db_vpc = db_instance['DBSubnetGroup']['VpcId']
                if db_vpc in dbs:
                    dbs[db_vpc].append('<tr><td class="confluenceTd">' + db_instance['DBInstanceIdentifier'] + '</td>' )
                    endpoint = db_instance['Endpoint']['Address'] + ':' + str(db_instance['Endpoint']['Port'])
                    dbs[db_vpc].append('<td class="confluenceTd">' + endpoint + '</td>')
                    dbs[db_vpc].append('<td class="confluenceTd">' + db_instance['DBName'] + '</td></tr>')
                else:
                    dbs[db_vpc] = [ '<tr><td class="confluenceTd">' + db_instance['DBInstanceIdentifier'] + '</td>' ]
                    endpoint = db_instance['Endpoint']['Address'] +':'+ str(db_instance['Endpoint']['Port'])
                    dbs[db_vpc].append('<td class="confluenceTd">' + endpoint + '</td>')
                    dbs[db_vpc].append('<td class="confluenceTd">' + db_instance['DBName'] + '</td></tr>')

        vpcs = ec2client.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            if vpc['IsDefault'] == False:
                vpc_id = vpc['VpcId']
                for tag in vpc['Tags']:
                    if tag['Key'] == "Name":
                        vpc_name = tag['Value']
                confluenceHTML += '<tr><th colspan="4" class="confluenceTh">'
                confluenceHTML += vpc_name + ' | ' + vpc['CidrBlock'] + ' (' + str(int(count(instances, vpc_id)) / 3)  + \
                        ' ec2 instances, ' + str(int(count(dbs, vpc_id)) / 2) + ' rds instances)'
                confluenceHTML += "</th></tr>"
                if vpc_id in instances:
                  confluenceHTML += ''.join(instances[vpc_id])
                if vpc_id in dbs:
                    confluenceHTML += ''.join(dbs[vpc_id])

confluenceHTML += "</tbody></table></div>"
print(confluenceHTML)
status = confluence.update_or_create(
    parent_id='REPLACE WITH PARENT PAGE ID',
    title='AWS Asset Inventory / Server List',
    body=confluenceHTML)
print(status)
