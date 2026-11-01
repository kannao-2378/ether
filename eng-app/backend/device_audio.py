"""Offline US speech as a cached WAV, played as media rather than browser speech."""
import hashlib,os,shutil,subprocess,tempfile,threading,wave
from pathlib import Path

_lock=threading.Lock()

def cache_path(text,folder):
 return Path(folder)/(hashlib.sha256(('us-v1:'+text).encode()).hexdigest()+'.wav')

def valid(path):
 try:
  with wave.open(str(path),'rb') as audio:return audio.getnframes()>0 and audio.getnchannels() in (1,2)
 except (OSError,EOFError,wave.Error):return False

def synthesize(text,target):
 if os.name=='nt':
  executable=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
  script="""$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.Speech;
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;
try {
 $voices=@($s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'en-US' });
 if ($voices.Count -eq 0) { throw 'No US English voice installed' };
 $voice=$voices | Where-Object { $_.VoiceInfo.Name -match 'Zira' } | Select-Object -First 1;
 if ($null -eq $voice) { $voice=$voices[0] };
 $s.SelectVoice($voice.VoiceInfo.Name); $s.SetOutputToWaveFile($env:PELS_WAV_OUTPUT);
 $s.Speak($env:PELS_WAV_TEXT);
} finally { $s.Dispose() }
"""
  env=os.environ.copy();env.update(PELS_WAV_TEXT=text,PELS_WAV_OUTPUT=str(target))
  subprocess.run([str(executable),'-NoProfile','-NonInteractive','-Command',script],env=env,check=True,timeout=30,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 else:
  executable=shutil.which('espeak-ng')
  if not executable:raise ValueError('服务器尚未安装离线录音引擎，请安装 espeak-ng 或迁移电脑已生成的录音缓存。')
  subprocess.run([executable,'-v','en-us','-w',str(target),'--stdin'],input=text.encode(),check=True,timeout=30,capture_output=True)

def get_audio(text,folder):
 if not text.strip() or len(text)>300:raise ValueError('发音内容长度无效')
 target=cache_path(text,folder)
 with _lock:
  if valid(target):return target
  target.parent.mkdir(parents=True,exist_ok=True)
  temporary=None
  try:
   with tempfile.NamedTemporaryFile(dir=target.parent,suffix='.wav',delete=False) as f:temporary=Path(f.name)
   synthesize(text,temporary)
   if not valid(temporary):raise ValueError('录音生成失败，请检查电脑的美式语音包。')
   temporary.replace(target)
  except (subprocess.SubprocessError,OSError) as e:
   raise ValueError('离线录音生成失败，请检查服务器英语语音引擎后重试。') from e
  finally:
   if temporary:temporary.unlink(missing_ok=True)
 return target
