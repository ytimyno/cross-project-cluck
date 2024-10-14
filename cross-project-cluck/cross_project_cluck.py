import requests
import json
import os
import base64
import csv
import argparse

def display_chicken_art():
    chicken_art = r"""
             ,~.
          ,-'__ `-,
         {,-'  `. }              ,')
        ,( a )   `-.__         ,',')~,
       <=.) (         `-.__,==' ' ' '}
         (   )                      /
          `-'\   ,                    )
              |  \        `~.        /
              \   `._        \      /
               \     `._____,'    ,'
                `-.________,-'
    """

    pipeline_art = r"""
          _____________________________________________________
         /                                                     \
        |                      PIPELINE                        |
         \_____________________________________________________/
    """

    print(chicken_art)
    print(pipeline_art)
    print("Why did the chicken cross the pipeline? To access the repo on the other side!")

def create_directory_if_not_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_projects(api_endpoint="projects", api_version="?api-version=7.1"):

        url = f"https://dev.azure.com/{organization}/_apis/{api_endpoint}{api_version}"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {pat_token}',
        }

        full_projects={}

        try:
            
            # Make the GET request
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Write output to a file named according to the resource type
            directory = f"outputs"
            create_directory_if_not_exists(directory)
            file_name = f"{directory}/projects.json"
            with open(file_name, 'w') as file:
                json.dump(data, file, indent=4)

            # Extract the mapping of project ID to project name
            full_projects = {project['id']: project for project in data['value']}
        except requests.exceptions.HTTPError as http_err:
            print(f"\tHTTP error occurred: {http_err}")
        except Exception as err:
            print(f"\tAn error occurred: {err}")
    
        return full_projects

def discover_cross_project_access(project_id, full_project):

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {pat_token}',
    }

    # Get all pipelines in the project
    pipelines_url = f'https://dev.azure.com/{organization}/{project_id}/_apis/pipelines?api-version=7.1'
    response = requests.get(pipelines_url, headers=headers)
    pipelines = response.json().get('value', [])


    project_repo_access = []
    for pipeline in pipelines:
        # Get runs for each pipeline
        runs_url = f'https://dev.azure.com/{organization}/{project_id}/_apis/pipelines/{pipeline["id"]}/runs?api-version=7.1'
        runs_response = requests.get(runs_url, headers=headers)
        runs = runs_response.json().get('value', [])

        for run in runs:

            url = run['_links']['self']['href']

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {pat_token}',
            }
            
            try:
                # Make the GET request 
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                # Parse JSON response
                self_run = response.json()

                if "repositories" in self_run['resources'].keys():
                    for resource in self_run['resources']['repositories'].values():
                        project_repo_access.append({
                            "home_project": full_project['name'],
                            "run": self_run['_links']['web']['href'],
                            "project": resource['repository']['fullName'].split('/')[0],
                            "repo": resource['repository']['fullName'].split('/')[-1],
                            "repo_id": resource['repository']['id'],
                            "branch": resource['refName'],
                            "cross_project": full_project['name'] == resource['repository']['fullName'].split('/')[0],
                            "status": 'REVIEW' if full_project['name'] != resource['repository']['fullName'].split('/')[0] else "OK"
                        })
            
            except requests.exceptions.HTTPError as http_err:
                print(f"\tHTTP error occurred: {http_err}")
            except Exception as err:
                print(f"\tAn error occurred: {err}")

    return project_repo_access

def deduplicate_entries(entries):
    seen = set()
    unique_entries = []

    for entry in entries:
        identifier = (entry['home_project'], entry['project'], entry['repo'], entry['cross_project'], entry['status'])

        if identifier not in seen:
            seen.add(identifier)
            unique_entries.append(entry)

    return unique_entries

def simulate_update_permissions(cross_project_access, projects):
    deduplicated_access = deduplicate_entries(cross_project_access)
    for row in deduplicated_access:
        if row['status'] == "APPROVED":
            for project_id, project_value in projects.items():
                if project_value['name'] == row['project']:
                    project = project_id

            project_permissions_url = f"https://dev.azure.com/{organization}/{project}/_settings/permissions"
            repository_url = f"https://dev.azure.com/{organization}/{project}/_settings/repositories?repo={row['repo_id']}"
            print("\n")
            print(f"1. Ensure the entity '{row['home_project']} Build Service ({organization})' has access to Project '{row['project']}' metadata level information.")
            print(f"   Link: {project_permissions_url}\n")
            print(f"2. Ensure the entity '{row['home_project']} Build Service ({organization})' has read access to the repository '{row['repo']}' in project '{row['project']}'.")
            print(f"   Link: {repository_url}")

    return


def get_args():
    # Argument parser
    parser = argparse.ArgumentParser(description="CLI tool to identify cross project repo access in Azure DevOps.")

    parser.add_argument(
        '--simulate-approve-all', 
        action='store_true',
        help="Simulate actions if you were to approve all cross project access, setting any 'REVIEW' to 'APPROVED' and outputting the steps that need to be taken.", 
    )

    parser.add_argument(
        "--organization",
        type=str,
        help="The organization name"
    )
    
    parser.add_argument(
        "--pat_token",
        type=str,
        help="The personal access token"
    )

    # Parse the arguments from the command line
    return parser.parse_args()

def load_config_from_file(file_path="config.json"):
    # Load configurations from a JSON file
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

# Main execution
if __name__ == "__main__":

    args = get_args()
    config = load_config_from_file("config.json")

    # Use environment variables or fall back to config file values or defaults
    organization = (
        args.organization or 
        os.getenv("ORGANIZATION") or 
        config.get("organization", "default_org")
    )

    pat_token_raw = (
        args.pat_token or 
        os.getenv("PAT_TOKEN") or 
        config.get("pat_token", "default_token")
    )

    pat_token = base64.b64encode(f":{pat_token_raw}".encode()).decode()
    simulate_approve_all = args.simulate_approve_all

    if not organization:
        print(f"Something went wrong - Provide a valid ADO organization via CLI, environment variables or config.JSON. [{organization}]")
        exit()

    display_chicken_art()

    projects = get_projects()
    cross_project_access_list = []

    for project in projects:
        cross_project_access_list.extend(discover_cross_project_access(project, projects[project]))

    directory = f"outputs"
    create_directory_if_not_exists(directory)
    file_name = f"{directory}/cross_access.json"
    with open(file_name, 'w') as file:
        json.dump(cross_project_access_list, file, indent=4)
        file.close()
    
    # Define the CSV file name
    directory = f"outputs"
    create_directory_if_not_exists(directory)
    csv_file = f"{directory}/cross_access.csv"

    if cross_project_access_list:

        with open(csv_file, mode='w', newline='') as file:
            # Create a CSV DictWriter object
            writer = csv.DictWriter(file, fieldnames=cross_project_access_list[0].keys())

            # Write the header (column names)
            writer.writeheader()

            # Write the data rows
            for row in cross_project_access_list:
                writer.writerow(row)
            
            file.close()


        if simulate_approve_all:
            for row in cross_project_access_list:
                if row["status"] == "REVIEW":
                    row["status"] = "APPROVED"

            # UPDATE PERMISSIONS
            simulate_update_permissions(cross_project_access_list, projects)
