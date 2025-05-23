import hashlib
import os
import json

def generate_checksum(module_path: str) -> str:
    '''
    Generates a SHA-256 checksum for all files in the specified folder and its subfolders (excluding .git).
    The checksum is based on the relative paths and contents of the files.

    Args:
        module_path (str): The path to the folder to be hashed.

    Returns:
        str: The SHA-256 checksum as a hexadecimal string.

    Raises:
        None
    '''
    sha256_hash = hashlib.sha256()
    file_count = 0

    for root, dirs, files in os.walk(module_path):
        dirs[:] = [d for d in dirs if d != '.git']
        files.sort()

        for filename in files:
            if filename == "checksum.txt":
                continue

            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, module_path)
            sha256_hash.update(relative_path.encode())

            try:
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        sha256_hash.update(chunk)
                file_count += 1
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    if file_count == 0:
        print(f"No files to hash in {module_path}. Skipping.")
        return None

    return sha256_hash.hexdigest()


def generate_checksums_for_new_versions(module_path: str):
    for version_folder in sorted(os.listdir(module_path)):
        version_path = os.path.join(module_path, version_folder)

        if not os.path.isdir(version_path):
            continue

        if version_folder == '.git':
            continue

        checksum_file = os.path.join(version_path, "checksum.txt")
        if os.path.exists(checksum_file):
            print(f"Skipping {version_folder} (already has checksum.txt)")
            continue

        print(f"Hashing new version: {version_folder}")
        checksum = generate_checksum(version_path)
        if checksum:
            with open(checksum_file, "w") as f:
                f.write(checksum)
            print(f"Checksum for {version_folder}: {checksum}")
        else:
            print(f"No files hashed for {version_folder}, checksum not written.")


def store_checksum(module_path: str) -> None:
    '''
    Stores the generated checksum in a file named "checksum.txt" in the specified folder.

    Args:
        module_path (str): The path to the folder where the checksum will be stored.

    Returns:
        None

    Raises:
        None
    '''

    if not os.path.exists(module_path):
        print(f"Error: The folder {module_path} does not exist.")
        return

    checksum = generate_checksum(module_path)
    
    if not checksum:
        print("No checksum generated.")
        return

    with open(os.path.join(module_path, "checksum.txt"), "w") as f:
        f.write(checksum)


def generate_module_checksum(module_path: str) -> int:
    '''
    Iterates through all versions of a module and generates checksums for each version folder.

    Args:
        module_path (str): The path to the module folder containing version subfolders.

    Returns:
        int: 1 if checksums were generated successfully, 0 otherwise.

    Raises:
        None
    '''
    version_json_path = os.path.join(module_path, "versions.json")

    if not os.path.exists(version_json_path):
        print(f"Error: The file {version_json_path} does not exist.")
        return 0

    with open(version_json_path, "r") as f:
        file_content = json.load(f)

    version_list = [entry["version"] for entry in file_content["versions"]]
    # print(f"Versions: {version_list}")
    for version in version_list:
        version_folder = os.path.join(module_path, version)
        store_checksum(version_folder)

    return 1

if __name__ == "__main__":
    folder_to_hash = ".\\c_cpp_modules\\test_module_6"
    # checksum = generate_checksum(folder_to_hash)
    # print(f"Checksum: {checksum}")
    # store_checksum(folder_to_hash)
    generate_module_checksum(folder_to_hash)
    # generate_checksums_for_new_versions(folder_to_hash)



