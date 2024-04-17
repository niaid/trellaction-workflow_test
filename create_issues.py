import os
import requests
import json
from github import Github

token = os.getenv("REPO_TOKEN")
g = Github(token)
headers = {"Authorization": f"Bearer {token}"}

owner, repo_name = os.getenv("GITHUB_REPOSITORY").split("/")
repo = g.get_repo(f"{owner}/{repo_name}")

# Get Dependabot alerts

query = f"""
{{
  repository(owner:"{owner}", name:"{repo_name}") {{
    vulnerabilityAlerts(first: 100) {{
      nodes {{
        number
        state
        createdAt
        dismissedAt
        securityVulnerability {{
          package {{
            name
          }}
          advisory {{
            description
          }}
          severity
        }}
      }}
    }}
  }}
}}
"""

response = requests.post('https://api.github.com/graphql', headers=headers, json={'query': query})
data = response.json()

alerts = data["data"]["repository"]["vulnerabilityAlerts"]["nodes"]

custom_labels_env = os.getenv("CUSTOM_LABELS", "")
custom_labels = [label.strip() for label in os.getenv("CUSTOM_LABELS", "").split(",")] + ["Trellaction"]
print(custom_labels_env)
print(custom_labels)
severity_prefix = os.getenv("PRIORITY_PREFIX", "").strip()

dep_created_issues = []
dep_skipped_issues = []

# Define the mapping dictionary
severity_mapping = {
    "moderate": "medium",
    "critical": "high"
}

# Define the function to convert severity
def convert_severity(severity):
    return severity_mapping.get(severity.lower(), severity)

for alert in alerts:
  alert_id = alert["number"]
  state = alert["state"]
  severity = convert_severity(str(alert["securityVulnerability"]["severity"])).title()
  package_name = alert["securityVulnerability"]["package"]["name"]
  description = alert["securityVulnerability"]["advisory"]["description"]

  if severity_prefix:
    severity_label = f"{severity_prefix} {severity}"
  else: 
    severity_label = severity

  # Create a title for the issue
  issue_title = f"Dependabot Alert #{alert_id} - {package_name} is vulnerable"

  # Check if an issue already exists
  issue_exists = any(issue.title == issue_title for issue in repo.get_issues(state="open"))
  if issue_exists or state != 'OPEN':
    dep_skipped_issues.append(alert_id)
  else:
    # Create a new issue
    alert_url = f"https://github.com/{owner}/{repo_name}/security/dependabot/{alert_id}"
    print(f"Severity: {severity_label} Labels: {custom_labels}")
    repo.create_issue(
      title=issue_title,
      body=f"{description}\n\n[Dependabot Alert Link]({alert_url})",
      labels=[severity_label] + custom_labels
    )
    dep_created_issues.append(alert_id)

print(f"Created issue IDs: {dep_created_issues}")
print(f"Skipped issue IDs: {dep_skipped_issues}")

# Get CodeQL alerts

codescan_alerts = repo.get_codescan_alerts()

scan_created_issues = []
scan_skipped_issues = []

for alert in codescan_alerts:
  alert_id = alert.number
  created_at = alert.created_at
  dismissed_at = alert.dismissed_at
  tool_name = alert.tool.name
  tool_version = alert.tool.version
  tool_guid = alert.tool.guid
  rule_name = alert.rule.name
  rule_severity_level = alert.rule.security_severity_level
  rule_severity = alert.rule.severity
  rule_description = alert.rule.description
  recent_instance_ref = alert.most_recent_instance.ref
  recent_instance_state = alert.most_recent_instance.state
  location = alert.most_recent_instance.location
  message_text = alert.most_recent_instance.message['text']
  severity = convert_severity(str(rule_severity_level)).title()

  if severity_prefix:
    severity_label = f"{severity_prefix} {severity}"
  else:
    severity_label = severity

  # Construct the issue title and body
  issue_title = f"CodeQL Alert #{alert_id} - Security rule {rule_name} triggered"
  issue_body = f"""
  **Tool**: {tool_name} ({tool_version})
  **Rule**: {rule_name}
  **Severity**: {rule_severity} (Security level: {rule_severity_level})
  **Description**: {rule_description}
  **Instance reference**: {recent_instance_ref}
  **Instance state**: {recent_instance_state}
  **Location**: {location}
  **Message**: {message_text}
  """

  # Check if the issue already exists
  issue_exists = any(issue.title == issue_title for issue in repo.get_issues(state="open"))

  # If the issue already exists or the alert has been dismissed, skip it
  if issue_exists or dismissed_at is not None:
    scan_skipped_issues.append(alert_id)
  else:
    # Create a new issue
    alert_url = f"https://github.com/{owner}/{repo_name}/security/code-scanning/{alert_id}"
    print(f"Severity: {severity_label} Labels: {custom_labels}")
    repo.create_issue(
      title=issue_title,
      body=f"{issue_body}\n\n[CodeQL Alert Link]({alert_url})",
      labels=[severity_label] + custom_labels
    )
    scan_created_issues.append(alert_id)

print(f"Created issue IDs: {scan_created_issues}")
print(f"Skipped issue IDs: {scan_skipped_issues}")