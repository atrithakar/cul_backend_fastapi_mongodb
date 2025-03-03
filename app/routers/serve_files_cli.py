import os
import json
import io
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

BASE_DIR = 'c_cpp_modules'

@router.get("/files/{module_name}")
async def serve_latest_version(module_name: str):
    '''
    This function serves the latest version of the specified module.

    Args:
        module_name (str): The name of the module.

    Returns:
        StreamingResponse: A StreamingResponse object containing the zipped module files.

    Raises:
        HTTPException: If the module directory does not exist.
        json.JSONDecodeError: If there is an error decoding the versions.json file.
        Exception: If an error occurs while serving the files.
    '''
    versions_file_path = os.path.join(BASE_DIR, module_name, 'versions.json')
    
    if not os.path.exists(os.path.join(BASE_DIR, module_name)):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")

    if not os.path.exists(versions_file_path):
        raise HTTPException(status_code=404, detail="The versions.json file is missing for the specified module.")

    try:
        with open(versions_file_path, 'r') as file:
            data = json.load(file)
            latest_path = data.get('latest_path')
            version = data.get('latest')

            if latest_path:
                module_dir = os.path.join(BASE_DIR, latest_path)

                if not os.path.exists(module_dir):
                    raise HTTPException(status_code=404, detail=f"The latest module path '{latest_path}' does not exist.")

                zip_stream = io.BytesIO()
                with zipfile.ZipFile(zip_stream, 'w') as zipf:
                    for root, dirs, files in os.walk(module_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, module_dir))

                zip_stream.seek(0)
                return StreamingResponse(zip_stream, media_type="application/zip", headers={
                    "Content-Disposition": f"attachment; filename={module_name}_{version}.zip"
                })
            else:
                raise HTTPException(status_code=500, detail="The 'latest_path' key is missing in the versions.json file.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the versions.json file.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred.")


@router.get("/files/{module_name}/{version}")
async def serve_specified_version(module_name: str, version: str):
    '''
    This function serves the specified version of the specified module.

    Args:
        module_name (str): The name of the module.
        version (str): The version of the module.

    Returns:
        StreamingResponse: A StreamingResponse object containing the zipped module files.

    Raises:
        HTTPException: If the module directory does not exist.
        Exception: If an error occurs while serving the files.
    '''
    module_dir = os.path.join(BASE_DIR, module_name, version)
    module_dir_wo_version = os.path.join(BASE_DIR, module_name)
    
    if not os.path.exists(module_dir_wo_version):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")
    
    if not os.path.exists(module_dir):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' with version {version} not found.")

    try:
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w') as zipf:
            for root, dirs, files in os.walk(module_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, module_dir))
        
        zip_stream.seek(0)
        return StreamingResponse(zip_stream, media_type="application/zip", headers={
            "Content-Disposition": f"attachment; filename={module_name}_{version}.zip"
        })
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error occurred while serving files.")