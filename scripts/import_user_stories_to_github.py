#!/usr/bin/env python3
"""
Import User Stories from Markdown to GitHub Issues

This script combines data from user-stories.md (full details) and Sprint-plan.md
(sprint info, story points, dependencies) to create comprehensive GitHub issues.

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
    """Parse user stories from markdown files."""

    def __init__(self, user_stories_path: str, sprint_plan_path: str):
        self.user_stories_path = Path(user_stories_path)
        self.sprint_plan_path = Path(sprint_plan_path)

        if not self.user_stories_path.exists():
            raise FileNotFoundError(f"User stories file not found: {user_stories_path}")
        if not self.sprint_plan_path.exists():
            raise FileNotFoundError(f"Sprint plan file not found: {sprint_plan_path}")

    def parse(self) -> List[Dict]:
        """Parse all user stories combining data from both files."""
        # Parse full details from user-stories.md
        print("[*] Parsing detailed user stories from user-stories.md...")
        detailed_stories = self._parse_user_stories_md()

        # Parse sprint info from Sprint-plan.md
        print("[*] Parsing sprint information from Sprint-plan.md...")
        sprint_info = self._parse_sprint_plan_md()

        # Merge the data
        print("[*] Merging story details with sprint information...")
        merged_stories = self._merge_story_data(detailed_stories, sprint_info)

        return merged_stories

    def _parse_user_stories_md(self) -> Dict[str, Dict]:
        """Parse user-stories.md for full story details."""
        with open(self.user_stories_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern to match user stories
        story_pattern = r'### (US-\d+|S\d+-\d+): (.+?)\n(.*?)(?=\n### (?:US-|S\d+-)|\n## End of User Stories|\Z)'
        matches = re.findall(story_pattern, content, re.DOTALL)

        stories_dict = {}
        for match in matches:
            story_id, title, body = match
            story = self._parse_story_body(story_id, title, body)
            stories_dict[story_id] = story

        print(f"   Found {len(stories_dict)} detailed user stories")
        return stories_dict

    def _parse_sprint_plan_md(self) -> Dict[str, Dict]:
        """Parse Sprint-plan.md for sprint organization and metadata."""
        with open(self.sprint_plan_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sprint_info = {}

        # Pattern to match sprint sections
        sprint_pattern = r'# (Sprint \d+|Sprint 0)(.*?)(?=\n# (?:Sprint|Summary|MVP)|\Z)'
        sprint_sections = re.findall(sprint_pattern, content, re.DOTALL)

        for sprint_header, sprint_content in sprint_sections:
            sprint_name = sprint_header.strip()

            # Extract sprint goal
            goal_match = re.search(r'## Goal\s*\n\s*(.+?)(?=\n\n|\n#)', sprint_content, re.DOTALL)
            sprint_goal = goal_match.group(1).strip() if goal_match else ''

            # Parse table rows for story metadata
            # Format: | ID | Story | Repo | SP | Dependency |
            table_pattern = r'\|\s*(S\d+-\d+|US-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|'
            story_rows = re.findall(table_pattern, sprint_content)

            for story_id, story_title, repos, sp, dependency in story_rows:
                story_id = story_id.strip()

                # Skip header rows
                if story_id in ['ID', 'Story']:
                    continue

                sprint_info[story_id] = {
                    'sprint': sprint_name,
                    'sprint_goal': sprint_goal,
                    'story_title': story_title.strip(),
                    'repos': [r.strip() for r in repos.split(',') if r.strip()],
                    'story_points': int(sp),
                    'dependency': dependency.strip()
                }

        print(f"   Found {len(sprint_info)} stories in sprint plan")
        return sprint_info

    def _merge_story_data(self, detailed_stories: Dict, sprint_info: Dict) -> List[Dict]:
        """Merge detailed story data with sprint information."""
        merged = []

        for story_id, sprint_data in sprint_info.items():
            # Get detailed story data if available
            story_detail = detailed_stories.get(story_id, {})

            # Merge the data
            merged_story = {
                'id': story_id,
                'title': story_detail.get('title', f"{story_id}: {sprint_data['story_title']}"),
                'sprint': sprint_data['sprint'],
                'sprint_goal': sprint_data['sprint_goal'],
                'repos': sprint_data['repos'],
                'story_points': sprint_data['story_points'],
                'dependency': sprint_data['dependency'],
                'as_a': story_detail.get('as_a', ''),
                'i_want_to': story_detail.get('i_want_to', ''),
                'so_that': story_detail.get('so_that', ''),
                'acceptance_criteria': story_detail.get('acceptance_criteria', []),
                'edge_cases': story_detail.get('edge_cases', []),
                'validation_rules': story_detail.get('validation_rules', []),
                'error_scenarios': story_detail.get('error_scenarios', [])
            }

            merged.append(merged_story)

        # Sort by sprint and story ID
        merged.sort(key=lambda x: (x['sprint'], x['id']))

        return merged

    def _parse_story_body(self, story_id: str, title: str, body: str) -> Dict:
        """Parse individual user story body for all details."""
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
        as_a_match = re.search(r'\*\*As (?:a|an)\*\* (.+?)(?=\n)', body, re.IGNORECASE)
        if as_a_match:
            story['as_a'] = as_a_match.group(1).strip()

        i_want_match = re.search(r'\*\*I want(?:\s+to)?\*\* (.+?)(?=\n)', body, re.IGNORECASE)
        if i_want_match:
            story['i_want_to'] = i_want_match.group(1).strip()

        so_that_match = re.search(r'\*\*So that\*\* (.+?)(?=\n)', body, re.IGNORECASE)
        if so_that_match:
            story['so_that'] = so_that_match.group(1).strip()

        # Extract sections
        story['acceptance_criteria'] = self._extract_section(body, 'Acceptance Criteria')
        story['edge_cases'] = self._extract_section(body, 'Edge Cases')
        story['validation_rules'] = self._extract_section(body, 'Validation Rules')
        story['error_scenarios'] = self._extract_section(body, 'Error Scenarios')

        return story

    def _extract_section(self, body: str, section_name: str) -> List[str]:
        """Extract bullet points and Given-When-Then from a section."""
        pattern = rf'\*\*{section_name}:\*\*\n(.*?)(?=\n\*\*[A-Z]|\n---|\n##|\Z)'
        match = re.search(pattern, body, re.DOTALL)

        if not match:
            return []

        section_content = match.group(1).strip()
        items = []

        # Extract bullet points
        bullets = re.findall(r'^- (.+)$', section_content, re.MULTILINE)
        items.extend([bullet.strip() for bullet in bullets])

        # Extract Given-When-Then patterns
        gwt_pattern = r'- (Given .+?)\n- (When .+?)\n- (Then .+?)(?=\n-|\n\*\*|\Z)'
        gwt_matches = re.findall(gwt_pattern, section_content, re.DOTALL)
        for given, when, then in gwt_matches:
            gwt_text = f"{given.strip()} {when.strip()} {then.strip()}"
            if gwt_text not in items:
                items.append(gwt_text)

        return items


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
            print(f"Sprint: {story.get('sprint', 'N/A')}")
            print(f"Story Points: {story.get('story_points', 'N/A')}")
            print(f"Repos: {', '.join(story.get('repos', []))}")
            print(f"Dependency: {story.get('dependency', 'None')}")
            print(f"Labels: {', '.join(issue_data['labels'])}")
            print(f"Body preview (first 300 chars):\n{issue_body[:300]}...")
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
        """Format user story as comprehensive GitHub issue body."""
        body_parts = []

        # Sprint and Metadata Information
        body_parts.append("## 📋 Sprint Information\n")
        body_parts.append(f"**Sprint:** {story.get('sprint', 'N/A')}")
        if story.get('sprint_goal'):
            body_parts.append(f"**Sprint Goal:** {story['sprint_goal']}")
        body_parts.append(f"**Story Points:** {story.get('story_points', 'N/A')}")

        if story.get('repos'):
            repos_formatted = ', '.join([f'`{r}`' for r in story['repos']])
            body_parts.append(f"**Repositories:** {repos_formatted}")

        if story.get('dependency') and story['dependency'] not in ['None', 'none', 'N/A']:
            body_parts.append(f"**Dependencies:** {story['dependency']}")

        body_parts.append("")

        # User Story (if available)
        if story.get('as_a') or story.get('i_want_to') or story.get('so_that'):
            body_parts.append("## 👤 User Story\n")
            if story.get('as_a'):
                body_parts.append(f"**As a** {story['as_a']}")
            if story.get('i_want_to'):
                body_parts.append(f"**I want to** {story['i_want_to']}")
            if story.get('so_that'):
                body_parts.append(f"**So that** {story['so_that']}")
            body_parts.append("")

        # Acceptance Criteria
        if story['acceptance_criteria']:
            body_parts.append("## ✅ Acceptance Criteria\n")
            for criteria in story['acceptance_criteria']:
                # Clean up the criteria text
                criteria_text = criteria.replace('Given ', '**Given** ') \
                                       .replace('When ', '**When** ') \
                                       .replace('Then ', '**Then** ') \
                                       .replace('And ', '**And** ')
                body_parts.append(f"- [ ] {criteria_text}")
            body_parts.append("")

        # Edge Cases
        if story['edge_cases']:
            body_parts.append("## ⚠️ Edge Cases\n")
            for edge_case in story['edge_cases']:
                body_parts.append(f"- {edge_case}")
            body_parts.append("")

        # Validation Rules
        if story['validation_rules']:
            body_parts.append("## 🔒 Validation Rules\n")
            for rule in story['validation_rules']:
                body_parts.append(f"- {rule}")
            body_parts.append("")

        # Error Scenarios
        if story['error_scenarios']:
            body_parts.append("## ❌ Error Scenarios\n")
            for error in story['error_scenarios']:
                # Highlight error codes
                error_text = re.sub(r'`([A-Z_]+)`', r'**`\1`**', error)
                body_parts.append(f"- {error_text}")
            body_parts.append("")

        # Technical Notes (if any)
        if story.get('technical_notes'):
            body_parts.append("## 🔧 Technical Notes\n")
            body_parts.append(story['technical_notes'])
            body_parts.append("")

        # Footer
        body_parts.append("---")
        body_parts.append(f"📄 **Source:** user-stories.md + Sprint-plan.md")
        body_parts.append(f"🔖 **Story ID:** `{story['id']}`")
        if story.get('dependency') and story['dependency'] not in ['None', 'none', 'N/A']:
            body_parts.append(f"🔗 **Blocked by:** {story['dependency']}")

        return "\n".join(body_parts)

    def _get_labels(self, story: Dict) -> List[str]:
        """Determine comprehensive labels for the issue."""
        labels = list(self.config.get('default_labels', ['user-story']))

        # Add sprint label
        if story.get('sprint'):
            sprint_slug = story['sprint'].lower().replace(' ', '-').replace('&', 'and')
            labels.append(sprint_slug)

        # Add story points label
        if story.get('story_points'):
            sp = story['story_points']
            if sp <= 3:
                labels.append('size: small')
            elif sp <= 8:
                labels.append('size: medium')
            else:
                labels.append('size: large')

        # Add repository labels
        if story.get('repos'):
            for repo in story['repos']:
                repo_clean = repo.strip().lower()
                if repo_clean and repo_clean != 'sp':
                    labels.append(f"repo:{repo_clean}")

        # Add dependency label
        if story.get('dependency') and story['dependency'] not in ['None', 'none', 'N/A']:
            labels.append('has-dependency')

        # Extract numeric ID for category-based labels
        story_id = story['id']
        if story_id.startswith('US-'):
            story_number = int(story_id.replace('US-', ''))

            # Add category labels from config
            label_mapping = self.config.get('label_mapping', {})
            for label_name, range_config in label_mapping.items():
                if range_config['start'] <= story_number <= range_config['end']:
                    labels.append(label_name)

            # Add priority labels from config
            if 'priority_mapping' in self.config:
                for priority, range_config in self.config['priority_mapping'].items():
                    if range_config['start'] <= story_number <= range_config['end']:
                        labels.append(priority)
                        break  # Only add one priority
        elif story_id.startswith('S'):
            labels.append('sprint-setup')
            labels.append('priority: critical')

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
        description='Import user stories from markdown to GitHub issues with full details'
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
        help='Import only stories from specific sprint (e.g., "Sprint 1", "0")'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip stories that already exist as issues'
    )

    args = parser.parse_args()

    # Load configuration
    print("[*] Loading configuration...")
    config = load_config(args.config)

    # Set default paths if not in config
    if 'user_stories_file' not in config:
        config['user_stories_file'] = '../Documents/user-stories.md'
    if 'sprint_plan_file' not in config:
        config['sprint_plan_file'] = '../Documents/Sprint-plan.md'

    # Parse user stories (combining both files)
    print(f"\n[*] Parsing user stories...")
    try:
        parser = UserStoryParser(
            config['user_stories_file'],
            config['sprint_plan_file']
        )
        all_stories = parser.parse()
        print(f"[+] Successfully merged {len(all_stories)} user stories\n")
    except Exception as e:
        print(f"[!] Error parsing user stories: {e}")
        sys.exit(1)

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
                print(f"[-] Skipped {story['id']}: Already exists")
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
        print(f"   [-] Skipped: {skipped_count}")
    if failed_count > 0:
        print(f"   [!] Failed: {failed_count}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[*] Run without --dry-run to create issues")


if __name__ == '__main__':
    main()
