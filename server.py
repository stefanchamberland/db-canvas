"""Loopback-only server for _dB Canvas's portable browser interface."""
from __future__ import annotations
import base64,io,json,mimetypes,os,re,secrets,shutil,sys,threading,time,uuid,webbrowser,zipfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs,unquote
from engine import Project,Layer,probe,arrange,export_project,source_image,text_tile

BASE=Path(__file__).resolve().parent
DATA=Path(os.environ.get('DB_CANVAS_DATA',str(BASE/'workspace'))).resolve()
DATA.mkdir(parents=True,exist_ok=True);MEDIA=DATA/'media';MEDIA.mkdir(exist_ok=True)
TOKEN=secrets.token_urlsafe(32);JOBS={};ASSETS={};LOCK=threading.Lock()
MAX_UPLOAD=2*1024**3

def preset_folder(name):
    if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',name):
        raise ValueError('Use a preset name with lowercase letters, numbers, hyphens, or underscores (up to 80 characters).')
    return DATA/'presets'/name

def save_preset(name,p):
    p.validate();folder=preset_folder(name)
    with LOCK:
        if folder.exists():raise ValueError('That preset already exists. Choose a new name.')
        folder.parent.mkdir(parents=True,exist_ok=True)
        import tempfile
        with tempfile.TemporaryDirectory(dir=folder.parent,prefix='.saving-') as temp:
            staging=Path(temp);p.save(staging/'project.dbcanvas')
            staging.rename(folder)
    return name

def asset(path):
    path=Path(path).resolve()
    for key,existing in ASSETS.items():
        if existing['path']==str(path) and existing['kind']!='audio':return {k:v for k,v in existing.items() if k!='path'}|{'id':key}
    key=uuid.uuid4().hex
    info=probe(path);ASSETS[key]={'path':str(path),'name':path.name,**info}
    return {'id':key,'name':path.name,**info}

def decode_project(data):
    d=json.loads(json.dumps(data));d.pop('schema_version',None)
    for l in d.get('layers',[]):
        media_id=l.pop('asset',None)
        if l.get('kind')!='text':
            if media_id not in ASSETS:raise ValueError('Missing media. Reopen the saved project or reimport the asset.')
            l['path']=ASSETS[media_id]['path']
        else:l['path']=''
    music=d.pop('music_asset',None);d['music']=''
    if music:
        if music not in ASSETS:raise ValueError('Missing soundtrack.')
        d['music']=ASSETS[music]['path']
    p=Project.from_dict(d);p.validate();return p

def encode_project(p):
    d=p.snapshot();assets=[];ids={}
    for l in d['layers']:
        if l['kind']=='text':l['asset']='';l['path']='';continue
        path=l['path']
        if path not in ids:
            result=asset(path);assets.append(result);ids[path]=result['id']
        l['asset']=ids[path];l['path']=''
    if d['music']:
        path=d['music'];key=uuid.uuid4().hex;ASSETS[key]={'path':path,'name':Path(path).name,'kind':'audio'};d['music_asset']=key;assets.append({'id':key,'name':Path(path).name,'kind':'audio'})
    d['music']='';return {'project':d,'assets':assets}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def json(self,data,status=200):
        content=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def authorized(self,query=None):return secrets.compare_digest(self.headers.get('X-DB-Token','') or (query or {}).get('token',[''])[0],TOKEN)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size<=0 or size>MAX_UPLOAD:raise ValueError('Empty file or upload exceeds the 2 GB per-file limit.')
        return self.rfile.read(size)
    def send_file(self,path,content_type=None,download=None):
        path=Path(path);size=path.stat().st_size;start=0;end=size-1
        # Byte ranges let HTML video seek without downloading the entire source again.
        header=self.headers.get('Range','')
        if header.startswith('bytes='):
            first,last=header[6:].split('-',1)
            if first:start=int(first);end=int(last) if last else end
            else:start=max(0,size-int(last))
            end=min(end,size-1)
            if start>end or start<0:self.send_error(416);return
        self.send_response(206 if header else 200);self.send_header('Content-Type',content_type or mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
        if header:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        if download:self.send_header('Content-Disposition',f'attachment; filename="{download}"')
        self.end_headers()
        with path.open('rb') as f:
            f.seek(start);remaining=end-start+1
            while remaining:
                chunk=f.read(min(1024*1024,remaining))
                if not chunk:break
                self.wfile.write(chunk);remaining-=len(chunk)
    def do_GET(self):
        try:
            u=urlparse(self.path);q=parse_qs(u.query)
            if u.path in ('/','/index.html'):
                data=(BASE/'index.html').read_text().replace('__TOKEN__',TOKEN).encode()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if not self.authorized(q):self.json({'error':'Unauthorized'},403);return
            if u.path=='/api/info':self.json({'ffmpeg':bool(shutil.which('ffmpeg')),'ffprobe':bool(shutil.which('ffprobe')),'workspace':str(DATA)});return
            if u.path=='/api/presets':
                folder=DATA/'presets'
                self.json({'presets':sorted(f.name for f in folder.iterdir() if (f/'project.dbcanvas').is_file() and not f.name.startswith('.')) if folder.exists() else []});return
            if u.path.startswith('/poster/'):
                key=u.path.split('/')[-1]
                if key not in ASSETS:raise ValueError('Unknown media.')
                a=ASSETS[key];target=MEDIA/(key+'-poster.jpg')
                alpha_target=MEDIA/(key+'-poster.png')
                if alpha_target.exists():target=alpha_target
                if not target.exists():
                    layer=Layer(path=a['path'],kind=a['kind'],start=0,end=max(.1,min(5,a.get('duration',5))))
                    im=source_image(layer);im.thumbnail((1800,1800))
                    if im.mode=='RGBA':target=alpha_target
                    im.save(target,quality=91)
                self.send_file(target,'image/png' if target.suffix=='.png' else 'image/jpeg');return
            if u.path.startswith('/media/'):
                key=u.path.split('/')[-1]
                if key not in ASSETS:raise ValueError('Unknown media.')
                self.send_file(ASSETS[key]['path']);return
            if u.path.startswith('/api/job/'):
                key=u.path.split('/')[-1]
                if key not in JOBS:raise ValueError('Unknown export.')
                self.json({k:v for k,v in JOBS[key].items() if k!='path'});return
            if u.path.startswith('/download/'):
                key=u.path.split('/')[-1]
                if key not in JOBS or JOBS[key]['status']!='done':raise ValueError('Download is not ready.')
                self.send_file(JOBS[key]['path'],'application/zip',JOBS[key]['filename']);return
            self.send_error(404)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:self.json({'error':str(e)},400)
    def do_POST(self):
        try:
            if not self.authorized():self.json({'error':'Unauthorized'},403);return
            u=urlparse(self.path);q=parse_qs(u.query)
            if u.path=='/api/upload':
                name=Path(q.get('name',['media'])[0]).name;ext=Path(name).suffix.lower()
                allowed={'.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp','.mp4','.mov','.m4v','.webm','.mkv','.avi','.mp3','.wav','.aac','.m4a','.ogg','.flac'}
                if ext not in allowed:raise ValueError('Unsupported file type. Use common photos, videos, or audio.')
                path=MEDIA/(uuid.uuid4().hex+ext);path.write_bytes(self.body())
                try:
                    if ext in {'.mp3','.wav','.aac','.m4a','.ogg','.flac'}:
                        key=uuid.uuid4().hex;ASSETS[key]={'path':str(path),'name':name,'kind':'audio'};result={'id':key,'name':name,'kind':'audio'}
                    else:
                        result=asset(path);ASSETS[result['id']]['name']=name;result['name']=name
                except Exception:path.unlink(missing_ok=True);raise
                self.json(result);return
            if u.path=='/api/open':
                # Portable project ZIP; only copy specifically referenced files after validation.
                data=self.body();folder=DATA/'projects'/uuid.uuid4().hex;folder.mkdir(parents=True)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    if sum(i.file_size for i in z.infolist())>4*1024**3:raise ValueError('Project expands beyond 4 GB.')
                    project=json.loads(z.read('project.dbcanvas'));project.pop('schema_version',None)
                    paths=[l.get('path') for l in project['layers'] if l.get('path')]+([project['music']] if project.get('music') else [])
                    for rel in set(paths):
                        candidate=Path(rel)
                        if candidate.is_absolute() or '..' in candidate.parts:raise ValueError('Invalid project asset path.')
                        target=folder/candidate;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(rel))
                    for l in project['layers']:
                        if l.get('path'):l['path']=str(folder/l['path'])
                    if project.get('music'):project['music']=str(folder/project['music'])
                p=Project.from_dict(project);p.validate();self.json(encode_project(p));return
            data=json.loads(self.body())
            if u.path=='/api/text-preview':
                # Typography uses the same renderer in the editor and exported files.
                l=Layer(**data['layer'])
                if l.kind!='text' or not 2<=l.w<=3840 or not 2<=l.h<=3840:raise ValueError('Text preview dimensions must be 2–3840.')
                Project(layers=[l]).validate()
                buf=io.BytesIO();text_tile(l).save(buf,format='PNG')
                self.json({'url':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()});return
            if u.path=='/api/presets/save':
                name=save_preset(data.get('name'),decode_project(data['project']))
                self.json({'name':name});return
            if u.path=='/api/presets/load':
                p=Project.load(preset_folder(data.get('name'))/'project.dbcanvas')
                self.json(encode_project(p));return
            if u.path=='/api/arrange':
                p=decode_project(data['project']);paths=[ASSETS[i]['path'] for i in data['ids']]
                arrange(p,paths,data.get('style','Seamless'));self.json(encode_project(p));return
            if u.path in ('/api/save','/api/export'):
                p=decode_project(data['project']);key=uuid.uuid4().hex
                JOBS[key]={'status':'working','progress':'Preparing…','filename':'db-canvas-project.zip' if u.path.endswith('save') else 'db-canvas-export.zip'}
                def worker():
                    try:
                        folder=DATA/'exports'/key;folder.mkdir(parents=True)
                        if u.path.endswith('save'):
                            p.save(folder/'project.dbcanvas');archive=folder.parent/(key+'.zip')
                            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                                for f in folder.rglob('*'):
                                    if f.is_file():z.write(f,f.relative_to(folder))
                        else:
                            output=folder/'slides';export_project(p,output,lambda s:JOBS[key].update(progress=s));archive=folder/(key+'.zip')
                            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                                for f in output.iterdir():z.write(f,f.name)
                        JOBS[key].update(status='done',progress='Ready',path=str(archive))
                    except Exception as e:JOBS[key].update(status='error',error=str(e))
                threading.Thread(target=worker,daemon=True).start();self.json({'id':key});return
            self.send_error(404)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:self.json({'error':str(e)},400)

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);url=f'http://127.0.0.1:{server.server_port}'
    print(f'_dB Canvas is running at {url}\nKeep this window open. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
