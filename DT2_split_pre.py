# 1.데이터 spilt 코드
import os
import json
# import cv2
import numpy as np
import shutil
from sklearn.model_selection import train_test_split

# 1-1.파일 이름 수정
def rename_and_copy_images(src_dir, dst_dir, target='.png', rm_name=''):
    """
    src_dir: 기존 이미지가 저장된 디렉토리
    dst_dir: 새로운 이미지가 저장될 디렉토리
    target: 타겟 파일 형식
    rm_name: 해당 문자열이 파일명에 포함된 경우, 문자열 부분 삭제
    """
    # dst_dir이 없으면 생성
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    # Traverse the source directory
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.lower().endswith(target):  # target 타입의 파일이면
                # 새로운 이름 생성
                relative_path = os.path.relpath(os.path.join(root, file), src_dir)
                new_name = relative_path.replace(os.sep, '_').replace(rm_name, '') # 필요없는 이름 삭제

                # 새로운 경로
                dst_file_path = os.path.join(dst_dir, new_name)
                os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)

                # 파일 복사
                shutil.copy2(os.path.join(root, file), dst_file_path)

    # 이미지 파일 이름 수정 - src_dir 하위 이미지 파일들 이름 수정 후 dst_dir에 저장
src_dir= '/_unzip/181.실내_자율_주차용_데이터/01-1.정식개방데이터/Validation/01.원천데이터'
dst_dir = '/dataset/images'

rename_and_copy_images(src_dir, dst_dir, '.png', '') # 필요 없는 부분 이름 넣고 삭제

    # 라벨 파일 이름 수정 - src_dir 하위 라벨 파일들 이름 수정 후 dst_dir에 저장
src_dir= '/_unzip/181.실내_자율_주차용_데이터/01-1.정식개방데이터/Validation/02.라벨링데이터'
dst_dir = '/dataset/labels'

rename_and_copy_images(src_dir, dst_dir, '.json', '')

    # 복사 루트 이미지 & 라벨 개수 확인
print(len(os.listdir('dataset/images')))
print(len(os.listdir('dataset/labels')))



# 1-2. train/validation/test 분할 7: 2: 1
img_dir = '/dataset/images'
lbl_dir = '/dataset/labels'

    # 분할된 데이터를 저장할 경로 설정
train_image_dir = '/data_set/train/images'
val_image_dir = '/data_set/val/images'
test_image_dir = '/data_set/test/images'

train_label_dir = '/data_set/train/labels'
val_label_dir = '/data_set/val/labels'
test_label_dir = '/data_set/test/labels'

    # 폴더가 존재하지 않으면 생성
os.makedirs(train_image_dir, exist_ok=True)
os.makedirs(val_image_dir, exist_ok=True)
os.makedirs(test_image_dir, exist_ok=True)

os.makedirs(train_label_dir, exist_ok=True)
os.makedirs(val_label_dir, exist_ok=True)
os.makedirs(test_label_dir, exist_ok=True)

    # 이미지와 라벨 파일 리스트 가져오기
images = sorted(os.listdir(img_dir))   ######
labels = sorted(os.listdir(lbl_dir))

    # 데이터셋 분할
train_images, temp_images, train_labels, temp_labels = train_test_split(images, labels, test_size=0.3, random_state=42) # train:temp = 7:3   ####
val_images, test_images, val_labels, test_labels = train_test_split(temp_images, temp_labels, test_size=1/3, random_state=42) # val:test = 2:1

def copy_files(file_list, src_dir, dst_dir):
    for file_name in file_list:
        shutil.copy(os.path.join(src_dir, file_name), os.path.join(dst_dir, file_name))

    # 파일 복사
print('train')
copy_files(train_images, img_dir, train_image_dir)
copy_files(train_labels, lbl_dir, train_label_dir)
print('val')
copy_files(val_images, img_dir, val_image_dir)
copy_files(val_labels, lbl_dir, val_label_dir)
print('test')
copy_files(test_images, img_dir, test_image_dir)
copy_files(test_labels, lbl_dir, test_label_dir)

    # train/val/test set 개수 확인
print(f"train: {len(os.listdir('dataset/train/images'))}")
print(f"val: {len(os.listdir('dataset/val/images'))}")
print(f"test: {len(os.listdir('dataset/test/images'))}")
