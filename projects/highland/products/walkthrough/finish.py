"""Check the encoded tour and package phone files for GitHub delivery."""
from pathlib import Path
import hashlib,json,shutil,subprocess
from PIL import Image,ImageStat

ROOT=Path(__file__).resolve().parents[4]
B=ROOT/'build/highland-drone';D=ROOT/'projects/highland/deliverables/drone';D.mkdir(parents=True,exist_ok=True)
video=B/'Highland-corridor-drone.mp4';viewer=B/'Highland-drone-tour.html'
assert video.exists() and viewer.exists()
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries','format=duration,size','-of','json',str(video)]))
stream=probe['streams'][0]
assert (stream['codec_name'],stream['width'],stream['height'],stream['r_frame_rate'],stream['nb_frames'])==('h264',720,1280,'24/1','624')
assert abs(float(probe['format']['duration'])-26)<.06
audio_probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_name,channels,sample_rate','-of','json',str(video)]))
audio_stream=audio_probe['streams'][0]
assert audio_stream['codec_name']=='aac' and audio_stream['channels']==2 and int(audio_stream['sample_rate'])==44100
poster=D/'Highland-drone-poster.png'
subprocess.run(['ffmpeg','-y','-loglevel','error','-ss','22','-i',str(video),'-frames:v','1',str(poster)],check=True)
gif=D/'Highland-drone-preview.gif'
subprocess.run(['ffmpeg','-y','-loglevel','error','-ss','2.5','-t','7','-i',str(video),'-vf','fps=8,scale=320:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5','-loop','0',str(gif)],check=True)
xray=D/'Highland-xray-preview.gif'
subprocess.run(['ffmpeg','-y','-loglevel','error','-ss','14.7','-t','4.9','-i',str(video),'-vf','fps=8,scale=320:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5','-loop','0',str(xray)],check=True)
for file in [poster,gif,xray]:
    frame=Image.open(file).convert('RGB');assert max(ImageStat.Stat(frame).stddev)>15,file
for file in [video,viewer]:shutil.copyfile(file,D/file.name)
report=json.loads((B/'validation.json').read_text())
assert not report['browser_errors'] and not report['mobile_overflow']
report['media_checks']={'codec':stream['codec_name'],'audio_codec':audio_stream['codec_name'],'audio_channels':2,'resolution':[720,1280],'frames':624,'duration_seconds':26,'poster_nonblank':True,'animated_preview_nonblank':True,'xray_preview_nonblank':True}
report['artifact_sha256']={file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in [video,viewer,poster,gif,xray]}
(D/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Phone video, standalone viewer, poster and animated preview packaged.')
