// example/lib/models/hazard/hazard_detection.dart
import 'dart:ui';
import 'hazard_class.dart';

/// Vision(YOLO)로부터 나온 "위험요소 1개"
class HazardDetection {
  final HazardClass hazard;
  final double score;   // confidence
  final Rect bbox;      // pixel bbox
  final Rect nbox;      // normalized bbox (0~1)
  final int tUs;        // timestamp (microseconds)

  const HazardDetection({
    required this.hazard,
    required this.score,
    required this.bbox,
    required this.nbox,
    required this.tUs,
  });

  /// ✅ AccidentDecision.toMap()에서 쓰는 직렬화 함수
  Map<String, dynamic> toMap() => {
        "hazard": hazard.label,
        "score": score,
        "bbox": {
          "l": bbox.left,
          "t": bbox.top,
          "r": bbox.right,
          "b": bbox.bottom,
        },
        "nbox": {
          "l": nbox.left,
          "t": nbox.top,
          "r": nbox.right,
          "b": nbox.bottom,
        },
        "t_us": tUs,
      };

  @override
  String toString() =>
      "HazardDetection(hazard=${hazard.label}, score=$score, bbox=$bbox)";
}
