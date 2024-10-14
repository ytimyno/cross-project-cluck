import http.client
from urllib.parse import urlparse
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
        
    conn = http.client.HTTPSConnection("dev.azure.com")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {pat_token}',
    }

    full_projects={}

    try:
        conn.request("GET", f"/{organization}/_apis/{api_endpoint}{api_version}", headers=headers)
        res = conn.getresponse()
        response = res.read()

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON Decode Error: {e}")

        # Write output to a file named according to the resource type
        directory = f"outputs"
        create_directory_if_not_exists(directory)
        file_name = f"{directory}/projects.json"
        with open(file_name, 'w') as file:
            json.dump(data, file, indent=4)

        # Extract the mapping of project ID to project name
        full_projects = {project['id']: project for project in data['value']}

    except Exception as e:
        print(f"An error occurred: {e}")

    return full_projects

def discover_cross_project_access(project_id, full_project):

    conn = http.client.HTTPSConnection("dev.azure.com")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {pat_token}',
    }

    project_repo_access = []

    try:
        conn.request("GET", f"/{organization}/{project_id}/_apis/pipelines?api-version=7.1", headers=headers)
        res = conn.getresponse()
        response = res.read()

        # Parse JSON response
        try:
            pipelines = json.loads(response).get('value', [])
        except json.JSONDecodeError as e:
            raise Exception(f"JSON Decode Error: {e}")
        

        for pipeline in pipelines:
            # Get runs for each pipeline
            try:
                conn.request("GET", f"/{organization}/{project_id}/_apis/pipelines/{pipeline['id']}/runs?api-version=7.1", headers=headers)
                res = conn.getresponse()
                response = res.read()
                # Parse JSON response
                try:
                    runs = json.loads(response).get('value', [])
                except json.JSONDecodeError as e:
                    raise Exception(f"JSON Decode Error: {e}")

                # Get self run for each run
                for run in runs:

                    url = run['_links']['self']['href']
                    parsed_url = urlparse(url)

                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Basic {pat_token}',
                    }
                    
                    try:
                        conn.request("GET", parsed_url.path, headers=headers)
                        res = conn.getresponse()
                        response = res.read()

                        # Parse JSON response
                        try:
                            self_run = json.loads(response)
                        except json.JSONDecodeError as e:
                            raise Exception(f"JSON Decode Error: {e}")

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

                    except Exception as e:
                        print(f"An error occurred: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

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

    instructions = [] 
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

            instruction = {
                "project_level": {
                    "instruction": f"1. Ensure the entity '{row['home_project']} Build Service ({organization})' has access to Project '{row['project']}' metadata level information.",
                    "link": project_permissions_url
                },
                "repo_level": {
                    "instruction": f"2. Ensure the entity '{row['home_project']} Build Service ({organization})' has read access to the repository '{row['repo']}' in project '{row['project']}'.",
                    "link": repository_url
                }
            }
            instructions.append(instruction)

    return instructions


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
            instructions = simulate_update_permissions(cross_project_access_list, projects)
            directory = f"outputs"
            create_directory_if_not_exists(directory)
            file_name = f"{directory}/instructions.json"
            with open(file_name, 'w') as file:
                json.dump(instructions, file, indent=4)
                file.close()
