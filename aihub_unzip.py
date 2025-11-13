import zipfile
import os
from pathlib import Path


zip_path = "./181.실내_자율주차용_데이터"
zip_dir = Path(zip_path)  # 최상위 폴더 경로

unzip_path = zip_path + "_unzip"
unzip_dir = Path(unzip_path)

os.makedirs(unzip_dir, exist_ok=True)

for zip_path in zip_dir.rglob("*.zip"):
    relative_path = zip_path.relative_to(zip_dir).with_suffix('')
    extract_path = unzip_path / relative_path
    os.makedirs(extract_path, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print(f"{zip_path} → {extract_path} 해제 완료")

print("zip 완료")
