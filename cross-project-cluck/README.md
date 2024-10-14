# cross-project-cluck

Helps identify cross-project repo access in Azure DevOps.

## What does it do? 

For each pipeline run harvested (API limited to latest 1000), it adds a row for each repository accessed. Determines if the access is cross-project. Sets the status to "REVIEW" for cross-project access or "OK" for same-project access.

It outputs a JSON file and matching CSV. It also outputs a list of projects it found.

```json
[
    {
        "home_project": "HOME PROJECT",
        "run": "Link to the Pipeline Run",
        "project": "HOME PROJECT",
        "repo": "Repo Accessed",
        "branch": "Branch reference",
        "cross_project": false,
        "status": "OK"
    },
    {
        "home_project": "HOME PROJECT",
        "run": "Link to the Pipeline Run",
        "project": "CROSS PROJECT",
        "repo": "Repo Accessed",
        "branch": "Branch reference",
        "cross_project": true,
        "status": "REVIEW"
    }
]
```

## Installation

Install via `pip`:

```bash
pip install cross-project-cluck
```

## Usage

Run the tool using the CLI:

1. With arguments:

    ```bash
    cluck --simulate-approve-all --organization my_org --pat_token my_secret_token
    ```

2. Without arguments (uses `config.json` or environment variables):

    ```bash
    cluck --simulate-approve-all
    ```

## Configuration

You can provide `organization` and `pat_token` in the following ways:

1. **Command-line arguments**:

    ```bash
    cluck --organization my_org --pat_token my_secret_token
    ```

2. **Environment variables**:

    ```bash
    export ORGANIZATION=my_org
    export PAT_TOKEN=my_secret_token
    cluck
    ```

3. **`config.json`** file:

    Create a `config.json` file:

    ```json
    {
        "organization": "my_org",
        "pat_token": "my_secret_token"
    }
    ```

### Priority

The tool checks for configuration in this order:
1. Command-line arguments
2. Environment variables
3. `config.json`

### If not using pip, use the python code directly:

```bash
python cross_project_cluck.py -h
python cross_project_cluck.py --organization my_org --pat_token my_secret_token
python cross_project_cluck.py --simulate-approve-all --organization my_org --pat_token my_secret_token
```

