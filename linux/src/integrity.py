import hashlib
import os
import sys

def check_integrity(manifest_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.normpath(os.path.join(base_dir, ".."))
    
    actual_manifest = os.path.join(root_dir, manifest_path)

    if not os.path.exists(actual_manifest):
        print(f"[ERROR] Manifest {actual_manifest} not found.")
        sys.exit(1)

    failed = False
    with open(actual_manifest, "r") as f:
        for line in f:
            if not line.strip(): continue
            expected_hash, rel_path = line.split(maxsplit=1)
            rel_path = rel_path.strip().replace("/", os.sep)
            
            full_path = os.path.join(root_dir, rel_path)
            
            if os.path.exists(full_path):
                md5 = hashlib.md5()
                with open(full_path, "rb") as f_bin:
                    while chunk := f_bin.read(4096):
                        md5.update(chunk)
                
                if md5.hexdigest() != expected_hash:
                    print(f"[FAIL] {rel_path}")
                    failed = True
                else:
                    print(f"[PASS] {rel_path}")
            else:
                print(f"[MISSING] {rel_path}")
                failed = True
    
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    check_integrity(os.path.join("src", "data", "manifest.md5"))