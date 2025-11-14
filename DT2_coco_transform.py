import os
import json
import numpy as np


###############################################
# 1) 기존 NumPy 계산 함수 
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
# 3) COCO 변환 메인 함수 (기존 구조 유지, segmentation 부분만 수정됨)
###############################################
def convert_to_coco(input_dir, output_file, directory):
    IMG_W = 4032
    IMG_H = 3040
    
    coco = {
        "images": [],
        "annotations": [],
        "categories": []
    }

    annotation_id = 0
    category_id_map = {}
    category_id_counter = 1

    for filename in os.listdir(input_dir):
        if not filename.endswith('.json'):
            continue

        with open(os.path.join(input_dir, filename), 'r') as f:
            data = json.load(f)

        img_filename = filename.replace('.json', '.png')

        # 기존 height/width 고정값 그대로 유지
        image_info = {
            "id": len(coco["images"]),
            "file_name": img_filename,
            "width": IMG_W,
            "height": IMG_H
        }
        coco["images"].append(image_info)

        #################################################
        # objects 내부 annotation 파싱 (중첩 구조 지원)
        #################################################
        for obj in data.get("objects", []):
            category_name = obj["class_name"]

            # 카테고리 등록
            if category_name not in category_id_map:
                category_id_map[category_name] = category_id_counter
                coco["categories"].append({
                    "id": category_id_counter,
                    "name": category_name
                })
                category_id_counter += 1

            # annotation raw data (중첩 리스트)
            seg_raw = obj.get("annotation", [])

            # 재귀 기반 polygon(dict list) 추출
            polygons = extract_polygon_dicts(seg_raw)

            # 기존 new_seg + area + bbox 생성 방법 유지
            for poly_dict_list in polygons:

                # polygon flatten → [x1,y1,x2,y2,...]
                new_seg = []
                for point in poly_dict_list:   # {'x':??, 'y':??}
                    new_seg.append(point["x"])
                    new_seg.append(point["y"])

                if len(new_seg) < 6:
                    continue  # polygon 최소 점 3개 필요

                area = calculate_area(new_seg)
                bbox = calculate_bbox(new_seg)

                ann = {
                    "id": annotation_id,
                    "image_id": image_info["id"],
                    "category_id": category_id_map[category_name],
                    "segmentation": [new_seg],
                    "area": float(area),
                    "bbox": bbox,
                    "iscrowd": 0
                }

                coco["annotations"].append(ann)
                annotation_id += 1

    # COCO JSON 저장
    with open(output_file, 'w') as f:
        json.dump(coco, f, indent=4)


###############################################
# 4) train/val 변환 실행
###############################################
for d in ('train', 'val', 'test'):
    print(f'{d} start')
    input_dir = f'data_set/{d}/labels'
    output_file = f'data_set/{d}.json'
    convert_to_coco(input_dir, output_file, d)

print("COCO 변환 완료")
