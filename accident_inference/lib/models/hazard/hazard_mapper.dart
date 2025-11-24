// frontend/example/lib/models/hazard/hazard_mapper.dart

// import 'package:ultralytics_yolo/yolo_result.dart'; // ✅ 패키지 import로 고정
import 'hazard_class.dart';
import 'hazard_detection.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';
import 'package:ultralytics_yolo/yolo_result.dart'; 
// ...
/// YOLOResult(플러그인 출력)을
/// 우리 프로젝트 도메인(HazardClass/HazardDetection)으로 변환하는 매퍼.
///
/// 핵심:
/// - YOLO className 문자열을 HazardClass로 매핑
/// - confidence / bbox / normalizedBox 유지
class HazardMapper {
  /// YOLO className(모델 학습 라벨) -> HazardClass
  /// 학습 라벨명에 맞춰 여기만 수정하면 됨.
  static HazardClass? mapClassName(String? raw) {
    if (raw == null) return null;
    final k = raw.trim().toLowerCase();

    // ---- 별칭/오타 방어 ----
    if (k == 'animal' || k == 'animals' || k.contains('animal')) {
      return HazardClass.animal;
    }
    if (k == 'person' || k == 'human' || k.contains('person')) {
      return HazardClass.person;
    }
    if (k == 'garbagebag' ||
        k == 'garbage_bag' ||
        k == 'garbage bag' ||
        k.contains('garbage')) {
      return HazardClass.garbageBag;
    }
    if (k == 'constructionsign' ||
        k == 'construction_sign' ||
        k == 'construction sign' ||
        k.contains('construction') ||
        k.contains('parking prohibited')) {
      return HazardClass.constructionSign;
    }
    if (k == 'box' || k.contains('box')) {
      return HazardClass.box;
    }
    if (k == 'stone' || k == 'rock' || k.contains('stone')) {
      return HazardClass.stone;
    }
    if (k == 'pothole' || k.contains('pothole')) {
      return HazardClass.pothole;
    }
    if (k == 'car' || k.contains('car')) {
      return HazardClass.car;
    }
    if (k == 'truck' || k.contains('truck')) {
      return HazardClass.truck;
    }
    if (k == 'bus' || k.contains('bus')) {
      return HazardClass.bus;
    }

    return null; // 모르는 라벨이면 스킵
  }

  /// YOLOResult 1개 -> HazardDetection 1개
  static HazardDetection? fromYOLOResult(
    YOLOResult r, {
    required int tUs,
    double minScore = 0.25,
  }) {
    final hazard = mapClassName(r.className);
    if (hazard == null) return null;
    if (r.confidence < minScore) return null;

    return HazardDetection(
      hazard: hazard,
      score: r.confidence,
      bbox: r.boundingBox,
      nbox: r.normalizedBox,
      tUs: tUs,
    );
  }

  /// YOLOResult 리스트 -> HazardDetection 리스트
  static List<HazardDetection> fromResults(
    List<YOLOResult> results, {
    required int tUs,
    double minScore = 0.25,
  }) {
    final out = <HazardDetection>[];
    for (final r in results) {
      final h = fromYOLOResult(r, tUs: tUs, minScore: minScore);
      if (h != null) out.add(h);
    }
    return out;
  }
}
