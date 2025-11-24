// example/lib/models/accidents/accident_decision.dart
import '../hazard/hazard_detection.dart';
import 'accident_type.dart';
import 'accident_level.dart';

class AccidentDecision {
  final int tUs;
  final AccidentType type;
  final AccidentLevel level;
  final String reason;
  final List<HazardDetection> hazards;

  // 참고용 수치
  final double linAccMag;   // |linear acc|
  final double gyroMag;     // |gyro|

  const AccidentDecision({
    required this.tUs,
    required this.type,
    required this.level,
    required this.reason,
    required this.hazards,
    required this.linAccMag,
    required this.gyroMag,
  });

  Map<String, dynamic> toMap() => {
    "t_us": tUs,
    "type": type.label,
    "level": level.label,
    "reason": reason,
    "linAccMag": linAccMag,
    "gyroMag": gyroMag,
    "hazards": hazards.map((h) => h.toMap()).toList(),
  };

  @override
  String toString() =>
      "AccidentDecision(type=${type.label}, level=${level.label}, "
      "linAccMag=$linAccMag, gyroMag=$gyroMag, hazards=${hazards.length})";
}
