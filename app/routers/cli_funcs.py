import os
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database
from models import Module

router = APIRouter()

BASE_DIR = "c_cpp_modules"

@router.get("/get_latest_version/{module_name}")
async def get_latest_version(module_name: str):
    '''
    Returns the latest version of the specified module. If the module is not found, returns an error message. If the versions.json file is missing, returns an error message. If any error occurs during the process, returns an error message.

    Args:
        module_name: The name of the module
    
    Returns:
        latest version: if the module is found and the versions.json file exists
        error message: if the module is not found, the versions.json file is missing, or any error occurs during the process

    Raises:
        json.JSONDecodeError: If an error occurs while decoding the versions.json file
        Exception: If any error occurs
    '''
    versions_file_path = os.path.join(BASE_DIR, module_name, 'versions.json')
    
    # Check if the module directory exists
    if not os.path.exists(os.path.join(BASE_DIR, module_name)):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")

    # Check if the versions.json file exists
    if not os.path.exists(versions_file_path):
        raise HTTPException(status_code=404, detail="The versions.json file is missing for the specified module.")

    try:
        with open(versions_file_path, 'r') as file:
            data = json.load(file)
            return JSONResponse(content={"latest": data.get('latest')})
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the versions.json file.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.get("/get_versions/{module_name}")
async def get_versions(module_name: str):
    '''
    Returns all the versions of the specified module. If the module is not found, returns an error message. If the versions.json file is missing, returns an error message. If any error occurs during the process, returns an error message.

    Args:
        module_name: The name of the module
    
    Returns:
        all versions: if the module is found and the versions.json file exists
        error message: if the module is not found, the versions.json file is missing, or any error occurs during the process

    Raises:
        json.JSONDecodeError: If an error occurs while decoding the versions.json file
        Exception: If any error occurs
    '''
    versions_file_path = os.path.join(BASE_DIR, module_name, 'versions.json')
    latest_version_path = None
    data = None
    module_info = None
    data_to_send = None
    
    # Check if the module directory exists
    if not os.path.exists(os.path.join(BASE_DIR, module_name)):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")

    # Check if the versions.json file exists
    if not os.path.exists(versions_file_path):
        raise HTTPException(status_code=404, detail="The versions.json file is missing for the specified module.")

    try:
        with open(versions_file_path, 'r') as file:
            data = json.load(file)
            latest_version_path = os.path.join(BASE_DIR, data.get('latest_path'),'module_info.json')
            
        with open(latest_version_path, 'r') as file:
            module_info = json.load(file)

        data_to_send = {
            "all_versions": data,
            "author": module_info.get('author'),
            "description": module_info.get('description'),
            "license": module_info.get('license'),
        }
        return JSONResponse(content=data_to_send)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding the versions.json file.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.get("/get_modules")
async def get_module_names(db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    Fetches all the module names from the database and returns them as a list.

    Args:
        db: The database connection object

    Returns:
        module_list: A list of module names

    Raises:
        HTTPException: If there is an error querying the database
    '''
    try:
        modules = await db["modules"].find().to_list(100)
        module_list = [module["module_name"] for module in modules]
        return JSONResponse(content=module_list)
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")