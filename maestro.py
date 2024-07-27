#!/usr/bin/env python3

import boto3
import subprocess
import time
import os
import sys
from config import  TARGET_GROUP_ARN

def get_ips_from_target_group(target_group_arn, region):
    elbv2_client = boto3.client('elbv2', region_name=region)
    ec2_client = boto3.client('ec2', region_name=region)
    
    response = elbv2_client.describe_target_health(
        TargetGroupArn=target_group_arn
    )
    
    instance_ids = [target['Target']['Id'] for target in response['TargetHealthDescriptions'] if target['TargetHealth']['State'] == 'healthy']
    
    ips = []
    if instance_ids:
        instances = ec2_client.describe_instances(InstanceIds=instance_ids)
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                ips.append(instance['PrivateIpAddress'])
    
    return ips

def create_tmux_session(ips, session_name='aws_servers'):
    # Check if tmux session already exists
    result = subprocess.run(['tmux', 'has-session', '-t', session_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if result.returncode == 0:
        # If the session exists, attach to it
        subprocess.run(['tmux', 'attach-session', '-t', session_name])
        return
    
    # If the session does not exist, create a new one
    subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
    
    # Split windows and SSH into servers
    for idx, ip in enumerate(ips):
        if idx == 0:
            # First pane, send SSH command
            subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0', f'ssh -i /Users/fsaint/.ssh/seer_key.pem -o ProxyJump=bastion-host ubuntu@{ip} -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no', 'C-m'])
        else:
            # For subsequent panes
            subprocess.run(['tmux', 'split-window', '-t', session_name, '-h'])
            subprocess.run(['tmux', 'select-layout', '-t', session_name, 'tiled'])
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh -i /Users/fsaint/.ssh/seer_key.pem -o ProxyJump=bastion-host ubuntu@{ip} -o CheckHostIP=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no', 'C-m'])
        time.sleep(1)
    
    # Create the command input pane
    subprocess.run(['tmux', 'split-window', '-t', session_name, '-v'])
    subprocess.run(['tmux', 'select-layout', '-t', session_name, 'tiled'])
    
    # Return to the command input pane
    subprocess.run(['tmux', 'select-pane', '-t', session_name, str(len(ips))])
    
    # Attach to the session
    subprocess.run(['tmux', 'attach-session', '-t', session_name])

def main():
    target_group_arn = TARGET_GROUP_ARN
    region = 'us-east-1'
    
    # Get IP addresses from target group
    ips = get_ips_from_target_group(target_group_arn, region)
    
    if not ips:
        print("No healthy targets found in the target group.")
        return
    
    # Create tmux session and SSH into servers
    create_tmux_session(ips)

if __name__ == '__main__':
    # Ensure the script is running in the virtual environment
    if not os.getenv('VIRTUAL_ENV'):
        print("Please activate the virtual environment first!")
        sys.exit(1)

    main()
