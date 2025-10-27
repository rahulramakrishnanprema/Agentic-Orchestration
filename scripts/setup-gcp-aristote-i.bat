@echo off
REM GCP Setup Script for Aristote-I Project (Windows)
REM Run this script to set up your GCP environment automatically

setlocal enabledelayedexpansion

REM Configuration
set PROJECT_ID=aristote-i
set PROJECT_NAME=Aristote-I
set REGION=us-central1
set SERVICE_ACCOUNT_NAME=gitlab-deployer
set REPOSITORY_NAME=aristotlei

echo ================================================================
echo      Aristote-I GCP Setup Script (Windows)
echo ================================================================
echo.
echo Project ID: %PROJECT_ID%
echo Project Name: %PROJECT_NAME%
echo Region: %REGION%
echo.

REM Check if gcloud is installed
where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI not found. Please install it first.
    echo Visit: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)
echo [OK] gcloud CLI found

REM Login check
echo Checking authentication...
gcloud auth list --filter=status:ACTIVE --format="value(account)" >nul 2>&1
if %errorlevel% neq 0 (
    echo Please login to gcloud...
    gcloud auth login
)
echo [OK] Authenticated

REM Create project
echo Creating GCP project: %PROJECT_ID%...
gcloud projects describe %PROJECT_ID% >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Project already exists: %PROJECT_ID%
) else (
    gcloud projects create %PROJECT_ID% --name="%PROJECT_NAME%"
    echo [OK] Project created: %PROJECT_ID%
)

REM Set project
gcloud config set project %PROJECT_ID%
echo [OK] Project set to: %PROJECT_ID%

REM Note about billing
echo.
echo NOTE: Make sure billing is enabled for this project
echo Visit: https://console.cloud.google.com/billing/linkedaccount?project=%PROJECT_ID%
echo Press any key to continue...
pause >nul

REM Enable APIs
echo Enabling required APIs...
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable compute.googleapis.com
echo [OK] APIs enabled

REM Create service account
echo Creating service account...
gcloud iam service-accounts describe %SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Service account already exists
) else (
    gcloud iam service-accounts create %SERVICE_ACCOUNT_NAME% --description="GitLab CI/CD Deployer" --display-name="GitLab Deployer"
    echo [OK] Service account created
)

REM Grant permissions
echo Granting permissions to service account...
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com" --role="roles/run.admin" --quiet
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com" --role="roles/artifactregistry.admin" --quiet
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser" --quiet
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com" --role="roles/storage.admin" --quiet
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com" --role="roles/cloudbuild.builds.editor" --quiet
echo [OK] Permissions granted

REM Create service account key
echo Creating service account key...
set KEY_FILE=gitlab-deployer-key.json
gcloud iam service-accounts keys create %KEY_FILE% --iam-account=%SERVICE_ACCOUNT_NAME%@%PROJECT_ID%.iam.gserviceaccount.com
echo [OK] Service account key created: %KEY_FILE%

REM Create Artifact Registry repository
echo Creating Artifact Registry repository...
gcloud artifacts repositories describe %REPOSITORY_NAME% --location=%REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Repository already exists
) else (
    gcloud artifacts repositories create %REPOSITORY_NAME% --repository-format=docker --location=%REGION% --description="Aristotle-I Docker Images"
    echo [OK] Repository created
)

echo.
echo ================================================================
echo      Setup Complete! [OK]
echo ================================================================
echo.
echo Next Steps:
echo.
echo 1. Copy the service account key to GitLab:
echo    File: %KEY_FILE%
echo    Location: %CD%\%KEY_FILE%
echo.
echo 2. Add to GitLab CI/CD Variables:
echo    Settings -^> CI/CD -^> Variables -^> Add variable
echo.
echo    Variable 1:
echo    Key:   GCP_PROJECT_ID
echo    Value: %PROJECT_ID%
echo.
echo    Variable 2:
echo    Key:   GCP_REGION
echo    Value: %REGION%
echo.
echo    Variable 3:
echo    Key:   GCP_SERVICE_ACCOUNT_KEY
echo    Value: ^<paste entire content of %KEY_FILE%^>
echo.
echo 3. View the service account key:
echo    type %KEY_FILE%
echo.
echo 4. Open the key file to copy:
echo    notepad %KEY_FILE%
echo.
echo 5. Push to GitLab and watch the pipeline run!
echo.
echo Useful Links:
echo    GCP Console: https://console.cloud.google.com/home/dashboard?project=%PROJECT_ID%
echo    Cloud Run: https://console.cloud.google.com/run?project=%PROJECT_ID%
echo    Artifact Registry: https://console.cloud.google.com/artifacts?project=%PROJECT_ID%
echo.
echo IMPORTANT: Keep %KEY_FILE% secure! Add it to .gitignore
echo.
echo Press any key to open the key file in Notepad...
pause >nul
notepad %KEY_FILE%

endlocal

