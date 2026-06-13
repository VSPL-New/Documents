#!/usr/bin/env python3
"""
Import User Stories from Markdown to GitHub Issues

This script parses user-stories.md or Sprint-plan.md and creates GitHub issues.
Configuration is loaded from config.json.

Requirements:
    pip install requests
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests


class UserStoryParser:
    """Parse user stories from markdown file."""

    def __init__(self, md_file_path: str):
        self.md_file_path = Path(md_file_path)
        if not self.md_file_path.exists():
            raise FileNotFoundError(f"User stories file not found: {md_file_path}")

    def parse(self) -> List[Dict]:
        """Parse all user stories from markdown file."""
        with open(self.md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if this is a Sprint-plan.md file
        if 'Sprint' in content and '## Stories' in content:
            return self._parse_sprint_plan(content)
        else:
            return self._parse_user_stories(content)

    def _parse_user_stories(self, content: str) -> List[Dict]:
        """Parse traditional user-stories.md format."""
        story_pattern = r'### (US-\d+): (.+?)\n(.*?)(?=\n### US-|\n## End of User Stories|\Z)'
        matches = re.findall(story_pattern, content, re.DOTALL)

        user_stories = []
        for match in matches:
            story_id, title, body = match
            story = self._parse_story_body(story_id, title, body)
            user_stories.append(story)

        return user_stories

    def _parse_sprint_plan(self, content: str) -> List[Dict]:
        """Parse Sprint-plan.md format with sprint organization."""
        stories = []

        sprint_pattern = r'# (Sprint \d+(?:\s*-[^#]+)?|MVP RELEASE)(.*?)(?=\n# (?:Sprint|MVP)|\Z)'
        sprint_sections = re.findall(sprint_pattern, content, re.DOTALL)

        for sprint_header, sprint_content in sprint_sections:
            sprint_name = sprint_header.strip()

            if 'MVP RELEASE' in sprint_name:
                continue

            goal_match = re.search(r'## Goal\s*\n\s*(.+?)(?=\n\n|\n#)', sprint_content, re.DOTALL)
            sprint_goal = goal_match.group(1).strip() if goal_match else ''

            # Match table rows - handle both 3-column and 5-column formats
            # Format 1: | ID | Story | Repo | SP | Dependency |
            # Format 2: | ID | User Story | Repo |
            table_pattern = r'\|\s*(S\d+-\d+|US-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'
            story_rows = re.findall(table_pattern, sprint_content)

            seen_ids = set()
            for story_id, story_title, repos_and_more in story_rows:
                story_id = story_id.strip()

                # Skip duplicate IDs (header rows or repeated stories)
                if story_id in seen_ids:
                    continue
                seen_ids.add(story_id)

                # Extract just the repo column (first item before | or end)
                repos_col = repos_and_more.split('|')[0].strip()

                story = {
                    'id': story_id,
                    'title': f"{story_id}: {story_title.strip()}",
                    'sprint': sprint_name,
                    'sprint_goal': sprint_goal,
                    'repos': [r.strip() for r in repos_col.split(',')],
                    'as_a': '',
                    'i_want_to': '',
                    'so_that': '',
                    'acceptance_criteria': [],
                    'edge_cases': [],
                    'validation_rules': [],
                    'error_scenarios': []
                }
                stories.append(story)

        return stories

    def _parse_story_body(self, story_id: str, title: str, body: str) -> Dict:
        """Parse individual user story body."""
        story = {
            'id': story_id,
            'title': f"{story_id}: {title.strip()}",
            'as_a': '',
            'i_want_to': '',
            'so_that': '',
            'acceptance_criteria': [],
            'edge_cases': [],
            'validation_rules': [],
            'error_scenarios': []
        }

        # Extract "As a / I want to / So that"
        as_a_match = re.search(r'\*\*As a\*\* (.+?)(?=\n)', body)
        if as_a_match:
            story['as_a'] = as_a_match.group(1).strip()

        i_want_match = re.search(r'\*\*I want to\*\* (.+?)(?=\n)', body)
        if i_want_match:
            story['i_want_to'] = i_want_match.group(1).strip()

        so_that_match = re.search(r'\*\*So that\*\* (.+?)(?=\n)', body)
        if so_that_match:
            story['so_that'] = so_that_match.group(1).strip()

        # Extract sections
        story['acceptance_criteria'] = self._extract_section(body, 'Acceptance Criteria')
        story['edge_cases'] = self._extract_section(body, 'Edge Cases')
        story['validation_rules'] = self._extract_section(body, 'Validation Rules')
        story['error_scenarios'] = self._extract_section(body, 'Error Scenarios')

        return story

    def _extract_section(self, body: str, section_name: str) -> List[str]:
        """Extract bullet points from a section."""
        pattern = rf'\*\*{section_name}:\*\*\n(.*?)(?=\n\*\*[A-Z]|\n---|\Z)'
        match = re.search(pattern, body, re.DOTALL)

        if not match:
            return []

        section_content = match.group(1).strip()
        # Extract bullet points
        bullets = re.findall(r'^- (.+)$', section_content, re.MULTILINE)
        return [bullet.strip() for bullet in bullets]


class GitHubIssueCreator:
    """Create GitHub issues via API."""

    def __init__(self, config: Dict):
        self.config = config
        self.base_url = f"https://api.github.com/repos/{config['repo_owner']}/{config['repo_name']}"
        self.headers = {
            'Authorization': f"token {config['github_token']}",
            'Accept': 'application/vnd.github.v3+json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def verify_access(self) -> bool:
        """Verify GitHub API access."""
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            print(f"[+] Successfully connected to {self.config['repo_owner']}/{self.config['repo_name']}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"[!] Failed to connect to GitHub: {e}")
            return False

    def create_issue(self, story: Dict, dry_run: bool = False) -> Optional[Dict]:
        """Create a GitHub issue from user story."""
        issue_body = self._format_issue_body(story)

        issue_data = {
            'title': story['title'],
            'body': issue_body,
            'labels': self._get_labels(story)
        }

        # Add milestone if configured
        if self.config.get('milestone_number'):
            issue_data['milestone'] = self.config['milestone_number']

        # Add assignees if configured
        if self.config.get('default_assignees'):
            issue_data['assignees'] = self.config['default_assignees']

        if dry_run:
            print(f"\n{'='*60}")
            print(f"[DRY RUN] Would create issue: {story['title']}")
            print(f"Labels: {', '.join(issue_data['labels'])}")
            print(f"Body preview (first 200 chars):\n{issue_body[:200]}...")
            print(f"{'='*60}")
            return {'number': 'DRY_RUN', 'html_url': 'DRY_RUN'}

        try:
            response = self.session.post(
                f"{self.base_url}/issues",
                json=issue_data
            )
            response.raise_for_status()
            issue = response.json()
            print(f"[+] Created issue #{issue['number']}: {story['title']}")
            return issue
        except requests.exceptions.RequestException as e:
            print(f"[!] Failed to create issue {story['title']}: {e}")
            if hasattr(e.response, 'text'):
                print(f"   Response: {e.response.text}")
            return None

    def _format_issue_body(self, story: Dict) -> str:
        """Format user story as GitHub issue body."""
        body_parts = []

        # Sprint information (if available)
        if story.get('sprint'):
            body_parts.append("## Sprint Information\n")
            body_parts.append(f"**Sprint:** {story['sprint']}")
            if story.get('sprint_goal'):
                body_parts.append(f"**Sprint Goal:** {story['sprint_goal']}")
            if story.get('repos'):
                body_parts.append(f"**Repositories:** {', '.join(story['repos'])}")
            body_parts.append("")

        # User Story (if traditional format)
        if story.get('as_a') or story.get('i_want_to') or story.get('so_that'):
            body_parts.append("## User Story\n")
            if story.get('as_a'):
                body_parts.append(f"**As a** {story['as_a']}")
            if story.get('i_want_to'):
                body_parts.append(f"**I want to** {story['i_want_to']}")
            if story.get('so_that'):
                body_parts.append(f"**So that** {story['so_that']}")
            body_parts.append("")

        # Acceptance Criteria
        if story['acceptance_criteria']:
            body_parts.append("## Acceptance Criteria\n")
            for criteria in story['acceptance_criteria']:
                body_parts.append(f"- [ ] {criteria}")
            body_parts.append("")

        # Edge Cases
        if story['edge_cases']:
            body_parts.append("## Edge Cases\n")
            for edge_case in story['edge_cases']:
                body_parts.append(f"- {edge_case}")
            body_parts.append("")

        # Validation Rules
        if story['validation_rules']:
            body_parts.append("## Validation Rules\n")
            for rule in story['validation_rules']:
                body_parts.append(f"- {rule}")
            body_parts.append("")

        # Error Scenarios
        if story['error_scenarios']:
            body_parts.append("## Error Scenarios\n")
            for error in story['error_scenarios']:
                body_parts.append(f"- {error}")
            body_parts.append("")

        # Footer
        body_parts.append("---")
        source = "Sprint-plan.md" if story.get('sprint') else "user-stories.md"
        body_parts.append(f"**Source:** {source}")
        body_parts.append(f"**Story ID:** {story['id']}")

        return "\n".join(body_parts)

    def _get_labels(self, story: Dict) -> List[str]:
        """Determine labels for the issue based on story ID and config."""
        labels = list(self.config.get('default_labels', ['user-story']))

        # Add sprint label if available
        if story.get('sprint'):
            sprint_slug = story['sprint'].lower().replace(' ', '-').replace('&', 'and')
            labels.append(sprint_slug)

        # Add repository labels
        if story.get('repos'):
            for repo in story['repos']:
                repo_clean = repo.strip().lower()
                if repo_clean and repo_clean != 'sp':
                    labels.append(f"repo:{repo_clean}")

        # Extract numeric ID for range-based labels
        story_id = story['id']
        if story_id.startswith('US-'):
            story_number = int(story_id.replace('US-', ''))

            label_mapping = self.config.get('label_mapping', {})
            for label_name, range_config in label_mapping.items():
                if range_config['start'] <= story_number <= range_config['end']:
                    labels.append(label_name)

            if 'priority_mapping' in self.config:
                for priority, range_config in self.config['priority_mapping'].items():
                    if range_config['start'] <= story_number <= range_config['end']:
                        labels.append(priority)
        elif story_id.startswith('S'):
            labels.append('sprint-setup')

        # Remove duplicates while preserving order
        seen = set()
        unique_labels = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)

        return unique_labels

    def issue_exists(self, story_id: str) -> bool:
        """Check if issue already exists by searching title."""
        try:
            search_query = f"repo:{self.config['repo_owner']}/{self.config['repo_name']} is:issue {story_id} in:title"
            response = self.session.get(
                "https://api.github.com/search/issues",
                params={'q': search_query}
            )
            response.raise_for_status()
            results = response.json()
            return results['total_count'] > 0
        except requests.exceptions.RequestException:
            return False


def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"[!] Config file not found: {config_path}")
        print("Please create config.json using config.example.json as template")
        sys.exit(1)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Validate required fields
    required_fields = ['github_token', 'repo_owner', 'repo_name']
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        print(f"[!] Missing required config fields: {', '.join(missing_fields)}")
        sys.exit(1)

    return config


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Import user stories from markdown to GitHub issues'
    )
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to config file (default: config.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview issues without creating them'
    )
    parser.add_argument(
        '--story-range',
        help='Import only specific stories (e.g., "1-10" or "68-100")'
    )
    parser.add_argument(
        '--sprint',
        help='Import only stories from specific sprint (e.g., "Sprint 1", "Sprint 0")'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip stories that already exist as issues'
    )
    parser.add_argument(
        '--source',
        choices=['user-stories', 'sprint-plan'],
        help='Source file type (auto-detected if not specified)'
    )

    args = parser.parse_args()

    # Load configuration
    print("[*] Loading configuration...")
    config = load_config(args.config)

    # Parse user stories
    print(f"[*] Parsing user stories from {config['user_stories_file']}...")
    parser = UserStoryParser(config['user_stories_file'])
    all_stories = parser.parse()
    print(f"[+] Found {len(all_stories)} user stories")

    # Filter stories by range if specified
    if args.story_range:
        start, end = map(int, args.story_range.split('-'))
        all_stories = [s for s in all_stories
                      if s['id'].startswith('US-') and
                      start <= int(s['id'].replace('US-', '')) <= end]
        print(f"[*] Filtered to {len(all_stories)} stories (US-{start:03d} to US-{end:03d})")

    # Filter stories by sprint if specified
    if args.sprint:
        sprint_filter = args.sprint if args.sprint.startswith('Sprint') else f"Sprint {args.sprint}"
        all_stories = [s for s in all_stories if s.get('sprint', '').startswith(sprint_filter)]
        print(f"[*] Filtered to {len(all_stories)} stories from {sprint_filter}")

    if not all_stories:
        print("[!] No stories to import")
        sys.exit(1)

    # Initialize GitHub client
    print("\n[*] Connecting to GitHub...")
    github = GitHubIssueCreator(config)

    if not args.dry_run and not github.verify_access():
        sys.exit(1)

    # Create issues
    print(f"\n{'='*60}")
    if args.dry_run:
        print("[*] DRY RUN MODE - No issues will be created")
    else:
        print("[*] Starting issue creation...")
    print(f"{'='*60}\n")

    created_count = 0
    skipped_count = 0
    failed_count = 0

    for story in all_stories:
        # Check if issue already exists
        if args.skip_existing and not args.dry_run:
            if github.issue_exists(story['id']):
                print(f"[-]  Skipped {story['id']}: Already exists")
                skipped_count += 1
                continue

        result = github.create_issue(story, dry_run=args.dry_run)

        if result:
            created_count += 1
        else:
            failed_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("[*] Summary:")
    print(f"   [+] Created: {created_count}")
    if skipped_count > 0:
        print(f"   [-]  Skipped: {skipped_count}")
    if failed_count > 0:
        print(f"   [!] Failed: {failed_count}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[*] Run without --dry-run to create issues")


if __name__ == '__main__':
    main()
