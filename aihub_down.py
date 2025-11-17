import subprocess
import os
import glob
import json
from pathlib import Path
import zipfile
from PIL import Image
from tqdm import tqdm

# curl -o "aihubshell" https://api.aihub.or.kr/api/aihubshell.do
# chmod +x aihubshell


# 1008x760 , // 4
resize_ratio = 4


api_key = ""

aihubshell_path = "/home/elicer/song/sesac_dacon/"
download_path = "./aihub_data"
dataset_key = "71576"

total_gb = 0
camera_numbers = []
seg_numbers = []




# ============================================================

ORIGINAL_SIZE = (4032, 3040)
TARGET_HEIGHT = ORIGINAL_SIZE[1] // resize_ratio
aspect_ratio = ORIGINAL_SIZE[0] / ORIGINAL_SIZE[1]
new_width = int(round(TARGET_HEIGHT * aspect_ratio))
NEW_SIZE = (new_width, TARGET_HEIGHT)
size_folder = f"{NEW_SIZE[0]}x{NEW_SIZE[1]}"

scale_x = NEW_SIZE[0] / ORIGINAL_SIZE[0]
scale_y = NEW_SIZE[1] / ORIGINAL_SIZE[1]

resize_image_path = f"/home/elicer/val_data/{size_folder}/images"
resize_label_path = f"/home/elicer/val_data/{size_folder}/labels"

os.makedirs(resize_image_path, exist_ok=True)
os.makedirs(resize_label_path, exist_ok=True)


def unzip_file(zip_file: str, output_dir: str):

    zip_path = Path(zip_file)
    out_dir = Path(output_dir)

    # 출력 폴더 생성
    os.makedirs(out_dir, exist_ok=True)

    # 압축 해제
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(out_dir)

    print(f"{zip_path} → {out_dir} 압축 해제 완료")

def resize_and_save_json(src_path, dst_path):
    try:
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1) polygon scaling (기존 코드 그대로 유지)
        for obj in data.get("objects", []):
            for ann_group in obj.get("annotation", []):
                for polygon in ann_group:
                    for point in polygon:
                        point["x"] = int(point["x"] * scale_x)
                        point["y"] = int(point["y"] * scale_y)
                        
        # 2) meta 내부 이미지 사이즈 업데이트 추가
        meta = data.get("meta", {})
        if "size" in meta:
            if "width" in meta["size"]:
                meta["size"]["width"] = NEW_SIZE[0]
            if "height" in meta["size"]:
                meta["size"]["height"] = NEW_SIZE[1]

        data["meta"] = meta
        name = src_path.split("/")[-1]
        with open(f"{dst_path}/{name}", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"[오류] JSON 라벨 처리 실패: {src_path} ({e})")

def resize_and_save_image(src_path, dst_path):
    try:
        name = src_path.split("/")[-1]
        with Image.open(src_path) as img:
            resized = img.resize(NEW_SIZE, Image.LANCZOS)
            resized.save(f"{dst_path}/{name}")
    except Exception as e:
        print(f"[오류] 이미지 리사이즈 실패: {src_path} ({e})")


def remove_download_file():
    print("remove download file")

    zip_file_list = glob.glob(f"{download_path}/**/*.zip", recursive=True)
    for file in tqdm(zip_file_list):
        os.remove(file)
    
    png_list = glob.glob(f"{download_path}/**/*.png", recursive=True)
    for file in tqdm(png_list):
        os.remove(file)

    json_list = glob.glob(f"{download_path}/**/*.json", recursive=True)
    for file in tqdm(json_list):
        os.remove(file)

    

aihubshell_exe = os.path.join(aihubshell_path, "aihubshell")
print(aihubshell_exe)

result = subprocess.run([aihubshell_exe, "-mode", "l", "-datasetkey", dataset_key],
                        capture_output=True, text=True)

# print("stdout:", result.stdout)
# print("stderr:", result.stderr)


download_list = result.stdout.split("\n")

camera_list = []
par_download_list = {}

for line in download_list:
    if "camera.zip" in line and "객체인식(2Hz)_" in line and "VS" in line:
        number = line.split("|")[-1].strip()
        name = line.split("|")[-3].strip().split("├─")[-1]
        name = name.split("객체인식(2Hz)")[-1].split(".camera")[-2][:-3]

        data_size = line.split("|")[-2].split(" ")
        dt_size = 0.0
        if data_size[2] == "GB":
            dt_size += int(data_size[1])
        elif data_size[2] == "MB":
            dt_size += int(data_size[1]) / 1024
        elif data_size[2] == "KB":
            dt_size += int(data_size[1]) / (1024 * 1024)

        r = par_download_list.get(name, None)
        if r == None:
            par_download_list[name] = {"number":[number], "size": [dt_size]}
        else:
            par_download_list[name]["number"].append(number)
            par_download_list[name]["size"].append(dt_size)


    if "segmentation.zip" in line and "VL" in line:
        number = line.split("|")[-1].strip()
        name = line.split("|")[-3].strip().split("├─")[-1]
        name = name.split("객체인식(2Hz)")[-1].split(".segmentation")[-2][:-3]

        data_size = line.split("|")[-2].split(" ")
        dt_size = 0.0
        if data_size[2] == "GB":
            dt_size += int(data_size[1])
        elif data_size[2] == "MB":
            dt_size += int(data_size[1]) / 1024
        elif data_size[2] == "KB":
            dt_size += int(data_size[1]) / (1024 * 1024)

        r = par_download_list.get(name, None)
        if r == None:
            par_download_list[name] = {"number":[number], "size": [dt_size]}
        else:
            par_download_list[name]["number"].append(number)
            par_download_list[name]["size"].append(dt_size)
        

total_download_file_num = 0
camera_gb = 0.0
seg_gb = 0.0
for key, value in par_download_list.items():
    if len(value["number"]) != 2:
        print(f"no pair data : {key} {value}")
        continue
    
    camera_gb += value["size"][0]
    seg_gb += value["size"][1]
    total_download_file_num += 1
    

print(f"download num : {total_download_file_num} * 2")
print(f"camera size: {camera_gb} gb, seg size: {seg_gb} gb")
print("total size:", camera_gb + seg_gb, " GB")



if not os.path.isdir(download_path):
    os.makedirs(download_path, exist_ok=True)


current_download_num = 1
for key, value in par_download_list.items():

    if len(value["number"]) != 2:
        continue
    
    for file_key in value["number"]:
        print(f"download {key}, {current_download_num}/{total_download_file_num}")

        cmd = [aihubshell_exe, "-mode", "d", "-datasetkey", dataset_key, "-filekey", file_key, "-aihubapikey", api_key]
        result = subprocess.run(cmd,
                                capture_output=True, 
                                cwd=download_path,
                                text=True)
        
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
    # check pair download
    # 다운 오류로 파일이 하나만 있으면 삭제

    zip_path = f"{download_path}/**/*.zip"
    download_file = glob.glob(zip_path, recursive=True)
    if len(download_file) != 2:
        print("not pair, delete file : ",download_file)
        remove_download_file()
    
    # segmentation 압축해제
    seg_zip = [f for f in download_file if "segmentation" in f][0]
    unzip_file(seg_zip, f"{download_path}/labels")

    # camera 압축해제
    camera_zip = [f for f in download_file if "camera" in f][0]
    unzip_file(camera_zip, f"{download_path}/images")
    
    # camera, segmentation resize
    camera_unzip_list = glob.glob(f"{download_path}/images/*png", recursive=True)
    
    # json 짝이 있으면 json 변환
    for img_name in tqdm(camera_unzip_list):
        json_name = img_name
        json_name = json_name.replace("images", "labels").replace(".png", ".json")
        

        if os.path.exists(json_name):
            resize_and_save_json(json_name, resize_label_path)
            resize_and_save_image(img_name, resize_image_path)
        else:
            print(json_name, "파일 없음")

    # 다운 받은 데이터 삭제
    remove_download_file()
    current_download_num+=1
