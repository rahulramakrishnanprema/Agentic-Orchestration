"""
GitHub Service - Handles GitHub operations
"""

from github import Github
from config.settings import config

class GitHubService:
    def __init__(self, token=None):
        self.client = Github(token or config.GITHUB_TOKEN)

    def create_pr(self, repo_name, title, body, head, base):
        repo = self.client.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return pr.html_url