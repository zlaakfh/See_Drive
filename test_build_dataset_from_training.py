# test_build_dataset_from_training.py
# - Training/01.원천데이터/*.png  ↔  Training/02.라벨링데이터/*.json
#   을 파일명(stem)으로 매칭해서 train/valid/test로 분할해
#   OUT_ROOT/<split>/images/*.png, OUT_ROOT/<split>/labels/*.txt 구조로 생성
#
# ※ convert_json_to_yoloseg.py 를 같은 폴더에 두고 import 합니다.

from pathlib import Path
import shutil, random
from test_convert_json_to_yoloseg import convert_json_to_txt, IMGW, IMGH

# ===== 사용자 설정 =====
TRAINING_ROOT = Path("/home/elicer/sesac_dacon/_unzip/181.실내_자율주차용_데이터/01-1.정식개방데이터/Validation/")
OUT_ROOT      = Path("/home/elicer/sesac_dacon/data")

TRAIN_RATIO = 0.7
VALID_RATIO = 0.2
TEST_FROM_VALIDATION = False     # True면 valid=0, test=VALID_RATIO
RANDOM_SEED = 42

def _index_by_stem(root: Path, pattern: str):
    """root에서 pattern으로 찾은 파일들을 stem → Path로 인덱싱"""
    idx = {}
    for p in root.rglob(pattern):
        if not p.is_file(): continue
        stem = p.stem
        # 중복 stem이 존재하면 더 짧은 경로를 우선 (임의 충돌 해소)
        if stem not in idx or len(str(p)) < len(str(idx[stem])):
            idx[stem] = p
    return idx

def build_pairs(training_root: Path):
    img_root  = training_root / "01.원천데이터"
    json_root = training_root / "02.라벨링데이터"

    img_idx  = _index_by_stem(img_root,  "*.png")
    json_idx = _index_by_stem(json_root, "*.json")

    stems_img, stems_json = set(img_idx.keys()), set(json_idx.keys())
    common = sorted(stems_img & stems_json)

    only_img  = sorted(stems_img  - stems_json)
    only_json = sorted(stems_json - stems_img)

    if only_img:
        print(f"[WARN] 라벨(JSON) 누락 {len(only_img)}개 예: {only_img[:5]}")
    if only_json:
        print(f"[WARN] 이미지(PNG) 누락 {len(only_json)}개 예: {only_json[:5]}")

    pairs = [(s, img_idx[s], json_idx[s]) for s in common]
    print(f"[INFO] 매칭된 페어 수: {len(pairs)} (png↔json)")
    return pairs

def split_pairs(pairs, train_ratio, valid_ratio, use_valid_as_test, seed=42):
    rnd = random.Random(seed)
    pairs = list(pairs)
    rnd.shuffle(pairs)

    n = len(pairs)
    if use_valid_as_test:
        n_train = round(n * train_ratio)
        n_test  = round(n * valid_ratio)
        n_valid = 0
    else:
        n_train = round(n * train_ratio)
        n_valid = round(n * valid_ratio)
        n_test  = max(0, n - n_train - n_valid)

    if n_train + n_valid + n_test != n:
        n_test = n - n_train - n_valid

    return pairs[:n_train], pairs[n_train:n_train+n_valid], pairs[n_train+n_valid:n_train+n_valid+n_test]

def _copy_image(src_img: Path, dst_img: Path):
    dst_img.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_img, dst_img)

def _export_split(pairs, split_name: str, out_root: Path, imgw=IMGW, imgh=IMGH):
    img_dir = out_root / split_name / "images"
    lbl_dir = out_root / split_name / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    for stem, png_path, json_path in pairs:
        dst_png = img_dir / f"{stem}.png"   # 파일명 동일
        dst_txt = lbl_dir / f"{stem}.txt"   # 파일명 동일
        _copy_image(png_path, dst_png)
        convert_json_to_txt(json_path, dst_txt, imgw, imgh)  # 변환해서 저장
    print(f"[OK] {split_name}: {len(pairs)}개 내보냄")

def main():
    pairs = build_pairs(TRAINING_ROOT)
    train, valid, test = split_pairs(pairs, TRAIN_RATIO, VALID_RATIO, TEST_FROM_VALIDATION, RANDOM_SEED)

    print(f"[SPLIT] train={len(train)}, valid={len(valid)}, test={len(test)}, total={len(pairs)}")

    if train: _export_split(train, "train", OUT_ROOT, IMGW, IMGH)
    if valid: _export_split(valid, "valid", OUT_ROOT, IMGW, IMGH)
    if test:  _export_split(test,  "test",  OUT_ROOT, IMGW, IMGH)

    print("\nDone. Dataset is ready at:", OUT_ROOT)

if __name__ == "__main__":
    main()
