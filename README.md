# Quay.io Permission Sync Tool

This tool synchronizes repository permissions between Quay.io and Zendesk organizations. It ensures that Zendesk organizations have the correct access to Quay.io repositories based on their team IDs.

## Features

- Reads repository names from an input file
- Fetches all current Zendesk organizations with 'current_customer' tag
- Retrieves Quay.io team permissions for each organization
- Manages repository permissions in Quay.io (add or remove) for specified teams
- Supports dry-run mode for testing changes
- Provides detailed logging of all operations

## Prerequisites

- Python 3.x
- Access to Zendesk API
- Access to Quay.io API
- Required Python packages (see requirements.txt)

## Environment Variables

The following environment variables must be set:

```bash
ZENDESK_EMAIL=your_zendesk_email
ZENDESK_TOKEN=your_zendesk_token
ZENDESK_SUBDOMAIN=your_zendesk_subdomain
QUAY_IO_TOKEN=your_quay_io_token
```

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Create an input file containing the repository names (one per line)
2. Run the script with one of the following commands:

   To add repositories to all teams:

   ```bash
   python sync_permissions.py --input your_repo_file.txt
   ```

   To remove repositories from all teams:

   ```bash
   python sync_permissions.py --input your_repo_file.txt --remove
   ```

   To process a specific team:

   ```bash
   python sync_permissions.py --input your_repo_file.txt --org-code TEAM_ID
   ```

   To preview changes without making them:

   ```bash
   python sync_permissions.py --input your_repo_file.txt --dry-run
   ```

## Input File Format

The input file should contain one repository name per line. Example:

```
repo1
repo2
repo3
```

## Command Line Options

- `--input`: (Required) Path to the input file containing repository names
- `--org-code`: (Optional) Process a specific 10-character organization code
- `--remove`: (Optional) Remove repositories from teams instead of adding them
- `--dry-run`: (Optional) Show what would be done without making changes

## Logging

The script provides detailed logging of all operations, including:

- Number of repositories read from the input file
- Organizations processed
- Repository permissions created or removed
- Any errors or issues encountered

## Error Handling

The script includes comprehensive error handling for:

- File reading errors
- API connection issues
- Invalid team IDs
- Missing permissions
- Network errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Add your license information here]
