import os
import json
import boto3
import requests
from datetime import datetime

ssm = boto3.client("ssm")
sns = boto3.client("sns")

INSTANCE_ID = os.getenv("INSTANCE_ID")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")

# -----------------------------------------------------------------------------
# SSM Cleanup Commands
# -----------------------------------------------------------------------------

DOCKER_COMMANDS = [
    "docker system prune -af --volumes",
    "docker image prune -af",
    "docker container prune -f"
]

# -----------------------------------------------------------------------------
# Slack
# -----------------------------------------------------------------------------

def send_slack(message, success=True):

    color = "#36a64f" if success else "#ff0000"

    payload = {
        "attachments": [
            {
                "color": color,
                "title": "Docker Cleanup Report",
                "text": message
            }
        ]
    }

    requests.post(
        SLACK_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

# -----------------------------------------------------------------------------
# Teams
# -----------------------------------------------------------------------------

def send_teams(message, success=True):

    color = "00FF00" if success else "FF0000"

    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "Docker Cleanup",
        "themeColor": color,
        "title": "Docker Cleanup Report",
        "text": message
    }

    requests.post(
        TEAMS_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------

def lambda_handler(event, context):

    try:

        response = ssm.send_command(
            InstanceIds=[INSTANCE_ID],
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": DOCKER_COMMANDS
            }
        )

        command_id = response["Command"]["CommandId"]

        message = (
            f"Cleanup executed successfully\n"
            f"Command ID: {command_id}\n"
            f"Timestamp: {datetime.utcnow()}"
        )

        # SNS
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Docker Cleanup Success",
            Message=message
        )

        # Slack
        send_slack(message)

        # Teams
        send_teams(message)

        return {
            "statusCode": 200,
            "body": message
        }

    except Exception as e:

        error_message = f"Cleanup failed: {str(e)}"

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Docker Cleanup FAILED",
            Message=error_message
        )

        send_slack(error_message, success=False)

        send_teams(error_message, success=False)

        raise
