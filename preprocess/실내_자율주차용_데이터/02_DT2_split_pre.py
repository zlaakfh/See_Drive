# 1. 데이터 split 코드
import os
import shutil
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# split 이후 복제가 아닌 이전 파일은 삭제됩니다! (신중)

#########################################
# 1-1. 이미지 / 라벨 매칭
#########################################
# 바꿀 부분
###################################################################################################################################
# 이미지 가로 세로 크기
IMG_W = 4032 // 4
IMG_H = 3040 // 4
# 클래스 개수
CLASS_NUM = 5
# iter 넘버
# ITER_NUM = 1000
# 리사이즈된 데이터가 저장된 경로
INPUT_DIR = r"C:\Users\21-01-00038\Desktop\sesac\Test\data"
# split 데이터가 저장될 최상위 폴더
SPLIT_ROOT = r"C:\Users\21-01-00038\Desktop\sesac\Test\data_split"
###################################################################################################################################

# 이미지 사이즈
IMG_SIZE = f"{IMG_W}x{IMG_H}"  
# split할 데이터셋 이름

img_dir = os.path.join(INPUT_DIR, IMG_SIZE, "images")
lbl_dir = os.path.join(INPUT_DIR, IMG_SIZE, "labels")

OUTPUT_NAME = f"dataset_DT_cls{CLASS_NUM}_{IMG_SIZE}" 

# split된 데이터셋 저장 폴더
OUT_ROOT = os.path.join(SPLIT_ROOT, OUTPUT_NAME) 

train_image_dir = os.path.join(OUT_ROOT, "train", "images")
val_image_dir   = os.path.join(OUT_ROOT, "val", "images")
test_image_dir  = os.path.join(OUT_ROOT, "test", "images")

train_label_dir = os.path.join(OUT_ROOT, "train", "labels")
val_label_dir   = os.path.join(OUT_ROOT, "val", "labels")
test_label_dir  = os.path.join(OUT_ROOT, "test", "labels")

for d in [
    train_image_dir, val_image_dir, test_image_dir,
    train_label_dir, val_label_dir, test_label_dir
]:
    os.makedirs(d, exist_ok=True)

# 이미지/라벨 매칭

images = sorted(os.listdir(img_dir))
labels = sorted(os.listdir(lbl_dir))

matched_pairs = []
for img in tqdm(images, desc="Matching images & labels", dynamic_ncols=True):
    base = os.path.splitext(img)[0]
    json_name = base + ".json"
    if json_name in labels:
        matched_pairs.append((img, json_name))
    else:
        print(" 라벨 없음:", img)

# 매칭된 리스트로 완전히 교체
if matched_pairs:
    images, labels = zip(*matched_pairs)
    images = list(images)
    labels = list(labels)
else:
    images, labels = [], []

print("최종 매칭 이미지 개수:", len(images))
print("최종 매칭 라벨 개수:", len(labels))


#########################################
# 2. train / val / test 분할 7:2:1
#########################################

# 데이터셋 분할: train:val:test = 7:2:1
train_images, temp_images, train_labels, temp_labels = train_test_split(
    images, labels, test_size=0.3, random_state=42   # train:temp = 7:3
)
val_images, test_images, val_labels, test_labels = train_test_split(
    temp_images, temp_labels, test_size=1/3, random_state=42  # val:test = 2:1
)

#########################################
# 3. 파일 복사 함수
#########################################

def move_files(file_list, src_dir, dst_dir, desc="Moving files"):
    for file_name in tqdm(file_list, desc=desc):
        src = os.path.join(src_dir, file_name)
        dst = os.path.join(dst_dir, file_name)
        shutil.move(src, dst)


print("\n[TRAIN] 이동 중...")
move_files(train_images, img_dir, train_image_dir, "Train images")
move_files(train_labels, lbl_dir, train_label_dir, "Train labels")

print("\n[VAL] 이동 중...")
move_files(val_images, img_dir, val_image_dir, "Val images")
move_files(val_labels, lbl_dir, val_label_dir, "Val labels")

print("\n[TEST] 이동 중...")
move_files(test_images, img_dir, test_image_dir, "Test images")
move_files(test_labels, lbl_dir, test_label_dir, "Test labels")

#########################################
# 4. 데이터 개수 확인
#########################################
print("\n========== 데이터 분할 완료 ==========")
print(f"train: {len(os.listdir(train_image_dir))}")
print(f"val:   {len(os.listdir(val_image_dir))}")
print(f"test:  {len(os.listdir(test_image_dir))}")

print("\n원본 데이터(images, labels)는 move 되면서 자동으로 삭제되었습니다.")
print(f"Split 데이터는 {OUT_ROOT} 에 저장되었습니다.")

#########################################
# 5. 기존 폴더 삭제
#########################################
folder_to_delete = os.path.join(INPUT_DIR, IMG_SIZE)
if os.path.exists(folder_to_delete):
    shutil.rmtree(folder_to_delete)
    print(f"\n원본 폴더 삭제 완료 → {folder_to_delete}")