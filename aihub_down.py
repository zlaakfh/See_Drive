import subprocess
import os

api_key = ""

aihubshell_path = "/app"
download_path = "/app/new_test_flod"
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



for line in download_list:
    if "camera.zip" in line:
        camera_numbers.append(line.split("|")[-1].strip())

        data_size = line.split("|")[-2].split(" ")
        if data_size[2] == "GB":
            total_gb += int(data_size[1])
        elif data_size[2] == "MB":
            total_gb += int(data_size[1]) / 1024
        elif data_size[2] == "KB":
            total_gb += int(data_size[1]) / (1024 * 1024)

    if "segmentation.zip" in line:
        seg_numbers.append(line.split("|")[-1].strip())

        data_size = line.split("|")[-2].split(" ")
        if data_size[2] == "GB":
            total_gb += int(data_size[1])
        elif data_size[2] == "MB":
            total_gb += int(data_size[1]) / 1024
        elif data_size[2] == "KB":
            total_gb += int(data_size[1]) / (1024 * 1024)
    


print(f"camera_numbers : {len(camera_numbers)}, seg_numbers : {len(seg_numbers)}")
print(total_gb, " GB")



if not os.path.isdir(download_path):
    os.makedirs(download_path, exist_ok=True)


for i, filekey in enumerate(seg_numbers):
    cmd = [aihubshell_exe, "-mode", "d", "-datasetkey", dataset_key, "-filekey", filekey, "-aihubapikey", api_key]
    result = subprocess.run(cmd,
                            capture_output=True, 
                            cwd=download_path,
                            text=True)
    
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    print(f"download segmantation {i+1}/{len(seg_numbers)}")



for i, filekey in enumerate(camera_numbers):
    cmd = [aihubshell_exe, "-mode", "d", "-datasetkey", dataset_key, "-filekey", filekey, "-aihubapikey", api_key]
    result = subprocess.run(cmd,
                            capture_output=True, 
                            cwd=download_path,
                            text=True)
    
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    print(f"download camera {i+1}/{len(camera_numbers)}")