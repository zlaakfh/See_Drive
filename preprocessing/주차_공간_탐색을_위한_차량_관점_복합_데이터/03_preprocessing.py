import zipfile
import os
from pathlib import Path
import glob
import json
from sklearn.model_selection import train_test_split
import shutil


zip_path = "./aihub_data"
zip_dir = Path(zip_path)  # 최상위 폴더 경로

unzip_path = zip_path + "_unzip"
unzip_dir = Path(unzip_path)


os.makedirs(f"{unzip_dir}/images", exist_ok=True)
os.makedirs(f"{unzip_dir}/labels", exist_ok=True)


## 파일 이름을 디렉토리 + 파일 이름으로 수정

image_list = glob.glob(f"{unzip_path}/**/*.jpg", recursive=True)
json_list = glob.glob(f"{unzip_path}/**/*.json", recursive=True)

for path in image_list:
    file_name = path.split("/")[-1]
    folder_name = path.split("/")[-3]
    mix_name = f"{unzip_path}/images/{folder_name}_{file_name}"
    print(path, "\n", mix_name)
    os.rename(path, mix_name)

for path in json_list:
    file_name = path.split("/")[-1]
    folder_name = path.split("/")[-3]
    mix_name = f"{unzip_path}/labels/{folder_name}_{file_name}"
    print(path, "\n", mix_name)
    os.rename(path, mix_name)


## 파일 짝이 안맞으면 삭제

camera_unzip_list = glob.glob(f"{unzip_dir}/images/*jpg", recursive=True)

# json 짝이 없으면 삭제
not_pair_cnt = 0
for img_name in camera_unzip_list:
    json_name = img_name
    json_name = json_name.replace("images", "labels").replace(".jpg", ".json")
    

    if os.path.exists(json_name):
        pass
    else:
        print(json_name, "파일 없음", img_name, "삭제")
        not_pair_cnt += 1
        # 삭제
        file_path = Path(img_name)
        file_path.unlink()
 
## 
json_unzip_list = glob.glob(f"{unzip_dir}/labels/*json", recursive=True)

for json_name in json_unzip_list:
    img_name = json_name
    img_name = img_name.replace("labels", "images").replace(".json", ".jpg")
    

    if os.path.exists(img_name):
        pass
    else:
        print(img_name, "파일 없음", json_name, "삭제")
        not_pair_cnt += 1
        # 삭제
        file_path = Path(json_name)
        file_path.unlink()

print(not_pair_cnt)




## seg 없는 json 갯수

json_unzip_list = glob.glob(f"{unzip_dir}/labels/*json", recursive=True)

labeling_class = {'Parking Space': 0, 'Driveable Space': 1}

emtpy_cnt = 0
for seg_json in json_unzip_list:
    # print(seg_json)
    with open(seg_json, 'r') as f:
        seg_data = json.load(f)
    if not seg_data["segmentation"]:
        emtpy_cnt += 1
        file_path = Path(seg_json)
        file_path.unlink()
    
    
print(f"not seg data : {emtpy_cnt}")

# json 짝이 없으면 삭제
camera_unzip_list = glob.glob(f"{unzip_dir}/images/*jpg", recursive=True)

not_pair_cnt = 0
for img_name in camera_unzip_list:
    json_name = img_name
    json_name = json_name.replace("images", "labels").replace(".jpg", ".json")
    

    if os.path.exists(json_name):
        pass
    else:
        print(json_name, "파일 없음", img_name, "삭제")
        not_pair_cnt += 1
        # 삭제
        file_path = Path(img_name)
        file_path.unlink()



## data split
## 데이터셋 분할: train:val:test = 7:2:1
camera_unzip_list = sorted(glob.glob(f"{unzip_dir}/images/*jpg", recursive=True))
json_unzip_list = sorted(glob.glob(f"{unzip_dir}/labels/*json", recursive=True))


train_images, temp_images, train_labels, temp_labels = train_test_split(
    camera_unzip_list, json_unzip_list, test_size=0.3, random_state=42   # train:temp = 7:3
)
val_images, test_images, val_labels, test_labels = train_test_split(
    temp_images, temp_labels, test_size=1/3, random_state=42             # val:test = 2:1
)

print(f"train {len(train_images)}, {len(train_labels)}")
print(f"val {len(val_images)}, {len(val_labels)}")
print(f"test {len(test_images)}, {len(test_labels)}")


train_image_dir = os.path.join(unzip_dir, "train", "images")
val_image_dir   = os.path.join(unzip_dir, "val", "images")
test_image_dir  = os.path.join(unzip_dir, "test", "images")

train_label_dir = os.path.join(unzip_dir, "train", "labels")
val_label_dir   = os.path.join(unzip_dir, "val", "labels")
test_label_dir  = os.path.join(unzip_dir, "test", "labels")

for d in [
    train_image_dir, val_image_dir, test_image_dir,
    train_label_dir, val_label_dir, test_label_dir
]:
    os.makedirs(d, exist_ok=True)

def move_files(file_list, dir1):
    for file_path in file_list:

        # 파일명만 추출
        file_name = os.path.basename(file_path)

        # 목적지 경로 합치기
        destination_path = os.path.join(dir1, file_name)
        # print(file_path, destination_path)
        shutil.move(file_path, destination_path)


print("\n[TRAIN] 이동 중...")
move_files(train_images, train_image_dir)
move_files(train_labels, train_label_dir)

print("\n[VAL] 이동 중...")
move_files(val_images, val_image_dir)
move_files(val_labels, val_label_dir)

print("\n[TEST] 이동 중...")
move_files(test_images, test_image_dir)
move_files(test_labels, test_label_dir)

print("\n========== 데이터 분할 완료 ==========")


