#!/usr/bin/env python3

import logging
import sys
import os
import requests
import traceback
import json
import argparse
from typing import List, Dict, Optional, Any
from datetime import datetime
from zenpy import Zenpy
from zenpy.lib.api_objects import User, Organization

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_repo_file(file_path: str) -> Dict[str, bool]:
    """
    Read repository names from a file and create a map.
    
    Args:
        file_path (str): Path to the file containing repository names
        
    Returns:
        Dict[str, bool]: Dictionary with repository names as keys and True as values
    """
    try:
        with open(file_path, 'r') as f:
            # Read lines, strip whitespace, filter empty lines, and create a map
            return {line.strip(): True for line in f if line.strip()}
    except Exception as e:
        logger.error(f"Error reading repository file: {str(e)}\n{traceback.format_exc()}")
        raise

def main():
    """Main entry point for the script."""
    try:
        # Set up command line argument parsing
        parser = argparse.ArgumentParser(description='Sync Quay.io permissions with Zendesk organizations')
        parser.add_argument('--input', required=True, help='Input file containing repository names')
        parser.add_argument('--org-code', help='10-character organization code to process (optional)')
        args = parser.parse_args()

        # Read repository names from file into a map
        repo_map = read_repo_file(args.input)
        logger.info(f"Read {len(repo_map)} repository names from {args.input}")
        
        sync = PermissionSync()
        sync._setup_connections()
        
        if args.org_code:
            # Process single organization directly without Zendesk lookup
            logger.info(f"Processing team ID: {args.org_code}")
            try:
                # Get and display Quay.io team permissions for this organization
                team_repos = sync.get_quay_teams('dremio', args.org_code)
                if team_repos is None:
                    logger.error(f"Failed to fetch team permissions for team ID: {args.org_code}")
                    sys.exit(1)
                elif not team_repos:
                    logger.info(f"No repositories found for team ID: {args.org_code}")
                else:
                    logger.info(f"\nRepositories for team ID: {args.org_code}:")
                    for repo in team_repos:
                        if repo in repo_map:
                            logger.info(f"  - {repo} (in target list)")
                        else:
                            logger.info(f"  - {repo} (not in target list)")
                    
                    # Create missing repositories
                    sync.create_repos(repo_map, team_repos, 'dremio', args.org_code)
                    
            except Exception as e:
                logger.error(f"Error processing team ID {args.org_code}: {str(e)}\n{traceback.format_exc()}")
                sys.exit(1)
        else:
            # Process all organizations
            logger.info("Fetching all Zendesk organizations...")
            organizations = sync.get_zendesk_organizations()
            
            # Track organizations with missing or invalid quay_io_team_id
            for org in organizations:
                # Check for quay_io_team_id
                team_id = org.get('organization_fields', {}).get('quay_io_team_id')
                if not team_id:
                    logger.info(f"Organization: {org['name']} (No Quay.io Team ID)")
                else:
                    logger.info(f"Organization: {org['name']} Quay.io Team ID: {team_id}")
                    try:
                        # Get and display Quay.io team permissions for this organization
                        team_repos = sync.get_quay_teams('dremio', team_id)  # Pass the team ID
                        if team_repos is None:
                            print(f"Failed to fetch team permissions for team ID: {team_id}")
                            continue  # Skip to next organization
                        elif not team_repos:
                            print(f"No repositories found for team ID: {team_id}")
                            continue  # Skip to next organization
                        else:
                            print(f"\nRepositories for {org['name']} (Team ID: {team_id}):")
                            for repo in team_repos:
                                if repo in repo_map:
                                    print(f"  - {repo} (in target list)")
                                else:
                                    print(f"  - {repo} (not in target list)")
                            
                            # Create missing repositories
                            sync.create_repos(repo_map, team_repos, 'dremio', team_id)
                            
                    except Exception as e:
                        print(f"Error processing team ID {team_id}: {str(e)}")
                        continue  # Skip to next organization
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

class PermissionSync:
    def __init__(self):
        """Initialize the PermissionSync class."""
        self.logger = logging.getLogger(__name__)
        self.zendesk_client = None
        self.quay_client = None
        self._setup_connections()

    def _setup_connections(self):
        """Set up connection to Zendesk and Quay.io using environment variables."""
        try:
            # Zendesk connection setup
            zendesk_email = os.getenv('ZENDESK_EMAIL')
            zendesk_token = os.getenv('ZENDESK_TOKEN')
            zendesk_subdomain = os.getenv('ZENDESK_SUBDOMAIN')
            
            if not all([zendesk_email, zendesk_token, zendesk_subdomain]):
                raise ValueError("Missing Zendesk credentials in environment variables")
            
            self.zendesk_client = Zenpy(
                subdomain=zendesk_subdomain,
                email=zendesk_email,
                token=zendesk_token
            )
            self.logger.info("Successfully connected to Zendesk")

            # Quay.io connection setup
            quay_token = os.getenv('QUAY_IO_TOKEN')
            
            if not quay_token:
                raise ValueError("Missing Quay.io OAuth token in environment variables")
            
            self.quay_client = {
                'token': quay_token,
                'base_url': 'https://quay.io/api/v1'
            }
            self.logger.info("Successfully connected to Quay.io")

        except Exception as e:
            self.logger.error(f"Failed to set up connections: {str(e)}\n{traceback.format_exc()}")
            raise

    def get_zendesk_organizations(self) -> List[Dict]:
        """
        Get all organizations from Zendesk that have either 'cloud_customer' or 'current_customer' tags.
        
        Returns:
            List[Dict]: List of organizations with their details
        """
        try:
            organizations = []
            for org in self.zendesk_client.organizations():
                # Check if organization has required tags
                tags = org.tags or []  # Handle case where tags might be None
                if 'current_customer' in tags:
                    organizations.append({
                        'id': org.id,
                        'name': org.name,
                        'domain_names': org.domain_names,
                        'created_at': org.created_at,
                        'updated_at': org.updated_at,
                        'details': org.details,
                        'notes': org.notes,
                        'tags': tags,
                        'organization_fields': org.organization_fields
                    })
                    self.logger.info(f"Included organization: {org.name}")
                else:
                    self.logger.debug(f"Skipped organization: {org.name}")
            return organizations
        except Exception as e:
            self.logger.error(f"Error getting Zendesk organizations: {str(e)}\n{traceback.format_exc()}")
            raise

    def get_quay_teams(self, org_name: str, team_id: str) -> List[str]:
        """
        Get team permissions from a Quay.io organization using their API
        
        Args:
            org_name (str): The name of the Quay.io organization
            team_id (str): The Quay.io team ID from Zendesk (used as teamname in API)
            
        Returns:
            List[str]: List of repository names
        """
        if not self.quay_client['token']:
            raise ValueError('Missing required Quay.io OAuth token')
        
        base_url = self.quay_client['base_url']
        # Use team_id as the teamname in the URL
        permissions_endpoint = f'/organization/{org_name}/team/{team_id}/permissions'
        
        headers = {
            'Authorization': f'Bearer {self.quay_client["token"]}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get permissions for the specific team
            permissions_response = requests.get(f'{base_url}{permissions_endpoint}', headers=headers)
            
            # Handle 404 errors separately without stack trace
            if permissions_response.status_code == 404:
                self.logger.error(f"Team {team_id} not found in organization {org_name}")
                return None
                
            permissions_response.raise_for_status()
            
            # Parse the JSON response
            data = permissions_response.json()
            
            # Extract repository names from the permissions array
            repo_names = []
            if isinstance(data, dict) and 'permissions' in data:
                for permission in data['permissions']:
                    if isinstance(permission, dict) and 'repository' in permission:
                        repo = permission['repository']
                        if isinstance(repo, dict) and 'name' in repo:
                            repo_names.append(repo['name'])
            
            return repo_names
                    
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError) or e.response.status_code != 404:
                self.logger.error(f"Error fetching Quay.io team permissions: {str(e)}\n{traceback.format_exc()}")
            return None

    def create_repos(self, target_repos: Dict[str, bool], team_repos: List[str], org_name: str, team_id: str) -> None:
        """
        Compare target repositories with team repositories and create missing ones.
        
        Args:
            target_repos (Dict[str, bool]): Dictionary of target repository names
            team_repos (List[str]): List of repositories the team currently has access to
            org_name (str): The Quay.io organization name
            team_id (str): The Quay.io team ID
        """
        try:
            # Convert team_repos to a set for faster lookup
            team_repo_set = set(team_repos)
            
            # Find repositories that need to be created
            repos_to_create = [repo for repo in target_repos.keys() if repo not in team_repo_set]
            
            if repos_to_create:
                print(f"\nRepositories to create for team {team_id}:")
                for repo in repos_to_create:
                    print(f"  - {repo}")
                    
                    # Prepare the request to add repository permissions
                    base_url = self.quay_client['base_url']
                    repo_path = f"{org_name}/{repo}"
                    permissions_endpoint = f'/repository/{repo_path}/permissions/team/{team_id}'
                    
                    headers = {
                        'Authorization': f'Bearer {self.quay_client["token"]}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Prepare the payload for adding repository permissions
                    payload = {
                        "role": "read"
                    }
                    
                    try:
                        # Add repository permissions to the team
                        response = requests.put(
                            f'{base_url}{permissions_endpoint}',
                            headers=headers,
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            print(f"    ✓ Successfully added {repo_path} to team {team_id}")
                        else:
                            print(f"    ✗ Failed to add {repo_path} to team {team_id}: {response.text}")
                        
                    except requests.exceptions.RequestException as e:
                        print(f"    ✗ Error adding {repo_path} to team {team_id}: {str(e)}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error in create_repos: {str(e)}\n{traceback.format_exc()}")
            raise

if __name__ == "__main__":
    main() 
