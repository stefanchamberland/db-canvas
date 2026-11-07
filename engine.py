"""Local composition and FFmpeg export engine. No upload or publishing service."""
from __future__ import annotations
import copy, json, math, os, shutil, subprocess, tempfile, uuid
# Finder-launched macOS apps do not inherit a shell's Homebrew PATH.
os.environ["PATH"] = os.pathsep.join(["/opt/homebrew/bin", "/usr/local/bin", os.environ.get("PATH", "")])
from dataclasses import dataclass, field, asdict
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

PRESETS = {'Portrait · 4:5':(1080,1350), 'Square · 1:1':(1080,1080),
           'Tall photo · 3:4':(1080,1440), 'Landscape · 1.91:1':(1080,566),
           'Widescreen · 16:9':(1080,608), 'Vertical · 9:16':(1080,1920)}
VIDEO_EXTS={'.mp4','.mov','.m4v','.webm','.mkv','.avi'}
MODES=['Carousel','Single post','Reel','Stories']

def run(args):
    p=subprocess.run([str(a) for a in args],capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-4000:] or 'Media command failed.')
    return p.stdout

def require_video():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Install FFmpeg (includes ffprobe) to import or export video. On macOS: brew install ffmpeg')

def probe(path):
    path=Path(path)
    if path.suffix.lower() not in VIDEO_EXTS:
        with Image.open(path) as original:
            im=ImageOps.exif_transpose(original)
            return dict(kind='image',width=im.width,height=im.height,duration=0,audio=False)
    require_video()
    data=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]))
    video=next((s for s in data['streams'] if s['codec_type']=='video'),None)
    if not video: raise ValueError('No video stream found.')
    w,h=video['width'],video['height']
    rotation=float(video.get('tags',{}).get('rotate',0))
    for side in video.get('side_data_list',[]): rotation=float(side.get('rotation',rotation))
    if abs(rotation)%180==90: w,h=h,w
    duration=float(video.get('duration') or data.get('format',{}).get('duration') or 0)
    if duration<=0: raise ValueError('Could not determine video duration.')
    return dict(kind='video',width=w,height=h,duration=duration,
                audio=any(s['codec_type']=='audio' for s in data['streams']))

@dataclass
class Layer:
    path: str=''
    kind: str='image'
    x: float=70
    y: float=100
    w: float=800
    h: float=600
    border: int=16
    fit: str='contain'
    focus_x: float=.5
    focus_y: float=.5
    start: float=0
    end: float=5
    loop: bool=False
    volume: float=0
    text: str=''
    font_size: int=30
    color: str='#333329'
    id: str=field(default_factory=lambda:uuid.uuid4().hex)

@dataclass
class Project:
    name: str='Untitled'
    mode: str='Carousel'
    width: int=1080
    height: int=1350
    count: int=4
    background: str='#eae7df'
    duration: float=5
    durations: list=field(default_factory=list)
    layers: list[Layer]=field(default_factory=list)
    music: str=''
    music_volume: float=.5
    fps: int=30
    def seconds(self,i):
        return float(self.durations[i] if i<len(self.durations) and self.durations[i] is not None else self.duration)
    def snapshot(self): return asdict(self)
    @classmethod
    def from_dict(cls,data):
        d=copy.deepcopy(data)
        d['layers']=[Layer(**l) for l in d.get('layers',[])]
        return cls(**d)
    def active(self,i):
        a=i*self.width;b=a+self.width
        return [l for l in self.layers if l.x+l.w+l.border>a and l.x-l.border<b and l.y+l.h+l.border>0 and l.y-l.border<self.height]
    def save(self,path):
        """Copy assets alongside JSON so the project folder can move between machines."""
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        assets=path.parent/(path.stem+'.media');assets.mkdir(exist_ok=True)
        data=self.snapshot();mapping={}
        for layer in data['layers']:
            if not layer['path']: continue
            source=Path(layer['path']).resolve()
            if str(source) not in mapping:
                target=assets/(uuid.uuid5(uuid.NAMESPACE_URL,str(source)).hex[:12]+source.suffix.lower())
                if source!=target.resolve(): shutil.copy2(source,target)
                mapping[str(source)]=str(target.relative_to(path.parent))
            layer['path']=mapping[str(source)]
        if data['music']:
            source=Path(data['music']).resolve();target=assets/('soundtrack'+source.suffix)
            if source!=target.resolve():shutil.copy2(source,target)
            data['music']=str(target.relative_to(path.parent))
        data['schema_version']=1
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)
    @classmethod
    def load(cls,path):
        path=Path(path);data=json.loads(path.read_text(encoding='utf-8'))
        if data.pop('schema_version',1)!=1:raise ValueError('Unsupported project version.')
        for l in data['layers']:
            if l['path']:l['path']=str((path.parent/l['path']).resolve())
        if data.get('music'):data['music']=str((path.parent/data['music']).resolve())
        p=cls.from_dict(data);p.validate();return p
    def validate(self):
        if self.mode not in MODES:raise ValueError('Unknown project mode.')
        if not 1<=self.count<=20:raise ValueError('Use 1–20 slides/scenes.')
        if self.width<2 or self.height<2 or self.width>3840 or self.height>3840 or self.width%2 or self.height%2:raise ValueError('Canvas dimensions must be positive even numbers.')
        if self.mode=='Single post' and self.count!=1:raise ValueError('Single post requires one scene.')
        if not 1<=self.fps<=60:raise ValueError('Frame rate must be 1–60.')
        for i in range(self.count):
            if not .1<=self.seconds(i)<=1200:raise ValueError('Each scene duration must be 0.1–1200 seconds.')
        for l in self.layers:
            if l.w<2 or l.h<2 or l.w>self.width*20 or l.h>self.height*20:raise ValueError('Invalid layer dimensions.')
            if l.border<0 or l.border>200:raise ValueError('Frame border must be 0–200 px.')
            if l.kind not in ('text','image','video'):raise ValueError('Unknown layer kind.')
            if not all(math.isfinite(v) for v in [l.x,l.y,l.w,l.h,l.focus_x,l.focus_y,l.start,l.end,l.volume]):raise ValueError('Frame values must be finite numbers.')
            if not 0<=l.focus_x<=1 or not 0<=l.focus_y<=1 or not 0<=l.volume<=1:raise ValueError('Crop focus and volume must be 0–1.')
            if l.fit not in ('contain','cover'):raise ValueError('Unknown frame fit.')
            if l.kind!='text' and not Path(l.path).is_file():raise ValueError('Missing media: '+l.path)
            if l.kind=='video' and l.end<=l.start:raise ValueError('Video out must be after video in.')
        if self.music and not Path(self.music).is_file():raise ValueError('Missing soundtrack: '+self.music)

def font(size):
    for f in ['/System/Library/Fonts/Helvetica.ttc','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(f).exists():return ImageFont.truetype(f,max(1,int(size)))
    return ImageFont.load_default()

def source_image(layer,time=0,max_width=2048):
    if layer.kind=='image':
        with Image.open(layer.path) as im:
            mode='RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB'
            return ImageOps.exif_transpose(im).convert(mode)
    duration=max(.01,layer.end-layer.start)
    t=layer.start+(time%duration if layer.loop else min(time,max(0,duration-.04)))
    require_video()
    data=run(['ffmpeg','-v','error','-ss',f'{t:.4f}','-i',layer.path,'-frames:v','1','-vf',f'scale=min({max_width}\\,iw):-2','-f','image2pipe','-vcodec','png','-threads','1','-'])
    import io
    return Image.open(io.BytesIO(data)).convert('RGB')

def fit_image(im,w,h,fit='contain',fx=.5,fy=.5,background='#fffdf8'):
    w,h=max(1,round(w)),max(1,round(h))
    if fit=='cover':return ImageOps.fit(im,(w,h),Image.Resampling.LANCZOS,centering=(max(0,min(1,fx)),max(0,min(1,fy))))
    frame=Image.new('RGBA' if im.mode=='RGBA' else 'RGB',(w,h),(0,0,0,0) if im.mode=='RGBA' else background)
    tile=ImageOps.contain(im,(w,h),Image.Resampling.LANCZOS)
    frame.paste(tile,((w-tile.width)//2,(h-tile.height)//2));return frame

def render(project,index=0,time=0,scale=1,cache=None,transparent=False):
    w,h=round(project.width*scale),round(project.height*scale)
    canvas=Image.new('RGBA' if transparent else 'RGB',(w,h),(0,0,0,0) if transparent else project.background);d=ImageDraw.Draw(canvas)
    for l in project.active(index):
        x=round((l.x-index*project.width)*scale);y=round(l.y*scale)
        lw,lh=max(1,round(l.w*scale)),max(1,round(l.h*scale));border=round(l.border*scale)
        if border:d.rectangle((x-border,y-border,x+lw+border-1,y+lh+border-1),fill='#fffdf8')
        if l.kind=='text':
            d.rectangle((x,y,x+lw-1,y+lh-1),fill='#fffdf8')
            d.text((x+12*scale,y+8*scale),l.text,font=font(l.font_size*scale),fill=l.color)
            continue
        key=(l.path,l.start) if l.kind=='video' else l.path
        if cache is not None and key in cache: im=cache[key]
        else:
            im=source_image(l,time)
            if cache is not None: cache[key]=im
        tile=fit_image(im,lw,lh,l.fit,l.focus_x,l.focus_y)
        if tile.mode=='RGBA':
            if transparent:canvas.alpha_composite(tile,(x,y))
            else:canvas.paste(tile,(x,y),tile.getchannel('A'))
        else:canvas.paste(tile,(x,y))
    return canvas

def arrange(project,paths,style='Frames'):
    """Return source-aware frames in input order; deterministic, editable placements."""
    layers=[];cursor=70;slide=0
    for path in paths:
        info=probe(path);ratio=info['width']/info['height']
        if style=='Seamless' and ratio>1.15 and project.mode=='Carousel':
            w=min(project.width*1.5,(project.height-180)*ratio)
            h=w/ratio;x=cursor;y=(project.height-h)/2
            cursor=x+w+90
        else:
            slide=math.ceil(max(0,cursor-70)/project.width) if layers else 0
            w=min(project.width-140,(project.height-200)*ratio);h=w/ratio
            x=slide*project.width+(project.width-w)/2;y=(project.height-h)/2
            cursor=(slide+1)*project.width+70
            if style=='Full bleed':x=slide*project.width;y=0;w=project.width;h=project.height
        layers.append(Layer(path=str(Path(path).resolve()),kind=info['kind'],x=x,y=y,w=w,h=h,
                            border=0 if style=='Full bleed' else 16,fit='cover' if style=='Full bleed' else 'contain',
                            end=min(info['duration'],5) if info['kind']=='video' else 5))
    count=max(1,math.ceil((max((l.x+l.w+l.border for l in layers),default=project.width))/project.width))
    if count>20:raise ValueError('This layout needs more than 20 slides. Import fewer assets or resize frames.')
    if project.mode=='Single post' and len(layers)>1:raise ValueError('Switch to Carousel, Reel, or Stories to arrange several assets.')
    project.layers=layers;project.count=1 if project.mode=='Single post' else count


def video_filter(l,w,h):
    if l.fit=='cover':
        return f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-ow)*{l.focus_x}:(ih-oh)*{l.focus_y},setsar=1'
    return f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0xfffdf8,setsar=1'

def export_scene(p,i,target,work,progress=lambda _:None):
    """Pre-render each moving layer, then stack it with still/text PNG layers."""
    require_video();seconds=p.seconds(i);w,h=p.width,p.height
    bg=work/f'bg-{i}.png';Image.new('RGB',(w,h),p.background).save(bg)
    command=['ffmpeg','-v','error','-y','-loop','1','-framerate',str(p.fps),'-i',str(bg)]
    filters=[];streams=[];index=1;last='0:v'
    for j,l in enumerate(p.active(i)):
        px=round(l.x-i*w);py=round(l.y);lw=max(2,round(l.w));lh=max(2,round(l.h));b=l.border
        if l.kind=='video':lw+=lw%2;lh+=lh%2
        if l.kind=='video':
            tile=work/f'video-{i}-{j}.mp4';clip=max(.01,l.end-l.start)
            # Decode only the trim interval; loop or hold its last frame for this scene.
            loop_args=['-stream_loop','-1'] if l.loop else []
            # Trim to an intermediate file so looping always repeats the selected interval.
            cut=work/f'cut-{i}-{j}.mkv'
            run(['ffmpeg','-v','error','-y','-ss',str(l.start),'-i',l.path,'-t',str(clip),'-map','0:v:0','-map','0:a?',
                 '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac',cut])
            vf=video_filter(l,lw,lh)+f',fps={p.fps},tpad=stop_mode=clone:stop_duration={seconds}'
            if b:vf+=f',pad={lw+2*b}:{lh+2*b}:{b}:{b}:color=0xfffdf8'
            run(['ffmpeg','-v','error','-y',*loop_args,'-i',cut,'-t',str(seconds),'-vf',vf,
                 '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2',tile])
            command+=['-i',str(tile)]
            if l.volume>0 and probe(l.path)['audio']:
                streams.append((cut,l.volume,l.loop))
        else:
            tile=work/f'still-{i}-{j}.png'
            isolated=Project(width=lw+2*b,height=lh+2*b,count=1,background='#fffdf8',layers=[copy.deepcopy(l)])
            isolated.layers[0].x=b;isolated.layers[0].y=b
            render(isolated,transparent=True).save(tile)
            command+=['-loop','1','-framerate',str(p.fps),'-i',str(tile)]
        out=f'v{index}'
        filters.append(f'[{last}][{index}:v]overlay=x={px-b}:y={py-b}:eof_action=repeat:shortest=0[{out}]')
        last=out;index+=1
    audio_indices=[]
    for cut,volume,loop in streams:
        command+=(['-stream_loop','-1'] if loop else [])+['-i',str(cut)]
        audio_indices.append((index,volume));index+=1
    if p.music:
        offset=sum(p.seconds(k) for k in range(i))
        command+=['-stream_loop','-1','-ss',str(offset),'-i',p.music]
        audio_indices.append((index,p.music_volume));index+=1
    audio_labels=[]
    for j,(idx,volume) in enumerate(audio_indices):
        tag=f'a{j}';filters.append(f'[{idx}:a]asetpts=PTS-STARTPTS,volume={volume},apad,atrim=duration={seconds}[{tag}]');audio_labels.append(f'[{tag}]')
    if audio_labels:filters.append(''.join(audio_labels)+f'amix=inputs={len(audio_labels)}:duration=longest:normalize=0,alimiter=limit=0.95[audio]')
    else:
        # FFmpeg requires all inputs before output options such as -map.
        command+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    if filters:command+=['-filter_complex_threads','1','-filter_complex',';'.join(filters)]
    command+=['-map',f'[{last}]' if last!='0:v' else '0:v']
    if audio_labels:command+=['-map','[audio]','-c:a','aac','-b:a','192k']
    else:
        # A silent audio stream makes later scene concatenation consistent.
        command+=['-map',f'{index}:a','-c:a','aac']
    command+=['-t',str(seconds),'-r',str(p.fps),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',
              '-ar','48000','-ac','2','-movflags','+faststart','-threads','2',str(target)]
    run(command)

def export_project(project,folder,progress=lambda _:None):
    project.validate();folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if any(folder.iterdir()):raise ValueError('Choose a new empty output folder to avoid overwriting an earlier export.')
    outputs=[]
    # Build everything privately. Do not leave a misleading partial export after a failure.
    with tempfile.TemporaryDirectory(prefix='db-canvas-') as tmp:
        work=Path(tmp);staged=work/'finished';staged.mkdir()
        for i in range(project.count):
            progress(f'Rendering {i+1} / {project.count}…')
            moving=bool(project.music) or project.mode in ('Reel','Stories') or any(l.kind=='video' for l in project.active(i))
            target=staged/f'{i+1:02}.{"mp4" if moving else "jpg"}'
            if moving:export_scene(project,i,target,work,progress)
            else:render(project,i).save(target,quality=96,subsampling=0)
            outputs.append(target)
        if project.mode=='Reel':
            concat=work/'concat.txt';concat.write_text('\n'.join("file '"+str(p)+"'" for p in outputs))
            reel=staged/'reel.mp4'
            run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',concat,'-c','copy','-movflags','+faststart',reel])
            for p in outputs:p.unlink()
            outputs=[reel]
        # Cover is a still, never counted as another carousel slide.
        render(project,0).save(staged/'cover.jpg',quality=95)
        manifest=dict(name=project.name,mode=project.mode,width=project.width,height=project.height,
                      files=[p.name for p in outputs],fps=project.fps,
                      notes=['Upload numbered files in order. cover.jpg is an optional cover, not an extra slide.',
                             'Spanning videos are spatially continuous; Instagram playback across swipes is not synchronized.'])
        (staged/'export.json').write_text(json.dumps(manifest,indent=2))
        for p in staged.iterdir():shutil.copy2(p,folder/p.name)
    progress('Export complete.')
    return [folder/p.name for p in outputs]
