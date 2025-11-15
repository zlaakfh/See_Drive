import subprocess
import os
import glob

api_key = "90F77A71-3D89-4C36-BE36-849A2400616A"

aihubshell_path = "./"
download_path = "./"
dataset_key = "71576"

total_gb = 0
camera_numbers = []
seg_numbers = []

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
    if "camera.zip" in line and "객체인식(2Hz)_" in line and "TS" in line:
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


    if "segmentation.zip" in line and "TL" in line:
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
        

cnt = 0
camera_gb = 0.0
seg_gb = 0.0
for key, value in par_download_list.items():
    if len(value["number"]) != 2:
        print(f"no pair data : {key} {value}")
        continue
    
    camera_gb += value["size"][0]
    seg_gb += value["size"][1]
    cnt += 1
    

print(f"download num : {cnt}")
print(f"camera size: {camera_gb} gb, seg size: {seg_gb} gb")
print("total size:", camera_gb + seg_gb, " GB")



if not os.path.isdir(download_path):
    os.makedirs(download_path, exist_ok=True)



i = 1
for key, value in par_download_list.items():
    if len(value["number"]) != 2:
        continue
    
    for file_key in value["number"]:
        print(f"download {key}, {i}/{cnt}")

        cmd = [aihubshell_exe, "-mode", "d", "-datasetkey", dataset_key, "-filekey", file_key, "-aihubapikey", api_key]
        result = subprocess.run(cmd,
                                capture_output=True, 
                                cwd=download_path,
                                text=True)
        
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
    # check pair download
    # 다운 오류로 파일이 하나만 있으면 삭제
    download_file = glob.glob(f"**/*{key}*", recursive=True)
    if len(download_file) != 2:
        print("not pair, delete file : ",download_file)
        os.remove(download_file[0])

    i+=1
