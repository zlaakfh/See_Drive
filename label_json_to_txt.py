# JSON 파일 → (class_name 확인) → (annotation에서 polygon 추출)
# → (좌표 정규화) → (YOLO 포맷 한 줄 생성) → .txt 저장

# =========================
# 사용자 설정 (여기만 바꾸면 됨)
# =========================

# 단일 .json 파일 or .json들이 있는 폴더
INPUT_PATH  = r"C:\Users\user\dacon_ws\Sample\02.라벨링데이터\segmentation"

# 결과 .txt 저장 폴더
OUTPUT_DIR  = r"C:\Users\user\dacon_ws\sesac_dacon\train_label"

# 이미지 크기
IMGW = 4056
IMGH = 3040


import json
from pathlib import Path

# class_name → class_id 맵핑
ANNOTATION_LABEL = {
    "Undefined Stuff": 0,
    "Wall": 1,
    "Driving Area": 2,
    "Non Driving Area": 3,
    "Parking Area": 4,
    "No Parking Area": 5,
    "Big Notice": 6,
    "Pillar": 7,
    "Parking Area Number": 8,
    "Parking Line": 9,
    "Disabled Icon": 10,
    "Women Icon": 11,
    "Compact Car Icon": 12,
    "Speed Bump": 13,
    "Parking Block": 14,
    "Billboard": 15,
    "Toll Bar": 16,
    "Sign": 17,
    "No Parking Sign": 18,
    "Traffic Cone": 19,
    "Fire Extinguisher": 20,
    "Undefined Object": 21,
    "Two-wheeled Vehicle": 22,
    "Vehicle": 23,
    "Wheelchair": 24,
    "Stroller": 25,
    "Shopping Cart": 26,
    "Animal": 27,
    "Human": 28
}


# -------------------------
# 1) polygon 탐색용 helpers
# -------------------------
def is_point_dict(d):
    '''{"x": 100, "y": 200} 형태인지 확인'''
    return isinstance(d, dict) and "x" in d and "y" in d

def is_point_list(item):
    '''
    "annotation":
    [
        [
            [
                {"x": 221.72, "y": 170.33},
                {"x": 277.54, "y": 170.81},
                {"x": 277.75, "y": 223.67},
                {"x": 221.93, "y": 223.19}
            ]
        ]
    ] 형태인지 확인
    '''
    return isinstance(item, list) and len(item) > 0 and all(is_point_dict(p) for p in item)

def extract_polygons(annotation):
    """
    annotation 안의 중첩 리스트를 재귀로 계속 탐색하면서,
    {x, y} 좌표들만 들어있는 리스트를 찾으면 polygons에 저장한다.

    예:
    [
      [
        [ {"x":1,"y":1}, {"x":5,"y":1}, {"x":5,"y":5}, {"x":1,"y":5} ],
        [ {"x":2,"y":2}, {"x":4,"y":2}, {"x":4,"y":4}, {"x":2,"y":4} ]
      ]
    ]
    → polygons = [
        [ {"x":1,"y":1}, {"x":5,"y":1}, {"x":5,"y":5}, {"x":1,"y":5} ],
        [ {"x":2,"y":2}, {"x":4,"y":2}, {"x":4,"y":4}, {"x":2,"y":4} ]
      ]
    """
    polygons = []

    def recurse(item):
        # 좌표 리스트면 수집
        if is_point_list(item):
            polygons.append(item)
            return
        # 리스트면 내부를 계속 확인
        if isinstance(item, list):
            for sub in item:
                recurse(sub)

    recurse(annotation)
    return polygons


# -------------------------
# 2) class + polygons 수집
# -------------------------
def collect_class_and_polygons(data, label_map):
    """
    JSON(dict)에서 objects를 순회하며:
      1) class_name을 label_map으로 class_id로 바꾸고
      2) annotation에서 폴리곤 좌표들을 추출한다.

    반환 형식:
    [
      { "class_id": 9,  "polygons": [ [ {x,y}, {x,y}, ... ], [ ... ] ] },
      { "class_id": 23, "polygons": [ [ {x,y}, {x,y}, ... ] ] },
      ...
    ]
    """
    results = []
    objects = data.get("objects", [])
    if not isinstance(objects, list):
        return results

    for obj in objects:
        cname = obj.get("class_name")
        if cname not in label_map:
            continue

        class_id = label_map[cname]
        annotation = obj.get("annotation", [])
        polys = extract_polygons(annotation)

        if polys:
            results.append({
                "class_id": class_id,
                "polygons": polys
            })

    return results


# -------------------------
# 3) 좌표 정규화 (0~1)
# -------------------------
def normalize_points(poly, imgw, imgh):
    """
    한 폴리곤( [{x,y}, {x,y}, ...] ) 안의 좌표들을
    이미지 크기 (imgw, imgh)로 나눠 0~1 범위로 정규화한다.
    """
    coords = []
    for p in poly:
        x = p["x"] / imgw
        y = p["y"] / imgh
        coords.extend([x, y])
    return coords

def to_normalized_results(items, imgw, imgh):
    """
    items 형식:
    [
      {"class_id": 23, "polygons": [ [ {x,y}, {x,y}, ... ], [ ... ] ]},
      ...
    ]
    → 좌표를 0~1로 나눈 동일 구조로 변환
    """
    out = []
    for it in items:
        class_id = it["class_id"]
        norm_polys = []
        for poly in it["polygons"]:
            norm_polys.append(normalize_points(poly, imgw, imgh))
        out.append({"class_id": class_id, "polygons": norm_polys})
    return out


# -------------------------
# 4) YOLO 라인 & 저장
# -------------------------
def yolo_line(class_id, coords):
    """YOLO-Seg 한 줄: class_id x1 y1 x2 y2 ..."""
    return f"{class_id} " + " ".join(map(str, coords))

def save_yolo_txt(data, results, output_dir):
    """
    정규화(0~1)된 좌표를 가진 results를 YOLO-Seg 라벨 파일(.txt)로 저장한다.
    - data["data_key"]의 파일명(확장자 제외)을 유지하고 .txt로 저장
    - output_dir 아래에 저장 폴더가 없으면 생성
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = Path(data.get("data_key") or "label")  # 예: "20220823_141221_60.json" 또는 ".png"
    out_path = out_dir / (base.stem + ".txt")     # → "20220823_141221_60.txt"

    lines = []
    for item in results:
        cid = item["class_id"]
        for coords in item["polygons"]:
            lines.append(yolo_line(cid, coords))
        # 🔹 클래스 하나가 끝날 때마다 빈 줄 추가
        lines.append("")

    # join할 때 \n 두 개 붙은 효과: 클래스별로 한 줄 띄어쓰기
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# -------------------------
# 5) 배치 처리 (파일/폴더 모두 지원)
# -------------------------
def process_one_json(json_path, output_dir, imgw=IMGW, imgh=IMGH):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = collect_class_and_polygons(data, ANNOTATION_LABEL)
    norm_results = to_normalized_results(items, imgw, imgh)
    save_yolo_txt(data, norm_results, output_dir)

    out_file = Path(output_dir) / (Path(data.get("data_key") or json_path.stem).stem + ".txt")
    print(f"[OK] {json_path.name} -> {out_file}")

def process_path(input_path, output_dir, imgw=IMGW, imgh=IMGH):
    """
    - input_path가 .json 파일이면 그 파일만 처리
    - 폴더면 재귀로 내부의 모든 .json 처리
    """
    input_path = Path(input_path)
    if input_path.is_file() and input_path.suffix.lower() == ".json":
        process_one_json(input_path, output_dir, imgw, imgh)
    else:
        for jp in input_path.rglob("*.json"):
            process_one_json(jp, output_dir, imgw, imgh)

# -------------------------
# 6) main
# -------------------------
def main():
    process_path(INPUT_PATH, OUTPUT_DIR, IMGW, IMGH)
    print("\nDone.")

if __name__ == "__main__":
    main()