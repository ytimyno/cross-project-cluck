import requests
import json
import config
import os
import base64
import csv
import argparse
from pprint import pprint

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
                            "branch": resource['refName'],
                            "cross_project": full_project['name'] == resource['repository']['fullName'].split('/')[0],
                            "status": 'REVIEW' if full_project['name'] != resource['repository']['fullName'].split('/')[0] else "OK"
                        })
            
            except requests.exceptions.HTTPError as http_err:
                print(f"\tHTTP error occurred: {http_err}")
            except Exception as err:
                print(f"\tAn error occurred: {err}")

    return project_repo_access

def update_permissions(cross_project_access):
    for row in cross_project_access:
        if row['status'] == "APPROVED":
                print("grant access to project & repo")
    return

organization = config.organization
pat_token = base64.b64encode(f":{config.pat_token}".encode()).decode()

# Main execution
if __name__ == "__main__":

    # Argument parser
    parser = argparse.ArgumentParser(description="Process pipelines and manage cross-project repository access.")
    parser.add_argument('--force-approve-all', help='Force approval of all pipeline access requests', default=False, type=bool)
    args = parser.parse_args()
    force_approve_all = args.force_approve_all

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

    # Open the CSV file for writing
    with open(csv_file, mode='w', newline='') as file:
        # Create a CSV DictWriter object
        writer = csv.DictWriter(file, fieldnames=cross_project_access_list[0].keys())

        # Write the header (column names)
        writer.writeheader()

        # Write the data rows
        for row in cross_project_access_list:
            writer.writerow(row)
        
        file.close()



    if force_approve_all:
        for row in cross_project_access_list:
            if row["status"] == "REVIEW":
                row["status"] = "APPROVED"

        # UPDATE PERMISSIONS
        update_permissions(cross_project_access_list)
