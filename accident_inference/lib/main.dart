import 'dart:async'; // StreamSubscription 사용을 위해 추가
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart'; // 자이로센서 패키지 추가
import 'package:fl_chart/fl_chart.dart'; // 차트 패키지 추가

// (main 함수 및 CameraApp 클래스는 기존과 동일)

late List<CameraDescription> _cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  _cameras = await availableCameras();
  runApp(const CameraApp());
}

class CameraApp extends StatefulWidget {
  /// Default Constructor
  const CameraApp({super.key});

  @override
  State<CameraApp> createState() => _CameraAppState();
}

class _CameraAppState extends State<CameraApp> {
  late CameraController controller;
  // 자이로센서 관련 변수
  List<double> gyroX = []; // X축 데이터를 저장할 리스트
  List<double> gyroY = [];
  List<double> gyroZ = [];
  var maxDataLen = 50;

  StreamSubscription? _gyroscopeSubscription; // 센서 구독 관리

  @override
  void initState() {
    super.initState();

    // 1. 카메라 초기화 (기존 코드와 동일)
    controller = CameraController(_cameras[0], ResolutionPreset.medium); // 해상도를 낮춰 성능 확보
    controller.initialize().then((_) {
      if (!mounted) return;
      setState(() {});
    }).catchError((e) {/* 에러 처리 */});

    // accelerometerEventStream
    _gyroscopeSubscription = accelerometerEventStream(samplingPeriod: Duration(milliseconds: 50)).listen(
          (AccelerometerEvent event) {
        // 화면이 마운트된 상태에서만 업데이트
        if (mounted) {
          setState(() {
            // 새 X축 각속도 값을 리스트에 추가합니다.
            // 그래프의 시각적 안정성을 위해, 최신 50개 정도의 데이터만 유지합니다.
            gyroX.add(event.x);
            if (gyroX.length > maxDataLen) {
              gyroX.removeAt(0); // 가장 오래된 데이터 제거
            }

            gyroY.add(event.y);
            if (gyroY.length > maxDataLen) {
              gyroY.removeAt(0);
            }

            gyroZ.add(event.z);
            if (gyroZ.length > maxDataLen) {
              gyroZ.removeAt(0);
            }

          });
        }
      },
      onError: (error) {
        // 에러 처리
        print("자이로센서 에러: $error");
      },
      cancelOnError: true,
    );
    // 2. 자이로스코프 센서 구독 시작
    // _gyroscopeSubscription = gyroscopeEventStream(samplingPeriod: Duration(milliseconds: 50)).listen(
    //       (GyroscopeEvent event) {
    //     // 화면이 마운트된 상태에서만 업데이트
    //     if (mounted) {
    //       setState(() {
    //         // 새 X축 각속도 값을 리스트에 추가합니다.
    //         // 그래프의 시각적 안정성을 위해, 최신 50개 정도의 데이터만 유지합니다.
    //         gyroX.add(event.x);
    //         if (gyroX.length > maxDataLen) {
    //           gyroX.removeAt(0); // 가장 오래된 데이터 제거
    //         }
    //
    //         gyroY.add(event.y);
    //         if (gyroY.length > maxDataLen) {
    //           gyroY.removeAt(0);
    //         }
    //
    //         gyroZ.add(event.z);
    //         if (gyroZ.length > maxDataLen) {
    //           gyroZ.removeAt(0);
    //         }
    //
    //       });
    //     }
    //   },
    //   onError: (error) {
    //     // 에러 처리
    //     print("자이로센서 에러: $error");
    //   },
    //   cancelOnError: true,
    // );
  }

  @override
  void dispose() {
    controller.dispose();
    _gyroscopeSubscription?.cancel(); // 센서 구독 해제
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!controller.value.isInitialized) {
      return Container(
        color: Colors.black,
        child: const Center(child: CircularProgressIndicator()),
      );
    }

    // 전체 화면을 세로로 나누기 위해 Column 위젯 사용
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text("Camera & acceler")),
        body: Column(
          children: <Widget>[
            // 1. 상단 절반: 카메라 화면
            Expanded(
              flex: 1, // 높이 비율 1 (전체의 절반)
              child: CameraPreview(controller),
            ),

            // 2. 하단 절반: 자이로센서 그래프
            Expanded(
              flex: 1, // 높이 비율 1 (전체의 절반)
              child: GyroscopeGraph(
                  gyroX: gyroX,
                  gyroY: gyroY,
                  gyroZ: gyroZ
              ), // 별도의 그래프 위젯 호출

            ),
          ],
        ),
      ),
    );
  }
}

class GyroscopeGraph extends StatelessWidget {
  final List<double> gyroX; // X축 각속도 데이터
  final List<double> gyroY;
  final List<double> gyroZ;

  const GyroscopeGraph({
    required this.gyroX,
    required this.gyroY,
    required this.gyroZ,
    super.key
  });

  @override
  Widget build(BuildContext context) {

    final List<FlSpot> spotsX = List.generate(gyroX.length, (index) {
      return FlSpot(index.toDouble(), gyroX[index]);
    });

    final List<FlSpot> spotsY = List.generate(gyroY.length, (index) {
      return FlSpot(index.toDouble(), gyroY[index]);
    });

    final List<FlSpot> spotsZ = List.generate(gyroZ.length, (index) {
      return FlSpot(index.toDouble(), gyroZ[index]);
    });

    return Padding(
      padding: const EdgeInsets.all(12.0),
      child: LineChart(
        LineChartData(
          // 그래프 제목 및 축 설정
          titlesData: const FlTitlesData(
            topTitles: AxisTitles(axisNameWidget: Text('acceler X-red, Y-blue, Z-green', style: TextStyle(fontWeight: FontWeight.bold))),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), // X축 제목 숨김
          ),
          gridData: const FlGridData(show: true),
          borderData: FlBorderData(show: true, border: Border.all(color: const Color(0xff37434d), width: 1)),

          // Y축 범위 설정 (예: -10.0 ~ 10.0)
          minY: -10.0,
          maxY: 10.0,

          lineBarsData: [
            LineChartBarData(
              spots: spotsX,
              isCurved: true,
              color: Colors.redAccent,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: const FlDotData(show: false),
            ),
            LineChartBarData(
              spots: spotsY,
              isCurved: true,
              color: Colors.blueAccent,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: const FlDotData(show: false),
            ),
            LineChartBarData(
              spots: spotsZ,
              isCurved: true,
              color: Colors.greenAccent,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: const FlDotData(show: false),
            ),
          ],
        ),
      ),
    );
  }
}