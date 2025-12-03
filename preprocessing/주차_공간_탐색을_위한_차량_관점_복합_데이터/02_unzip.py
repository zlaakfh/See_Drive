import zipfile
import os
from pathlib import Path
import glob


## unzip
##      zip 파일 삭제


zip_path = "./aihub_data"
zip_dir = Path(zip_path)  # 최상위 폴더 경로

unzip_path = zip_path + "_unzip"
unzip_dir = Path(unzip_path)

## unzip

def fix_encoding(name):
    """ZIP 내부 파일명을 cp437 → cp949로 복원"""
    try:
        return name.encode('cp437').decode('cp949')
    except:
        return name



os.makedirs(unzip_dir, exist_ok=True)


for zip_path in zip_dir.rglob("*.zip"):

    print(zip_path)
    relative_path = zip_path.relative_to(zip_dir).with_suffix('')
    extract_path = Path(unzip_path) / relative_path
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for info in zip_ref.infolist():
            fixed_name = fix_encoding(info.filename)
            target_file = extract_path / fixed_name

            # 디렉토리면 생성
            if info.is_dir():
                os.makedirs(target_file, exist_ok=True)
            else:
                # 상위 폴더 생성
                os.makedirs(target_file.parent, exist_ok=True)

                # 파일 복원
                with zip_ref.open(info.filename) as src, open(target_file, 'wb') as dst:
                    dst.write(src.read())

    print(f"{zip_path} → {extract_path} 해제 완료")

    # 압축 해재 마다 zip 삭제
    file_path = Path(zip_path)
    try:
        file_path.unlink()
        print(f"{zip_path}삭제 완료")
    except FileNotFoundError:
        print("파일이 없습니다.")

    


print("unzip 완료")