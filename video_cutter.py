#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIアバター動画無音削除・倍速ツール（設定可能版）
基本検出またはSpleeter AI音声分離から選択可能
"""

import os
import sys
import subprocess
import librosa
import numpy as np
from moviepy.editor import VideoFileClip
from pydub import AudioSegment, silence
import soundfile as sf

# ==================== 設定エリア ====================
# ここの設定を変更して使用してください

SETTINGS = {
    # 処理方法: "basic" (基本検出) または "spleeter" (AI音声分離)
    "processing_mode": "basic",
    
    # 最小無音時間（秒）: この時間未満の無音は無視
    "min_silence_duration": 1.0,
    
    # マージン（秒）: 無音部分の前後に残す時間
    "margin": 0.5,
    
    # 閾値: "auto" (自動設定) または手動指定 (-30, -35, -40など)
    "threshold": "auto",
    
    # 倍速設定
    "speed_factor": 1.15,
    
    # 入出力ファイル名 (コマンドライン引数で上書きされます)
    "input_file": "",
    "output_file": ""
}

# ==================== 処理関数 ====================

def determine_auto_threshold(audio_level):
    """音声レベルに基づいて最適な閾値を自動設定"""
    if audio_level >= -25:
        return -35
    elif audio_level >= -30:
        return -40
    else:
        return -45

def extract_audio_from_video(video_path, output_path="temp_audio.wav"):
    """動画から音声を抽出"""
    print(f"動画から音声を抽出中: {video_path}")
    
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_path, logger=None)
        video.close()
        print(f"音声抽出完了: {output_path}")
        return output_path
    except Exception as e:
        print(f"音声抽出エラー: {e}")
        return None

def separate_audio_with_spleeter(audio_path):
    """Spleeterで音声分離"""
    print("Spleeterで音声分離中...")
    
    try:
        from spleeter.separator import Separator
        
        separator = Separator('spleeter:2stems')
        waveform, sample_rate = librosa.load(audio_path, sr=44100, mono=False)
        
        if len(waveform.shape) == 1:
            waveform = np.stack([waveform, waveform])
        
        prediction = separator.separate(waveform.T)
        
        vocals_path = "separated_vocals.wav"
        sf.write(vocals_path, prediction['vocals'], sample_rate)
        
        print(f"音声分離完了: {vocals_path}")
        return vocals_path
        
    except ImportError:
        print("Spleeterがインストールされていません")
        print("pip install spleeter でインストールしてください")
        return None
    except Exception as e:
        print(f"音声分離エラー: {e}")
        return None

def detect_silence_with_settings(audio_path, settings):
    """設定に基づいて無音検出"""
    print(f"無音検出中: {audio_path}")
    
    try:
        audio = AudioSegment.from_wav(audio_path)
        audio_level = audio.dBFS
        
        # 閾値の決定
        if settings["threshold"] == "auto":
            threshold = determine_auto_threshold(audio_level)
            print(f"自動閾値設定: {threshold}dB (音声レベル: {audio_level:.1f}dB)")
        else:
            threshold = settings["threshold"]
            print(f"手動閾値設定: {threshold}dB")
        
        print(f"最小無音時間: {settings['min_silence_duration']}秒")
        print(f"マージン: {settings['margin']}秒")
        
        # 無音検出
        silent_ranges = silence.detect_silence(
            audio, 
            min_silence_len=int(settings["min_silence_duration"] * 1000),
            silence_thresh=threshold
        )
        
        # 秒単位に変換
        silent_ranges_sec = [(start/1000, end/1000) for start, end in silent_ranges]
        
        print(f"検出結果: {len(silent_ranges_sec)}個の無音部分")
        
        return silent_ranges_sec, audio_level, threshold
        
    except Exception as e:
        print(f"無音検出エラー: {e}")
        return [], None, None

def generate_keep_segments_with_margin(silent_ranges, total_duration, margin):
    """マージン付きで保持セグメントを計算"""
    keep_segments = []
    
    if not silent_ranges:
        return [(0, total_duration)]
    
    # マージン付きの無音範囲を計算
    padded_silent_ranges = []
    for start, end in silent_ranges:
        padded_start = max(0, start + margin)
        padded_end = min(total_duration, end - margin)
        
        if padded_end > padded_start:
            padded_silent_ranges.append((padded_start, padded_end))
    
    if not padded_silent_ranges:
        return [(0, total_duration)]
    
    # 保持セグメントを計算
    if padded_silent_ranges[0][0] > 0:
        keep_segments.append((0, padded_silent_ranges[0][0]))
    
    for i in range(len(padded_silent_ranges) - 1):
        start = padded_silent_ranges[i][1]
        end = padded_silent_ranges[i + 1][0]
        if end > start:
            keep_segments.append((start, end))
    
    if padded_silent_ranges[-1][1] < total_duration:
        keep_segments.append((padded_silent_ranges[-1][1], total_duration))
    
    return keep_segments

def create_ffmpeg_filter(keep_segments, speed_factor):
    """FFmpegフィルターコマンドを生成"""
    if not keep_segments:
        return "", "", ""
    
    filters = []
    
    for i, (start, end) in enumerate(keep_segments):
        filters.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}];")
        filters.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}];")
    
    video_inputs = "".join([f"[v{i}]" for i in range(len(keep_segments))])
    audio_inputs = "".join([f"[a{i}]" for i in range(len(keep_segments))])
    
    filters.append(f"{video_inputs}concat=n={len(keep_segments)}:v=1:a=0[vout];")
    filters.append(f"{audio_inputs}concat=n={len(keep_segments)}:v=0:a=1[aout];")
    
    if speed_factor != 1.0:
        filters.append(f"[vout]setpts=PTS/{speed_factor}[vfinal];")
        filters.append(f"[aout]atempo={speed_factor}[afinal]")
        return "".join(filters), "[vfinal]", "[afinal]"
    else:
        return "".join(filters), "[vout]", "[aout]"

def process_video_with_ffmpeg(input_path, output_path, keep_segments, speed_factor):
    """FFmpegで動画を処理"""
    print(f"FFmpegで動画処理中...")
    print(f"入力: {input_path}")
    print(f"出力: {output_path}")
    print(f"倍速: {speed_factor}x")
    
    try:
        if not keep_segments:
            print("保持するセグメントがありません")
            return False
        
        filter_complex, video_map, audio_map = create_ffmpeg_filter(keep_segments, speed_factor)
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-filter_complex', filter_complex,
            '-map', video_map,
            '-map', audio_map,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',
            output_path
        ]
        
        print(f"セグメント数: {len(keep_segments)}個")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"動画処理完了: {output_path}")
            return True
        else:
            print(f"FFmpegエラー: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"動画処理エラー: {e}")
        return False

def save_detailed_report(filename, settings, silent_ranges, keep_segments, total_duration, audio_level, threshold):
    """詳細レポートを保存"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("AIアバター動画処理結果レポート\n")
            f.write("=" * 60 + "\n\n")
            
            # 設定情報
            f.write("処理設定:\n")
            f.write(f"  処理方法: {settings['processing_mode']}\n")
            f.write(f"  最小無音時間: {settings['min_silence_duration']}秒\n")
            f.write(f"  マージン: {settings['margin']}秒\n")
            f.write(f"  閾値設定: {settings['threshold']}\n")
            f.write(f"  実際の閾値: {threshold}dB\n")
            f.write(f"  倍速: {settings['speed_factor']}x\n")
            f.write(f"  音声レベル: {audio_level:.1f}dB\n\n")
            
            # 検出結果
            total_silence_time = sum(end - start for start, end in silent_ranges)
            f.write("無音検出結果:\n")
            f.write(f"  検出された無音: {len(silent_ranges)}個\n")
            f.write(f"  無音時間合計: {total_silence_time:.2f}秒\n\n")
            
            if silent_ranges:
                f.write("検出された無音詳細:\n")
                for i, (start, end) in enumerate(silent_ranges, 1):
                    duration = end - start
                    padded_start = max(0, start + settings['margin'])
                    padded_end = min(total_duration, end - settings['margin'])
                    actual_cut = max(0, padded_end - padded_start)
                    f.write(f"  {i:2d}: {start:6.2f}秒-{end:6.2f}秒 ({duration:.2f}秒) → 実削除: {actual_cut:.2f}秒\n")
            
            f.write("\n" + "-" * 40 + "\n\n")
            
            # 処理結果
            total_keep_time = sum(end - start for start, end in keep_segments)
            final_duration = total_keep_time / settings['speed_factor']
            compression_ratio = (total_duration - final_duration) / total_duration * 100
            
            f.write("処理結果:\n")
            f.write(f"  元動画長: {total_duration:.2f}秒\n")
            f.write(f"  無音削除後: {total_keep_time:.2f}秒\n")
            f.write(f"  {settings['speed_factor']}x倍速後: {final_duration:.2f}秒\n")
            f.write(f"  短縮率: {compression_ratio:.1f}%\n")
            f.write(f"  保持セグメント: {len(keep_segments)}個\n\n")
            
            if keep_segments:
                f.write("保持セグメント詳細:\n")
                for i, (start, end) in enumerate(keep_segments, 1):
                    duration = end - start
                    f.write(f"  {i:2d}: {start:6.2f}秒-{end:6.2f}秒 ({duration:.2f}秒)\n")
        
        print(f"レポート保存完了: {filename}")
        
    except Exception as e:
        print(f"レポート保存エラー: {e}")

def main():
    """メイン処理"""
    # --- 引数処理 ---
    if len(sys.argv) < 2:
        print("エラー: 入力ファイルが指定されていません。")
        print(f"使用法: python {os.path.basename(__file__)} <動画ファイル名>")
        return

    input_file = sys.argv[1]
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_processed{ext}"
    
    SETTINGS["input_file"] = input_file
    SETTINGS["output_file"] = output_file
    
    print("AIアバター動画無音削除・倍速ツール")
    print("=" * 50)
    
    # 設定表示
    print("現在の設定:")
    for key, value in SETTINGS.items():
        print(f"  {key}: {value}")
    print()
    
    # 入力ファイル確認
    if not os.path.exists(SETTINGS["input_file"]):
        print(f"ファイルが見つかりません: {SETTINGS['input_file']}")
        return
    
    # 1. 音声抽出
    original_audio = extract_audio_from_video(SETTINGS["input_file"])
    if not original_audio:
        return
    
    # 動画の長さを取得
    video = VideoFileClip(SETTINGS["input_file"])
    total_duration = video.duration
    video.close()
    
    # 2. 処理方法に応じた音声準備
    if SETTINGS["processing_mode"] == "spleeter":
        print("\nSpleeter音声分離モード")
        target_audio = separate_audio_with_spleeter(original_audio)
        if not target_audio:
            print("Spleeterが使用できません。基本モードに切り替えます。")
            target_audio = original_audio
    else:
        print("\n基本検出モード")
        target_audio = original_audio
    
    # 3. 無音検出
    silent_ranges, audio_level, threshold = detect_silence_with_settings(target_audio, SETTINGS)
    
    if not silent_ranges:
        print("無音部分が検出されませんでした。倍速のみ適用します。")
        keep_segments = [(0, total_duration)]
    else:
        # 4. 保持セグメント計算
        keep_segments = generate_keep_segments_with_margin(
            silent_ranges, total_duration, SETTINGS["margin"]
        )
    
    # 5. 処理サマリー表示
    total_silence_time = sum(end - start for start, end in silent_ranges)
    total_keep_time = sum(end - start for start, end in keep_segments)
    final_duration = total_keep_time / SETTINGS["speed_factor"]
    
    print(f"\n処理サマリー:")
    print(f"  元動画: {total_duration:.2f}秒")
    print(f"  検出無音: {len(silent_ranges)}個 ({total_silence_time:.2f}秒)")
    print(f"  無音削除後: {total_keep_time:.2f}秒")
    print(f"  {SETTINGS['speed_factor']}x倍速後: {final_duration:.2f}秒")
    print(f"  短縮率: {(total_duration - final_duration) / total_duration * 100:.1f}%")
    
    # 6. FFmpegで動画処理
    success = process_video_with_ffmpeg(
        SETTINGS["input_file"], SETTINGS["output_file"], 
        keep_segments, SETTINGS["speed_factor"]
    )
    
    if success:
        # 7. レポート保存
        save_detailed_report(
            "processing_report.txt", SETTINGS, silent_ranges, 
            keep_segments, total_duration, audio_level, threshold
        )
        
        print(f"\n処理完了!")
        print(f"  出力ファイル: {SETTINGS['output_file']}")
        print(f"  詳細レポート: processing_report.txt")
    else:
        print(f"\n処理に失敗しました")
    
    # 一時ファイルの削除
    temp_files = [original_audio, "separated_vocals.wav"]
    for temp_file in temp_files:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

if __name__ == "__main__":
    main()
