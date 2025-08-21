import os
import shutil
import json
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from secrets import token_hex
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database, get_next_sequence_value
from models import User, Module
from rapidfuzz import process
from .checksum_utils import generate_module_checksum, generate_checksums_for_new_versions
from .normalize_line_endings import normalize_line_endings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BASE_DIR = "c_cpp_modules"

temp_link_code_map = {}

def handle_remove_readonly(func, path, exc_info):
    '''
    This function removes the read-only attribute from a file or directory and then calls the provided function.

    Args:
        func (function): The function to call.
        path (str): The path to the file or directory.
        exc_info (tuple): The exception information.

    Returns:
        None

    Raises:
        None
    '''
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    '''
    This function serves the login page.

    Args:
        request (Request): The request object.

    Returns:
        HTMLResponse: The HTML response containing the login page.

    Raises:
        None
    '''
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
async def login_webui(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function logs in a user and sets the session email.

    Args:
        request (Request): The request object.
        email (str): The email of the user.
        password (str): The password of the user.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the login page with an error message if the login fails.
        RedirectResponse: The redirect response to the main page if the login is successful.

    Raises:
        None
    '''
    user = await db["users"].find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid email or password"})
    
    request.session["email"] = email
    return RedirectResponse(url="/main_page", status_code=303)


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    '''
    This function serves the signup page.

    Args:
        request (Request): The request object.

    Returns:
        HTMLResponse: The HTML response containing the signup page.

    Raises:
        None
    '''
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup", response_class=HTMLResponse)
async def signup_user_webui(request: Request, email: str = Form(...), password: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), username: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function signs up a user and inserts the user into the database if the username or the email does not already exist.

    Args:
        request (Request): The request object.
        email (str): The email of the user.
        password (str): The password of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        username (str): The username of the user.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the signup page with an error message if the user already exists.
        RedirectResponse: The redirect response to the login page if the signup is successful.

    Raises:
        None
    '''
    user_exists = await db["users"].find_one({"email": email})
    if user_exists:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "User already exists"})
    
    user_name_exists = await db["users"].find_one({"username": username})
    if user_name_exists:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already exists, pick a different username."})

    hashed_password = generate_password_hash(password)
    user = {"email": email, "password": hashed_password, "first_name": first_name, "last_name": last_name, "username": username}
    await db["users"].insert_one(user)
    return RedirectResponse(url="/", status_code=303)


@router.post("/change_password", response_class=HTMLResponse)
async def change_password_webui(request: Request, old_password: str = Form(...), new_password: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function changes the password of the user by validating the old password and updating the new password in the database.
    If a user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.
        old_password (str): The old password of the user.
        new_password (str): The new password of the user.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the profile page with an error message if the old password is incorrect.
        HTMLResponse: The HTML response containing the profile page with a success message if the password is changed successfully.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    profile = await db["users"].find_one({"email": request.session.get("email")})
    
    if request.session.get("email") != profile.get("email"):
        return templates.TemplateResponse("index.html", {"request": request, "error": "You are not authorized to change the password"})

    if not check_password_hash(profile["password"], old_password):
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Old password is incorrect", "profile": profile})
    
    new_hashed_password = generate_password_hash(new_password)
    await db["users"].update_one({"email": request.session.get("email")}, {"$set": {"password": new_hashed_password}})
    return templates.TemplateResponse("profile.html", {"request": request, "success": "Password changed successfully", "profile": profile})


@router.get("/main_page", response_class=HTMLResponse)
async def main_page_webui(request: Request):
    '''
    This function serves the main page if the user is logged in else redirects to the login page.
    if the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.

    Returns:
        HTMLResponse: The HTML response containing the main page if the user is logged in.
        RedirectResponse: The redirect response to the login page if the user is not logged in.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("main_page.html", {"request": request})


@router.post("/main_page", response_class=HTMLResponse)
async def main_page_search(request: Request, module_name: str = Form(...)):
    '''
    This function searches for the module name in the BASE_DIR and returns the versions of the modules if found.
    if the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.
        module_name (str): The name of the module to search for.

    Returns:
        HTMLResponse: The HTML response containing the main page with the module versions if found.
        HTMLResponse: The HTML response containing the main page with an error message if no matching modules are found.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)
    
    available_modules = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    all_matches = process.extract(module_name, available_modules, limit=None)
    matched_modules = [match[0] for match in all_matches if match[1] > 70]
    
    module_versions_dict = {}
    error = None

    if matched_modules:
        for module_name in matched_modules:
            versions_json = os.path.join(BASE_DIR, module_name, 'versions.json')
            if os.path.exists(versions_json):
                with open(versions_json, 'r') as file:
                    module_versions = json.load(file)
                    module_versions_dict[module_name] = [item['version'] for item in module_versions.get('versions', [])]
            else:
                error = "Some modules were found, but versions could not be loaded."
        return templates.TemplateResponse("main_page.html", {"request": request, "module_versions": module_versions_dict, "error": error})
    else:
        error = "No matching modules found."
        return templates.TemplateResponse("main_page.html", {"request": request, "error": error})


@router.get("/upload_modules", response_class=HTMLResponse)
async def upload_modules_page(request: Request):
    '''
    This function serves the "upload modules" page.
    If the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.

    Returns:
        HTMLResponse: The HTML response containing the "upload modules" page.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("upload_modules.html", {"request": request})


@router.post("/generate_code")
async def generate_code(data: dict):
    '''
    This function generates a temporary verification code for the provided GitHub repository link.

    Args:
        data (dict): A dictionary containing the GitHub repository link.

    Returns:
        JSONResponse: A JSON response containing the generated verification code if the link is valid.
        JSONResponse: A JSON response with an error message if the link is invalid.

    Raises:
        None
    '''
    github_repo_link = data.get("github_repo_link")
    if not github_repo_link or not github_repo_link.startswith("https://github.com/"):
        return JSONResponse(status_code=400, content={"error": "Invalid GitHub link"})
    
    code = token_hex(32)  # 256-bit hex string
    temp_link_code_map[github_repo_link] = code
    return {"generated_code": code}

@router.post("/upload_modules", response_class=HTMLResponse)
async def upload_modules_webui(request: Request, github_repo_link: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function handles the upload of a CUL module via the Web UI. It verifies that the user is logged in, ensures the module does not already exist,
    and validates ownership of the GitHub repository through a temporary verification code mechanism.

    - Verifies session, checks for duplicate module, and ensures a verification code was generated.
    - Clones the GitHub repo and confirms presence of `versions.json` and `cul_verify.txt`.
    - Validates the code in `cul_verify.txt` against the generated one.
    - Generates checksum, inserts module into DB, and cleans up on failure.

    Args:
        request (Request): The HTTP request object containing user session data.
        github_repo_link (str): The GitHub repository link provided by the user.
        db (AsyncIOMotorDatabase): The MongoDB database object used for inserting module data.

    Returns:
        HTMLResponse: Rendered upload page with an error message if verification fails or module already exists.
        RedirectResponse: Redirect to the main page upon successful module upload.

    Raises:
        Exception: If any of the required files are missing, verification code does not match, or cloning fails.
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    module_name = github_repo_link.split('/')[-1]
    module_folder = os.path.join(BASE_DIR, module_name)

    if await db["modules"].find_one({"module_name": module_name}):
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": "Module already exists"})

    if github_repo_link not in temp_link_code_map:
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": "Repository verification code not generated for this link"})

    expected_code = temp_link_code_map[github_repo_link]

    cloned_status = os.system(f"git clone {github_repo_link} {module_folder}")
    if cloned_status != 0:
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": "Error cloning the repository"})
    
    # Normalize line endings in the cloned files
    for root, dirs, files in os.walk(module_folder):
        for file in files:
            file_path = os.path.join(root, file)
            normalize_line_endings(file_path)

    try:
        if not os.path.exists(os.path.join(module_folder, "versions.json")):
            raise Exception("versions.json not found")

        verify_path = os.path.join(module_folder, "cul_verify.txt")
        if not os.path.exists(verify_path):
            raise Exception("cul_verify.txt not found")

        with open(verify_path, "r") as f:
            user_code = f.read().strip()

        if user_code != expected_code:
            raise Exception("Verification code mismatch")

        hash_success_status = generate_module_checksum(module_folder)
        if not hash_success_status:
            raise Exception("Error generating checksum")

        module_id = await get_next_sequence_value("module_id")
        module_doc = {
            "module_id": module_id,
            "module_name": module_name,
            "module_url": github_repo_link,
            "associated_user": request.session.get("email")
        }
        await db["modules"].insert_one(module_doc)

        del temp_link_code_map[github_repo_link]

        return RedirectResponse(url="/main_page", status_code=303)

    except Exception as e:
        shutil.rmtree(module_folder, onexc=handle_remove_readonly)
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": str(e)})


@router.get("/delete_module/{module_id}", response_class=HTMLResponse)
async def delete_module_webui(request: Request, module_id: int, db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function deletes the module from the database and the filesystem of the server.
    If the user is not logged in, it redirects to the login page.
    If the email of the current user does not match the associated_user of the module, it returns an error message.

    Args:
        request (Request): The request object.
        module_id (int): The module_id of the module to delete.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the profile page with an error message if the module is not found.
        HTMLResponse: The HTML response containing the profile page with the modules if the module is deleted successfully.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    module = await db["modules"].find_one({"module_id": module_id})

    if not module:
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Module not found"})

    if request.session.get("email") != module.get("associated_user"):
        return templates.TemplateResponse("index.html", {"request": request, "error": "You are not authorized to delete this module"})
    
    module_path = os.path.join(BASE_DIR, module['module_name'])
    if os.path.exists(module_path):
        shutil.rmtree(module_path, onexc=handle_remove_readonly)
        delete_result = await db["modules"].delete_one({"module_id": module_id})
        print(f"Deleted {delete_result.deleted_count} document")
    
    profile = await db["users"].find_one({"email": request.session.get("email")})
    modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})


@router.get("/update_module/{module_id}", response_class=HTMLResponse)
async def update_module_webui(request: Request, module_id: int, db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function updates the module by pulling the latest changes from the github repository.
    If the user is not logged in, it redirects to the login page.
    If the email of the current user does not match the associated_user of the module, it returns an error message.

    Args:
        request (Request): The request object.
        module_id (int): The module_id of the module to update.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the profile page with an error message if the module is not found.
        HTMLResponse: The HTML response containing the profile page with the modules if the module is updated successfully.

    Raises:
        None
    '''

    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    module = await db["modules"].find_one({"module_id": module_id})

    if request.session.get("email") != module.get("associated_user"):
        return templates.TemplateResponse("index.html", {"request": request, "error": "You are not authorized to update this module"})
    
    if not module:
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Module not found"})
    
    os.system(f"cd {os.path.join(BASE_DIR, module['module_name'])} && git pull")
    module_path = os.path.join(BASE_DIR, module['module_name'])
    generate_checksums_for_new_versions(module_path)
    
    profile = await db["users"].find_one({"email": request.session.get("email")})
    modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})


@router.get("/info/{module}/{version}", response_class=HTMLResponse)
async def get_module_info_webui(request: Request, module: str, version: str):
    '''
    This function serves the module information page where it displays various module information like author, description, license, and dependencies.
    If the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.
        module (str): The name of the module.
        version (str): The version of the module.

    Returns:
        HTMLResponse: The HTML response containing the module information page.
        HTMLResponse: The HTML response containing an error message if the module/version is not found.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    module_info_file_path = os.path.join(BASE_DIR, module, version, 'module_info.json')
    if not os.path.exists(module_info_file_path):
        return HTMLResponse(content="<h1>Error 404: Module/Version not found.</h1>", status_code=404)
    
    with open(module_info_file_path, 'r') as file:
        module_info = json.load(file)
    
    deps = module_info.get('requires', [])
    data = {
        "ModuleName": module,
        "Version": version,
        "Author": module_info.get('author'),
        "Description": module_info.get('description'),
        "License": module_info.get('license'),
        "Dependencies": {dep.split('==')[0]: dep.split('==')[1] for dep in deps} if deps else None,
    }
    return templates.TemplateResponse("version_info.html", {"request": request, "data": data})


@router.get("/profile", response_class=HTMLResponse)
async def get_profile_webui(request: Request, db: AsyncIOMotorDatabase = Depends(get_database)):
    '''
    This function serves the profile page of the user if the user is logged in else redirects to the login page.
    If the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.
        db (AsyncIOMotorDatabase): The database object.

    Returns:
        HTMLResponse: The HTML response containing the profile page if the user is logged in.
        RedirectResponse: The redirect response to the login page if the user is not logged in.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    profile = await db["users"].find_one({"email": request.session.get("email")})
    modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})


@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    '''
    This function logs out the user by popping the email from the session.
    If the user is not logged in, it redirects to the login page.

    Args:
        request (Request): The request object.

    Returns:
        RedirectResponse: The redirect response to the login page.

    Raises:
        None
    '''
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    request.session.pop("email", None)
    return RedirectResponse(url="/")