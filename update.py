#!/usr/bin/env python3
import os
import io
import gzip
import bz2
import hashlib
import tarfile

REPO_NAME = "некромантия ios 5"
REPO_DESCRIPTION = "Cydia repository for iOS 5 (некромантия ios 5)"

def get_hashes_and_size(filepath):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    size = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            size += len(chunk)
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()

def extract_control_info(deb_path):
    with open(deb_path, 'rb') as f:
        magic = f.read(8)
        if magic != b'!<arch>\n':
            raise ValueError(f"File {deb_path} is not a valid deb (ar) archive")
        
        while True:
            header = f.read(60)
            if len(header) < 60:
                break
            
            # Parse ar header fields
            name = header[0:16].decode('ascii', errors='ignore').strip()
            name = name.rstrip('/')
            
            size_str = header[48:58].decode('ascii', errors='ignore').strip()
            if not size_str:
                break
            size = int(size_str)
            
            # Read file data
            data = f.read(size)
            if size % 2 == 1:
                f.read(1) # pad byte
                
            if name.startswith('control.tar'):
                # Extract control file from tarball
                tar_data = io.BytesIO(data)
                # Auto-detect compression (.tar, .tar.gz, .tar.xz, .tar.bz2, .tar.zst etc)
                with tarfile.open(fileobj=tar_data, mode='r:*') as tar:
                    for member in tar.getmembers():
                        if member.name in ('control', './control'):
                            control_file = tar.extractfile(member)
                            if control_file:
                                return control_file.read().decode('utf-8', errors='ignore')
    return None

def main():
    # Change working directory to the folder containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    debs_dir = 'debs'
    if not os.path.exists(debs_dir):
        os.makedirs(debs_dir)
        print(f"Created '{debs_dir}' folder. Place your .deb packages here.")
        
    deb_files = [f for f in os.listdir(debs_dir) if f.endswith('.deb')]
    if not deb_files:
        print("No .deb packages found in 'debs/' folder.")
        # We will create empty index files or write placeholders
    
    packages_entries = []
    for deb_file in sorted(deb_files):
        deb_path = os.path.join(debs_dir, deb_file)
        try:
            print(f"Processing {deb_file}...")
            control_content = extract_control_info(deb_path)
            if not control_content:
                print(f"Warning: 'control' file not found in {deb_file}. Skipping.")
                continue
            
            # Format and clean control block
            lines = [line.rstrip() for line in control_content.splitlines() if line.strip()]
            
            # Compute file properties
            size, md5, sha1, sha256 = get_hashes_and_size(deb_path)
            
            # Add relative filename and hashes
            lines.append(f"Filename: debs/{deb_file}")
            lines.append(f"Size: {size}")
            lines.append(f"MD5sum: {md5}")
            lines.append(f"SHA1: {sha1}")
            lines.append(f"SHA256: {sha256}")
            
            packages_entries.append("\n".join(lines))
        except Exception as e:
            print(f"Error processing {deb_file}: {e}")
            
    # Write Packages index
    packages_content = "\n\n".join(packages_entries)
    if packages_entries:
        packages_content += "\n" # Add trailing newline
        
    with open('Packages', 'w', encoding='utf-8') as f:
        f.write(packages_content)
    print("Generated 'Packages'")
    
    # Write Packages.gz
    with gzip.open('Packages.gz', 'wb') as f:
        f.write(packages_content.encode('utf-8'))
    print("Generated 'Packages.gz'")
    
    # Write Packages.bz2
    with bz2.open('Packages.bz2', 'wb') as f:
        f.write(packages_content.encode('utf-8'))
    print("Generated 'Packages.bz2'")
    
    # Calculate hashes for index files to write in Release
    index_files = ['Packages', 'Packages.gz', 'Packages.bz2']
    file_hashes = {}
    for filename in index_files:
        if os.path.exists(filename):
            size, md5, sha1, sha256 = get_hashes_and_size(filename)
            file_hashes[filename] = {
                'size': size,
                'md5': md5,
                'sha1': sha1,
                'sha256': sha256
            }
            
    # Generate Release file
    release_lines = [
        f"Origin: {REPO_NAME}",
        f"Label: {REPO_NAME}",
        "Suite: stable",
        "Version: 1.0",
        "Codename: ios5",
        "Architectures: iphoneos-arm",
        "Components: main",
        f"Description: {REPO_DESCRIPTION}",
    ]
    
    # MD5Sum section
    release_lines.append("MD5Sum:")
    for filename in index_files:
        if filename in file_hashes:
            h = file_hashes[filename]
            release_lines.append(f" {h['md5']} {h['size']} {filename}")
            
    # SHA1 section
    release_lines.append("SHA1:")
    for filename in index_files:
        if filename in file_hashes:
            h = file_hashes[filename]
            release_lines.append(f" {h['sha1']} {h['size']} {filename}")
            
    # SHA256 section
    release_lines.append("SHA256:")
    for filename in index_files:
        if filename in file_hashes:
            h = file_hashes[filename]
            release_lines.append(f" {h['sha256']} {h['size']} {filename}")
            
    # Add trailing newline
    release_content = "\n".join(release_lines) + "\n"
    
    with open('Release', 'w', encoding='utf-8') as f:
        f.write(release_content)
    print("Generated 'Release'")
    print("Cydia repository index update complete!")

if __name__ == '__main__':
    main()
