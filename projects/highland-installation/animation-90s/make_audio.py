"""Local public-domain-dataset TTS plus an original restrained instrumental bed."""
import json,wave,math,subprocess
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from scipy.io import wavfile
from piper import PiperVoice,SynthesisConfig
ROOT=Path(__file__).resolve().parent;A=ROOT/'audio';A.mkdir(exist_ok=True)
S=json.loads((ROOT/'animation-spec.json').read_text());SR=48000;N=90*SR
voice=PiperVoice.load(A/'en_US-ljspeech-high.onnx')
speech=np.zeros(N,dtype=np.float32);activity=np.zeros(N,dtype=np.float32);segments=[]
for sh in S['shots']:
 raw=A/f"voice-{sh['id']:02}.wav"
 with wave.open(str(raw),'wb') as w:
  voice.synthesize_wav(sh['voice'],w,SynthesisConfig(length_scale=1.02,noise_scale=.5,noise_w_scale=.65))
 rate,x=wavfile.read(raw);x=x.astype(np.float32)/32768
 # Remove long generated edge silence without clipping consonants.
 hit=np.flatnonzero(np.abs(x)>.008)
 if len(hit):x=x[max(0,hit[0]-int(.10*rate)):min(len(x),hit[-1]+int(.18*rate))]
 available=sh['end']-sh['start']-(1.0 if sh['id']<8 else .8)
 if len(x)/rate>available:
  # Resample-free tempo correction retains pitch for a clip slightly longer than its shot.
  temp=A/'tempo-input.wav';wavfile.write(temp,rate,(x*32767).astype(np.int16))
  tempo=(len(x)/rate)/available
  subprocess.run(['ffmpeg','-y','-i',str(temp),'-af',f'atempo={tempo:.6f}',str(raw)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  rate,x=wavfile.read(raw);x=x.astype(np.float32)/32768
 x=resample_poly(x,SR,rate).astype(np.float32)
 x*=.76/max(float(np.max(np.abs(x))),.01)
 # Ten millisecond ramps remove clicks while keeping normal speech articulation.
 fade=min(480,len(x)//4);x[:fade]*=np.linspace(0,1,fade);x[-fade:]*=np.linspace(1,0,fade)
 start=sh['start']+(.55 if sh['id']<8 else .25);offset=round(start*SR)
 end=min(offset+len(x),N);speech[offset:end]+=x[:end-offset];activity[offset:end]=1
 segments.append({'id':sh['id'],'start':start,'end':end/SR,'text':sh['voice']})
 print('Voice',sh['id'],round(len(x)/SR,2),'s',flush=True)
wavfile.write(A/'narration.wav',SR,(np.clip(speech,-1,1)*32767).astype(np.int16))
# Compose soft sustained intervals and sparse rounded plucks; no sampled music.
rng=np.random.default_rng(200);music=np.zeros((N,2),dtype=np.float32)
chords=[[146.832,220,277.183,369.994],[123.471,185,246.942,293.665],[98,146.832,185,246.942],[110,164.814,220,293.665]]
for k,start in enumerate(range(0,90,9)):
 duration=min(11,90-start);t=np.arange(round(duration*SR),dtype=np.float32)/SR
 env=np.minimum(t/1.8,1)*np.minimum((duration-t)/2.8,1)
 for j,f in enumerate(chords[k%4]):
  sig=np.sin(2*np.pi*f*t+j*.7)+.16*np.sin(2*np.pi*2*f*t+j*.3)
  trem=.92+.08*np.sin(2*np.pi*.11*t+j)
  sig=(sig*env*trem*.008).astype(np.float32)
  off=start*SR;stop=min(off+len(sig),N);pan=(j-1.5)/4
  music[off:stop,0]+=sig[:stop-off]*(1-pan);music[off:stop,1]+=sig[:stop-off]*(1+pan)
 for j,dt in enumerate([2.5,6]):
  off=round((start+dt)*SR)
  if off>=N:continue
  t=np.arange(min(round(3*SR),N-off),dtype=np.float32)/SR;f=chords[k%4][j+1]*2
  env=(1-np.exp(-t*70))*np.exp(-t*2.8)
  note=(np.sin(2*np.pi*f*t)+.18*np.sin(4*np.pi*f*t))*env*.018
  music[off:off+len(note),0]+=note*.8;music[off:off+len(note),1]+=note
# Gentle ducking under narration, with smoothed boundaries.
duck=np.convolve(activity[::480],np.ones(30,dtype=np.float32)/30,mode='same')
duck=np.interp(np.arange(N),np.arange(len(duck))*480,duck).astype(np.float32)
music*=((1-.65*duck)[:,None])
for t0 in [8,18,29,45,58,73,85]:
 count=int(.13*SR);t=np.arange(count,dtype=np.float32)/SR
 cue=np.sin(2*np.pi*(880*t+160*t*t))*np.sin(np.pi*np.arange(count)/count)**2*.012
 start=round(t0*SR);music[start:start+count,:]+=cue[:,None]
fadein=np.minimum(np.arange(N)/(2*SR),1);fadeout=np.minimum((N-np.arange(N))/(3*SR),1);music*=(fadein*fadeout)[:,None]
wavfile.write(A/'original-score.wav',SR,(np.clip(music,-1,1)*32767).astype(np.int16))
mix=music+speech[:,None]*.9
assert np.max(np.abs(mix))<1
wavfile.write(A/'mix.wav',SR,(mix*32767).astype(np.int16))
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
import textwrap
(ROOT/'Highland-repipe-90s.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(s['start'])} --> {stamp(s['end'])}\n"+'\n'.join(textwrap.wrap(s['text'],46)) for i,s in enumerate(segments))+'\n')
(A/'timing.json').write_text(json.dumps(segments,indent=2,ensure_ascii=False))
(A/'CREDITS.txt').write_text('Narration: locally synthesized with Piper, en_US-ljspeech-high, LJ Speech public-domain dataset. Source: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/ljspeech/high\nScore and transition cues: original procedural composition generated for this project.\nNo original site audio or actual flow measurements are represented.\n')
print('AUDIO_COMPLETE: 90-second stereo mix; narration captions aligned to actual synthesized clips.')
