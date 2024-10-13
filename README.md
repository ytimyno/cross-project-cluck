# cross-project-cluck
A few lines of code to help identifyin cross project repo access.

```
python cross_project_cluck.py --force-approve-all True
python cross_project_cluck.py
```

Code uses the usual config.py to get the ORG and PAT token. You don't need a full access PAT token for this one.


For each pipeline run harvested (API limited to latest 1000), it adds a row for each repository accessed. Determines if the access is cross-project. Sets the status to "REVIEW" for cross-project access or "OK" for same-project access.

It outputs a JSON and a CSV.