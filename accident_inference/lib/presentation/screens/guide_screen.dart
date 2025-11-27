import 'package:flutter/material.dart';
import 'dart:ui';
import 'package:permission_handler/permission_handler.dart';

class GuideScreen extends StatefulWidget {
  const GuideScreen({Key? key}) : super(key: key);

  @override
  _GuideScreenState createState() => _GuideScreenState();
}

class _GuideScreenState extends State<GuideScreen> with SingleTickerProviderStateMixin {
  final Color _primary = const Color(0xFF1565C0); // match main primary
  final Color _navy = const Color(0xFF0D1B2A);

  late AnimationController _controller;
  late Animation<double> _iconAnimation;
  late Animation<double> _titleAnimation;
  late Animation<double> _subtitleAnimation;
  bool _showScrollHint = true;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _iconAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: const Interval(0.0, 0.5, curve: Curves.easeOut)),
    );

    _titleAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: const Interval(0.4, 0.8, curve: Curves.easeOut)),
    );

    _subtitleAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: const Interval(0.7, 1.0, curve: Curves.easeOut)),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<bool> _ensureCameraPermission() async {
    var status = await Permission.camera.status;
    if (status.isGranted) return true;

    // 안내 다이얼로그 (요청 전 사전 설명)
    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('카메라 권한 요청'),
        content: const Text('실시간 감지를 위해 카메라 권한이 필요합니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('확인')),
        ],
      ),
    );

    status = await Permission.camera.request();
    if (status.isGranted) return true;

    if (status.isPermanentlyDenied) {
      final go = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('권한이 비활성화됨'),
          content: const Text('설정 > 앱 권한에서 카메라 권한을 허용해 주세요.'),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('취소')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('설정 열기')),
          ],
        ),
      );
      if (go == true) {
        await openAppSettings();
      }
    }
    return false;
  }

  Widget _buildGlassmorphicButton(BuildContext context) {
    return GestureDetector(
      onTap: () async {
        final ok = await _ensureCameraPermission();
        if (!ok) return;
        Navigator.pushNamed(
          context,
          '/camera',
          arguments: const {'autoStart': true},
        );
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(40),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 14),
            decoration: BoxDecoration(
              color: _primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(40),
              border: Border.all(color: _primary.withOpacity(0.35), width: 1.2),
              boxShadow: [
                BoxShadow(
                  color: _primary.withOpacity(0.18),
                  offset: const Offset(0, 4),
                  blurRadius: 10,
                  spreadRadius: 1,
                ),
              ],
            ),
            alignment: Alignment.center,
            child: Text(
              '시작하기',
              style: TextStyle(
                color: _primary,
                fontWeight: FontWeight.bold,
                fontSize: 20,
                letterSpacing: 1.1,
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // 배경색: 메인 화면과 통일된 Dark Theme
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 10),
                      // 1. Header Section
                      const Text(
                        '안전한 주행을 위한\n체크리스트',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          height: 1.3,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        '정확한 감지와 안전을 위해 아래 항목을 확인해주세요.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 32),

                      // 2. Checklist Section (Cards)
                      _ChecklistCard(
                        icon: Icons.stay_current_landscape_rounded,
                        title: '가로 거치 고정',
                        subtitle: '스마트폰이 흔들리지 않도록\n차량 거치대에 단단히 고정하세요.',
                        accentColor: const Color(0xFF60A5FA),
                      ),
                      const SizedBox(height: 16),
                      _ChecklistCard(
                        icon: Icons.cleaning_services_rounded,
                        title: '렌즈 청결 확인',
                        subtitle: '카메라 렌즈를 닦아 인식률을 높이세요.\n이물질은 오작동의 원인이 됩니다.',
                        accentColor: const Color(0xFFF59E0B),
                      ),
                      const SizedBox(height: 16),
                      _ChecklistCard(
                        icon: Icons.visibility_rounded,
                        title: '시야 확보',
                        subtitle: '차선과 표지판이 잘 보이도록\n카메라 각도를 조절해주세요.',
                        accentColor: const Color(0xFF34D399),
                      ),
                      const SizedBox(height: 16),
                      _ChecklistCard(
                        icon: Icons.do_not_touch_rounded,
                        title: '조작 주의',
                        subtitle: '운전 중 조작은 매우 위험합니다.\n반드시 정차 후 설정하세요.',
                        accentColor: const Color(0xFFFB7185),
                      ),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ),
            
            // 3. Bottom Action Button
            Container(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
              decoration: BoxDecoration(
                color: const Color(0xFF121212),
                border: Border(top: BorderSide(color: Colors.white.withOpacity(0.1))),
              ),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () async {
                    // TODO: 카메라 권한 요청 및 네비게이션 로직
                    // Navigator.pushReplacementNamed(context, '/camera');
                    final ok = await _ensureCameraPermission();
                    if (!ok) return;
                    Navigator.pushNamed(
                      context,
                      '/camera',
                      arguments: const {'autoStart': true},
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF60A5FA), // 메인 액센트 컬러
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: const Text(
                    '확인 및 주행 시작',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 하위 위젯 컴포넌트 ---

class _ChecklistCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color accentColor;

  const _ChecklistCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E), // 카드 배경색
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withOpacity(0.05),
          width: 1,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: accentColor.withOpacity(0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: accentColor, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}


class _AnimatedScrollHintArrow extends StatefulWidget {
  @override
  State<_AnimatedScrollHintArrow> createState() => _AnimatedScrollHintArrowState();
}

class _AnimatedScrollHintArrowState extends State<_AnimatedScrollHintArrow> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _offsetAnimation;
  late Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1100),
      vsync: this,
    )..repeat(reverse: true);
    _offsetAnimation = Tween<double>(begin: 0, end: 18).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    _opacityAnimation = Tween<double>(begin: 1, end: 0.4).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Color _navy = const Color(0xFF0D1B2A);
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Opacity(
          opacity: _opacityAnimation.value,
          child: Transform.translate(
            offset: Offset(0, _offsetAnimation.value),
            child: Icon(
              Icons.keyboard_arrow_down,
              size: 48,
              color: _navy.withOpacity(0.75),
            ),
          ),
        );
      },
    );
  }
}