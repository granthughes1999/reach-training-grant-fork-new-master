# reach-training (8/1)
Repository to house all required documents to run video acquisition, deeplabcut-enabled network creation, reach finding, and curation.

# General GitHub Commands
* Run git commands in Windows Powershell prompt
* Always navigate to repository directory
## First Time Cloning:
* 1. Go to https://github.com/Cerebellum-Lab/reach-training (must be added by an owner)
* 2. Press green "Code" dropdown and copy HTTPS
	- Can also download zip file and extract into desired directory (skip following)
* 3. Open Windows Powershell prompt
* 4. Navigate to directory where you want the repository to live
** ex. cd Documents
* 5. git clone <copied_HTTPS>

## To Pull (update code):
* 1. git stash save "<message>"
* 2. git pull
	- git stash pop #applys stashed changes back to current repo
	

## To confirm your repository is up to date:
* 1. git fetch
* 2. git status
	- IF "On branch main... Your branch is up to date with 'origin/main'"
	-- you are up-to-date 
	- ELSE IF: "On branch main... Your branch is behind 'origin/main' by X commits, and can be fast-forwarded"
	-- git pull


# Folder Contents
## PythonScripts 
- instructions for operating all GUI's = Script_operating_instructions.txt
- GUI scripts and dependent functions

Run the python scripts via:
1. Command line (command prompt, powershell, conda prompt):
     - FOR CONDA ONLY: Activate environment (conda activate <env_name>)
     - Navigate to folder containing .py script (cd C:\path\to\your\script)
     - python script_file_name.py
2. Spyder:
     - Activate environment (conda activate <env_name>)
     - Open spyder (spyder)
     - Open file within spyder and Run. 

## Arduino-control 
- .ino files used to operate the Arduino devices. 
- instructions for appropriate file selection if reupload is needed.

## Conda-envs
- Anaconda environment configuration files
- instructions for building required anaconda environments

## Examples
- configuration files for dlc project and curator
- example userdata file