# test_convert_json_to_yoloseg.py
# - JSON(annotation polygon) → YOLO-Seg(.txt)
# - 저장 파일명은 JSON 파일명(stem)과 동일하게 유지 (abc123.json → abc123.txt)

from pathlib import Path
import json

# ===== 사용자 설정: 필요 시 바꾸세요 =====

INPUT = "/home/elicer/sesac_dacon/_unzip/181.실내_자율주차용_데이터/01-1.정식개방데이터/Validation/02.라벨링데이터"
OUTPUT = r"D:\자율주행_팀플\data"

IMGW = 4056  # 이미지 원본 너비
IMGH = 3040  # 이미지 원본 높이

# class_name → class_id 맵핑
ANNOTATION_LABEL = {
    "Undefined Stuff": 0, "Wall": 1, "Driving Area": 2, "Non Driving Area": 3,
    "Parking Area": 4, "No Parking Area": 5, "Big Notice": 6, "Pillar": 7,
    "Parking Area Number": 8, "Parking Line": 9, "Disabled Icon": 10,
    "Women Icon": 11, "Compact Car Icon": 12, "Speed Bump": 13,
    "Parking Block": 14, "Billboard": 15, "Toll Bar": 16, "Sign": 17,
    "No Parking Sign": 18, "Traffic Cone": 19, "Fire Extinguisher": 20,
    "Undefined Object": 21, "Two-wheeled Vehicle": 22, "Vehicle": 23,
    "Wheelchair": 24, "Stroller": 25, "Shopping Cart": 26, "Animal": 27, "Human": 28
}

# -------------------------
# 1) polygon 탐색용
# -------------------------
def _is_point_dict(d):
    '''{"x": 100, "y": 200} 형태인지 확인'''
    return isinstance(d, dict) and "x" in d and "y" in d

def _is_point_list(item):
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
    return isinstance(item, list) and len(item) > 0 and all(_is_point_dict(p) for p in item)

def _extract_polygons(annotation):
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
    def recurse(it):
        if _is_point_list(it):
            polygons.append(it); return
        if isinstance(it, list):
            for sub in it: recurse(sub)
    recurse(annotation)
    return polygons

# -------------------------
# 2) class + polygons 수집
# -------------------------

def _collect_class_and_polygons(data, label_map):
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
    results, objects = [], data.get("objects", [])
    if not isinstance(objects, list): return results
    for obj in objects:
        cname = obj.get("class_name")
        if cname not in label_map: continue
        polys = _extract_polygons(obj.get("annotation", []))
        if polys:
            results.append({"class_id": label_map[cname], "polygons": polys})
    return results

# -------------------------
# 3) 좌표 정규화 (0~1)
# -------------------------

def _normalize_points(poly, imgw, imgh):
    """
    한 폴리곤( [{x,y}, {x,y}, ...] ) 안의 좌표들을
    이미지 크기 (imgw, imgh)로 나눠 0~1 범위로 정규화한다.
    """
    coords = []
    for p in poly:
        coords.extend([p["x"]/imgw, p["y"]/imgh])
    return coords

def _to_normalized_results(items, imgw, imgh):
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
        out.append({
            "class_id": it["class_id"],
            "polygons": [_normalize_points(poly, imgw, imgh) for poly in it["polygons"]]
        })
    return out

# -------------------------
# 4) YOLO 라인 & 저장
# -------------------------
def _yolo_line(class_id, coords):
    """YOLO-Seg 한 줄: class_id x1 y1 x2 y2 ..."""
    return f"{class_id} " + " ".join(f"{v:.6f}" for v in coords)

# -------------------------
# 5) txt 파일로 저장
# -------------------------
def convert_json_to_txt(json_path: Path, out_txt_path: Path, imgw: int = IMGW, imgh: int = IMGH):
    """
    JSON 1개를 읽어서 YOLO-Seg 라벨(.txt)로 저장
    - 저장 파일명은 호출자가 넘긴 out_txt_path를 그대로 사용
    - 좌표는 0~1 정규화
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = _collect_class_and_polygons(data, ANNOTATION_LABEL)
    norm_results = _to_normalized_results(items, imgw, imgh)

    out_txt_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for item in norm_results:
        for coords in item["polygons"]:
            lines.append(_yolo_line(item["class_id"], coords))
        lines.append("")  # 클래스별 구분 공백 줄

    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def convert_path(input_path, output_dir, imgw: int = IMGW, imgh: int = IMGH):
    """
    input_path: 파일(.json) 또는 폴더(재귀)
    output_dir: 결과 .txt 저장 폴더
    - 저장명은 JSON 파일명(stem) 그대로 사용
    """
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def _one(p: Path):
        out_txt = output_dir / f"{p.stem}.txt"  # ← 파일명 동일 보장
        convert_json_to_txt(p, out_txt, imgw, imgh)
        print(f"[OK] {p.name} → {out_txt}")

    if input_path.is_file() and input_path.suffix.lower() == ".json":
        _one(input_path)
    else:
        for jp in input_path.rglob("*.json"):
            _one(jp)

# 스크립트로 직접 실행할 때만 동작 (모듈 임포트 시에는 실행 안 됨)
if __name__ == "__main__":
    # 예시: 아래 경로를 네 환경에 맞게 수정해서 테스트
    input_path = INPUT
    output_path = OUTPUT
    convert_path(input_path, output_path, IMGW, IMGH)
