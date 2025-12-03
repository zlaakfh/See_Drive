import os
import json
import numpy as np
from tqdm import tqdm

###########################
# 🔧 0) 사용자 설정 
###########################
# 바꿀 부분
###################################################################################################################################
# 이미지 가로 세로 크기
IMG_W = 1920
IMG_H = 1080
# 클래스 개수
CLASS_NUM = 2

###################################################################################################################################
# 이미지 사이즈
IMG_SIZE = f"{IMG_W}x{IMG_H}"  
# json 만들 데이터셋 이름
DATASET_NAME = f"dataset_DT_cls{CLASS_NUM}_{IMG_SIZE}"
# train/val/test 라벨 경로
BASE_DIR = f"./aihub_data_unzip"

###############################################
# 1) class_name → class_id 고정 맵핑 
###############################################
ANNOTATION_LABEL = {
    "Driveable Space": 1, 
    "Parking Space": 2, 
}


# id -> name 으로 뒤집은 딕셔너리 (categories 생성용)
ID_TO_NAME = {v: k for k, v in ANNOTATION_LABEL.items()}


###############################################
# 1) 기존 NumPy 계산 함수 (그대로)
###############################################
def calculate_area(polygon):
    x = np.array(polygon[::2])
    y = np.array(polygon[1::2])
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def calculate_bbox(polygon):
    x = polygon[::2]
    y = polygon[1::2]
    return [min(x), min(y), max(x) - min(x), max(y) - min(y)]


###############################################
# 2) segmentation 중첩 구조에서 polygon(dict list)만 추출하는 함수
###############################################
def extract_polygon_dicts(seg):
    """
    segmentation 안에서 [{x,y},{x,y}...] 형태의 polygon만 추출하여 리스트로 반환.
    new_seg(flat list) 변환은 기존 코드에서 처리한다.
    """
    polygons = []

    def traverse(item):
        # polygon 형태는 dict 리스트
        if isinstance(item, list) and len(item) > 0 and isinstance(item[0], dict):
            polygons.append(item)
        # 리스트 안에 리스트가 더 있으면 계속 탐색
        elif isinstance(item, list):
            for elem in item:
                traverse(elem)

    traverse(seg)
    return polygons  # [{x,y},{x,y}...] 형태로 추출


###############################################
# 3) COCO 변환 메인 함수
#    -> 여기서 category_id를 ANNOTATION_LABEL 기준으로 고정
###############################################
# 라벨 통합하는 코드
import os
import json
# import cv2
import numpy as np

def calculate_area(polygon):
    x = np.array(polygon[::2])
    y = np.array(polygon[1::2])
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def calculate_bbox(polygon):
    x = polygon[::2]
    y = polygon[1::2]
    return [min(x), min(y), max(x) - min(x), max(y) - min(y)]

def convert_to_coco(input_dir, output_file, directory):
    # 초기 세팅
    coco = {
        "info" : [],
        "images": [],
        "annotations": [],
        "categories": []
    }

    annotation_id = 0
    category_id_map = {}
    category_id_counter = 1

    # 라벨 변경
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            with open(os.path.join(input_dir, filename), 'r') as f:
                data = json.load(f)

                # 이미지 정보
                img_filename = filename.replace('.json', '.jpg')

                # img = cv2.imread('/content/drive/MyDrive/alice/dataset/' + directory + '/images/' + img_filename)
                # height, width, _ = img.shape

                image_info = {
                    "id": len(coco["images"]),
                    "file_name": img_filename, # 이미지와 라벨의 파일명은 같음
                    "width": 1920,
                    "height": 1080
                }
                coco["images"].append(image_info)

                '''
                # 2D bbox 어노테이션은 필요하면 추가
                for bbox2d in data.get("bbox2d", []):
                    category_name = bbox2d["name"]
                    if category_name not in category_id_map:
                        category_id_map[category_name] = category_id_counter
                        coco["categories"].append({
                            "id": category_id_counter,
                            "name": category_name
                        })
                        category_id_counter += 1

                    bbox = bbox2d["bbox"]
                    x_min, y_min, x_max, y_max = bbox
                    width = x_max - x_min
                    height = y_max - y_min

                    annotation = {
                        "id": annotation_id,
                        "image_id": image_info["id"],
                        "category_id": category_id_map[category_name],
                        "bbox": [x_min, y_min, width, height],
                        "area": width * height,
                        "iscrowd": 0
                    }
                    coco["annotations"].append(annotation)
                    annotation_id += 1
                '''

                # Add segmentations
                for segmentation in data.get("segmentation", []):
                    category_name = segmentation["name"]
                    if category_name not in category_id_map:
                        category_id_map[category_name] = category_id_counter
                        coco["categories"].append({
                            "id": category_id_counter,
                            "name": category_name
                        })
                        category_id_counter += 1

                    # segmentation을 [[x1, y1], [x1, y1], ...] => [x1, y1, x1, y1, ...] 형식으로 수정
                    new_seg = []
                    for x1, y1 in segmentation['polygon']:
                        new_seg.append(x1)
                        new_seg.append(y1)

                    # 면적 및 bbox 계산
                    area = calculate_area(new_seg)
                    bbox = calculate_bbox(new_seg)

                    annotation = {
                        "id": annotation_id,
                        "image_id": image_info["id"],
                        "category_id": category_id_map[category_name],
                        "segmentation": [new_seg],
                        "area": area,
                        "bbox": bbox,
                        "iscrowd": 0
                    }
                    coco["annotations"].append(annotation)
                    annotation_id += 1

    # Save the result to a JSON file
    with open(output_file, 'w', encoding='utf-8') as f: # encoding='utf-8' 조건 추가 가능하지만 오래걸림
        json.dump(coco, f, indent=4) # ensure_ascii=False 조건을 추가하여 한글 깨짐을 해결할 수 있으나 시간 오래 걸림


###############################################
# 4) train / val / test 변환 실행
###############################################
for d in ("train", "val", "test"):
    print(f"\n===== {d} 변환 시작 =====")
    input_dir = f"{BASE_DIR}/{d}/labels"
    output_file = f"{BASE_DIR}/{d}.json"
    convert_to_coco(input_dir, output_file, d)

print("\n🎉 COCO 변환 완료!")