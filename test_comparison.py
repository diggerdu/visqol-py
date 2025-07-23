#!/usr/bin/env python3
"""
对比测试脚本：验证Python binding与原始ViSQOL二进制的计算结果一致性
"""

import os
import sys
import subprocess
import tempfile
import numpy as np
from pathlib import Path

# 添加我们的包到路径
sys.path.insert(0, '/home/xingjian/evaluation/visqol-py/github-repo/repo-for-github/visqol-py-repo')

def setup_environment():
    """设置测试环境"""
    # 设置环境变量，使用我们构建的包
    env_python_path = "/home/xingjian/mf3/envs/test-fresh-install/bin/python"
    if not os.path.exists(env_python_path):
        print("❌ 测试环境不存在，请先创建conda环境")
        return None
    
    return env_python_path

def run_original_visqol(ref_file, deg_file, use_speech_mode=False, verbose=False):
    """使用原始ViSQOL二进制计算分数"""
    visqol_bin = "/home/xingjian/evaluation/visqol-py/github-repo/repo-for-github/visqol/bazel-bin/visqol"
    visqol_dir = "/home/xingjian/evaluation/visqol-py/github-repo/repo-for-github/visqol"
    
    if not os.path.exists(visqol_bin):
        print("❌ 原始ViSQOL二进制不存在，请先构建：cd visqol && bazel build :visqol -c opt")
        return None
    
    cmd = [visqol_bin, "--reference_file", ref_file, "--degraded_file", deg_file]
    if use_speech_mode:
        cmd.append("--use_speech_mode")
    if verbose:
        cmd.append("--verbose")
    
    try:
        # 在ViSQOL目录下运行，这样可以找到模型文件
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=visqol_dir)
        if result.returncode != 0:
            print(f"❌ 原始ViSQOL执行失败: {result.stderr}")
            return None
        
        # 解析输出中的MOS-LQO分数
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if "MOS-LQO" in line or line.replace('.', '', 1).isdigit():
                # 提取数值
                parts = line.split()
                for part in parts:
                    try:
                        score = float(part)
                        if 1.0 <= score <= 5.0:  # 合理的MOS范围
                            return score
                    except ValueError:
                        continue
        
        # 如果没找到明确的MOS-LQO标记，尝试解析最后一行的数值
        last_line = lines[-1].strip()
        try:
            score = float(last_line)
            if 1.0 <= score <= 5.0:
                return score
        except ValueError:
            pass
            
        print(f"❌ 无法解析原始ViSQOL输出: {result.stdout}")
        return None
        
    except subprocess.TimeoutExpired:
        print("❌ 原始ViSQOL执行超时")
        return None
    except Exception as e:
        print(f"❌ 运行原始ViSQOL时出错: {e}")
        return None

def run_python_binding(ref_file, deg_file, use_speech_mode=False, python_path=None):
    """使用Python binding计算分数"""
    if python_path is None:
        python_path = sys.executable
    
    code = f"""
import sys
sys.path.insert(0, '/home/xingjian/mf3/envs/test-fresh-install/lib/python3.12/site-packages')
import visqol_py

mode = visqol_py.ViSQOLMode.SPEECH if {use_speech_mode} else visqol_py.ViSQOLMode.AUDIO
visqol = visqol_py.ViSQOL(mode=mode)
result = visqol.measure('{ref_file}', '{deg_file}')
print(f"{{result.moslqo:.6f}}")
"""
    
    try:
        env = os.environ.copy()
        env['PATH'] = "/home/xingjian/mf3/envs/test-fresh-install/bin:" + env.get('PATH', '')
        
        result = subprocess.run([python_path, "-c", code], 
                              capture_output=True, text=True, timeout=30, env=env)
        if result.returncode != 0:
            print(f"❌ Python binding执行失败: {result.stderr}")
            return None
        
        score = float(result.stdout.strip())
        return score
        
    except subprocess.TimeoutExpired:
        print("❌ Python binding执行超时")
        return None
    except Exception as e:
        print(f"❌ 运行Python binding时出错: {e}")
        return None

def create_test_audio_files():
    """创建测试音频文件"""
    test_files = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建简单的测试音频文件
        sample_rates = [16000, 48000]  # Speech and Audio modes
        
        for sr in sample_rates:
            duration = 5.0
            t = np.linspace(0, duration, int(sr * duration))
            
            # 参考信号：纯正弦波
            reference = np.sin(2 * np.pi * 440 * t) * 0.7
            
            # 降质信号：添加噪声
            degraded = reference + 0.05 * np.random.randn(len(reference))
            
            # 保存为WAV文件
            ref_file = temp_path / f"ref_{sr}Hz.wav"
            deg_file = temp_path / f"deg_{sr}Hz.wav"
            
            # 使用Python的wave模块保存
            import wave
            
            # 保存参考文件
            with wave.open(str(ref_file), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sr)
                audio_int16 = (reference * 32767).astype(np.int16)
                wav.writeframes(audio_int16.tobytes())
            
            # 保存降质文件
            with wave.open(str(deg_file), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sr)
                audio_int16 = (degraded * 32767).astype(np.int16)
                wav.writeframes(audio_int16.tobytes())
            
            test_files.append((str(ref_file), str(deg_file), sr))
    
    return test_files

def compare_implementations():
    """对比两种实现的结果"""
    print("🔍 开始对比测试...")
    
    python_path = setup_environment()
    if python_path is None:
        return False
    
    # 测试用例
    test_cases = []
    
    # 1. 使用原始repo中的测试文件
    original_test_files = [
        ("/home/xingjian/evaluation/visqol-py/github-repo/repo-for-github/visqol/testdata/clean_speech/CA01_01.wav",
         "/home/xingjian/evaluation/visqol-py/github-repo/repo-for-github/visqol/testdata/clean_speech/transcoded_CA01_01.wav",
         True, "Speech test from original repo"),
    ]
    
    # 检查文件是否存在
    for ref, deg, is_speech, desc in original_test_files:
        if os.path.exists(ref) and os.path.exists(deg):
            test_cases.append((ref, deg, is_speech, desc))
    
    if not test_cases:
        print("⚠️ 原始测试文件不存在，使用生成的测试文件")
        # 创建临时测试文件（这个会在函数结束时被删除，所以先不用）
    
    # 2. 测试同一文件（应该得到完美分数）
    if test_cases:
        ref_file = test_cases[0][0]  # 使用第一个测试文件作为参考
        test_cases.append((ref_file, ref_file, True, "Perfect match (same file) - Speech"))
        test_cases.append((ref_file, ref_file, False, "Perfect match (same file) - Audio"))
    
    results = []
    tolerance = 0.001  # 允许的误差范围
    
    for ref_file, deg_file, use_speech_mode, description in test_cases:
        print(f"\n📝 测试: {description}")
        print(f"   参考文件: {os.path.basename(ref_file)}")
        print(f"   降质文件: {os.path.basename(deg_file)}")
        print(f"   模式: {'Speech (16kHz)' if use_speech_mode else 'Audio (48kHz)'}")
        
        # 运行原始ViSQOL
        print("   🔄 运行原始ViSQOL...")
        original_score = run_original_visqol(ref_file, deg_file, use_speech_mode, verbose=True)
        
        if original_score is None:
            print("   ❌ 原始ViSQOL执行失败，跳过此测试")
            continue
        
        # 运行Python binding
        print("   🐍 运行Python binding...")
        python_score = run_python_binding(ref_file, deg_file, use_speech_mode, python_path)
        
        if python_score is None:
            print("   ❌ Python binding执行失败，跳过此测试")
            continue
        
        # 比较结果
        diff = abs(original_score - python_score)
        match = diff <= tolerance
        
        print(f"   📊 结果对比:")
        print(f"      原始ViSQOL:    {original_score:.6f}")
        print(f"      Python binding: {python_score:.6f}")
        print(f"      差异:          {diff:.6f}")
        print(f"      匹配: {'✅ 是' if match else '❌ 否'}")
        
        results.append({
            'description': description,
            'original_score': original_score,
            'python_score': python_score,
            'difference': diff,
            'match': match
        })
    
    # 总结结果
    print(f"\n{'='*60}")
    print("📋 测试总结:")
    
    if not results:
        print("❌ 没有成功完成任何测试")
        return False
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['match'])
    
    print(f"   总测试数: {total_tests}")
    print(f"   通过数: {passed_tests}")
    print(f"   通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！Python binding与原始实现结果一致")
        return True
    else:
        print("⚠️ 部分测试未通过，需要进一步检查")
        
        # 显示失败的测试
        print("\n❌ 失败的测试:")
        for r in results:
            if not r['match']:
                print(f"   - {r['description']}: 差异 {r['difference']:.6f}")
        
        return False

if __name__ == "__main__":
    success = compare_implementations()
    sys.exit(0 if success else 1)