import subprocess
import os
import glob
import json
from pathlib import Path
import zipfile
from PIL import Image
from tqdm import tqdm


# https://aihub.or.kr/aihubdata/data/view.do?pageIndex=1&currMenu=115&topMenu=100&srchOptnCnd=OPTNCND001&searchKeyword=%EC%A3%BC%EC%B0%A8+%EA%B3%B5%EA%B0%84+%ED%83%90%EC%83%89&srchDetailCnd=DETAILCND001&srchOrder=ORDER001&srchPagePer=20&aihubDataSe=data&dataSetSn=598
# 주차 공간 탐색을 위한 차량 관점 복합 데이터 

# curl -o "aihubshell" https://api.aihub.or.kr/api/aihubshell.do
# chmod +x aihubshell


# 1008x760 , // 4
resize_ratio = 4


api_key = "B7CF0514-EF35-4305-9F12-E08B64778090"

aihubshell_path = "/home/elicer/song/sesac_dacon/"
download_path = "./aihub_data"
dataset_key = "598"


aihubshell_exe = os.path.join(aihubshell_path, "aihubshell")
print(aihubshell_exe)

result = subprocess.run([aihubshell_exe, "-mode", "l", "-datasetkey", dataset_key],
                        capture_output=True, text=True)

print("stdout:", result.stdout)
print("stderr:", result.stderr)


download_list = result.stdout.split("\n")

camera_list = []
par_download_list = {}

down_num = []

for line in download_list:

    if "TS" in line or "TL" in line or "VS" in line or "VL" in line:
        number = line.split("|")[-1].strip()
        down_num.append(number)

        
print(down_num)



if not os.path.isdir(download_path):
    os.makedirs(download_path, exist_ok=True)


current_download_num = 1
for num in tqdm(down_num):
    print(f"download {num}/{len(down_num)}")
    
    cmd = [aihubshell_exe, "-mode", "d", "-datasetkey", dataset_key, "-filekey", num, "-aihubapikey", api_key]
    result = subprocess.run(cmd,
                            capture_output=True, 
                            cwd=download_path,
                            text=True)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    
    
    current_download_num += 1