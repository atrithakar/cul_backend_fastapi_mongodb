import os
import shutil
import json
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database, get_next_sequence_value
from models import User, Module
from rapidfuzz import process

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

BASE_DIR = "c_cpp_modules"

def handle_remove_readonly(func, path, exc_info):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/", response_class=HTMLResponse)
async def login_webui(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    user = await db["users"].find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid email or password"})
    
    request.session["email"] = email
    return RedirectResponse(url="/main_page", status_code=303)

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup", response_class=HTMLResponse)
async def signup_user_webui(request: Request, email: str = Form(...), password: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), username: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
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
    profile = await db["users"].find_one({"email": request.session.get("email")})
    if not check_password_hash(profile["password"], old_password):
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Old password is incorrect", "profile": profile})
    
    new_hashed_password = generate_password_hash(new_password)
    await db["users"].update_one({"email": request.session.get("email")}, {"$set": {"password": new_hashed_password}})
    return templates.TemplateResponse("profile.html", {"request": request, "success": "Password changed successfully", "profile": profile})

@router.get("/main_page", response_class=HTMLResponse)
async def main_page_webui(request: Request):
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("main_page.html", {"request": request})

@router.post("/main_page", response_class=HTMLResponse)
async def main_page_search(request: Request, module_name: str = Form(...)):
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
    return templates.TemplateResponse("upload_modules.html", {"request": request})

@router.post("/upload_modules", response_class=HTMLResponse)
async def upload_modules_webui(request: Request, github_repo_link: str = Form(...), db: AsyncIOMotorDatabase = Depends(get_database)):
    module_name = github_repo_link.split('/')[-1]
    module = await db["modules"].find_one({"module_name": module_name})
    if module:
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": "Module already exists"})
    
    cloned_status = os.system(f"git clone {github_repo_link} {os.path.join(BASE_DIR, module_name)}")
    if cloned_status != 0:
        return templates.TemplateResponse("upload_modules.html", {"request": request, "error": "Error cloning the repository"})
    
    module_id = await get_next_sequence_value("module_id")
    module = {"module_id": module_id, "module_name": module_name, "module_url": github_repo_link, "associated_user": request.session.get("email")}
    await db["modules"].insert_one(module)
    return RedirectResponse(url="/main_page", status_code=303)

@router.get("/delete_module/{module_id}", response_class=HTMLResponse)
async def delete_module_webui(request: Request, module_id: int, db: AsyncIOMotorDatabase = Depends(get_database)):
    module = await db["modules"].find_one({"module_id": module_id})
    if not module:
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Module not found"})
    
    module_path = os.path.join(BASE_DIR, module['module_name'])
    if os.path.exists(module_path):
        shutil.rmtree(module_path, onerror=handle_remove_readonly)
        delete_result = await db["modules"].delete_one({"module_id": module_id})
        print(f"Deleted {delete_result.deleted_count} document")
    
    profile = await db["users"].find_one({"email": request.session.get("email")})
    modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})

@router.get("/update_module/{module_id}", response_class=HTMLResponse)
async def update_module_webui(request: Request, module_id: int, db: AsyncIOMotorDatabase = Depends(get_database)):
    module = await db["modules"].find_one({"module_id": module_id})
    if not module:
        return templates.TemplateResponse("profile.html", {"request": request, "error": "Module not found"})
    
    os.system(f"cd {os.path.join(BASE_DIR, module['module_name'])} && git pull")
    
    profile = await db["users"].find_one({"email": request.session.get("email")})
    modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})

@router.get("/info/{module}/{version}", response_class=HTMLResponse)
async def get_module_info_webui(request: Request, module: str, version: str):
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
    if request.session.get("email"):
        profile = await db["users"].find_one({"email": request.session.get("email")})
        modules = await db["modules"].find({"associated_user": request.session.get("email")}).to_list(100)
        return templates.TemplateResponse("profile.html", {"request": request, "profile": profile, "modules": modules})
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    request.session.pop("email", None)
    return RedirectResponse(url="/")