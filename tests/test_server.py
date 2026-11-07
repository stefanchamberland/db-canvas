"""Exercise the real HTTP workflow without a browser or external service."""
import io,json,re,sys,tempfile,threading,time,unittest,urllib.request,urllib.error,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
import server

class LocalWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();server.DATA=Path(cls.tmp.name);server.MEDIA=server.DATA/'media';server.MEDIA.mkdir()
        server.ASSETS.clear();server.JOBS.clear()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.base=f'http://127.0.0.1:{cls.http.server_port}'
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def request(self,path,data=None,raw=False,authorized=True):
        headers={'X-DB-Token':server.TOKEN} if authorized else {}
        body=data if raw else json.dumps(data).encode() if data is not None else None
        req=urllib.request.Request(self.base+path,data=body,headers=headers)
        with urllib.request.urlopen(req) as r:
            value=r.read();return value if raw else json.loads(value)
    def wait_for_job(self,key):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=self.request('/api/job/'+key)
            if state['status']=='error':self.fail(state.get('error'))
            if state['status']=='done':return state
            time.sleep(.05)
        self.fail('Export job timed out')
    def test_interface_is_served_and_token_protected(self):
        html=urllib.request.urlopen(self.base).read().decode()
        self.assertIn(server.TOKEN,html);self.assertNotIn('__TOKEN__',html)
        self.assertIn('Continuous carousel composition',html)
        with self.assertRaises(urllib.error.HTTPError) as err:self.request('/api/info',authorized=False)
        self.assertEqual(err.exception.code,403)
    def test_import_arrange_save_reopen_export_and_video_range(self):
        buf=io.BytesIO();Image.new('RGB',(320,180),'#539f92').save(buf,'PNG')
        imported=self.request('/api/upload?name=photo.png',buf.getvalue(),raw=True)
        imported=json.loads(imported)
        p=server.Project(width=160,height=160,count=1).snapshot();p['music_asset']=''
        layout=self.request('/api/arrange',{'project':p,'ids':[imported['id']],'style':'Full bleed'})
        self.assertEqual(len(layout['project']['layers']),1)
        # Arrange twice: source IDs are reused instead of multiplying media-library entries.
        again=self.request('/api/arrange',{'project':layout['project'],'ids':[imported['id']],'style':'Full bleed'})
        self.assertEqual(again['assets'][0]['id'],imported['id'])
        poster=self.request('/poster/'+imported['id'],raw=True);self.assertTrue(poster.startswith(b'\xff\xd8'))
        saved=self.request('/api/save',{'project':layout['project']});self.wait_for_job(saved['id'])
        bundle=self.request('/download/'+saved['id'],raw=True)
        with zipfile.ZipFile(io.BytesIO(bundle)) as z:self.assertIn('project.dbcanvas',z.namelist())
        opened=self.request('/api/open',bundle,raw=True);opened=json.loads(opened)
        self.assertEqual(opened['project']['layers'][0]['w'],160)
        exported=self.request('/api/export',{'project':opened['project']});self.wait_for_job(exported['id'])
        with zipfile.ZipFile(io.BytesIO(self.request('/download/'+exported['id'],raw=True))) as z:
            self.assertEqual(set(z.namelist()),{'01.jpg','cover.jpg','export.json'})
        req=urllib.request.Request(self.base+'/media/'+imported['id']+'?token='+server.TOKEN,headers={'Range':'bytes=0-15'})
        with urllib.request.urlopen(req) as response:self.assertEqual(response.status,206);self.assertEqual(len(response.read()),16)
    def test_project_zip_rejects_parent_traversal(self):
        p=server.Project(width=160,height=160,count=1,layers=[server.Layer(path='../outside.png',w=80,h=80)]).snapshot()
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('project.dbcanvas',json.dumps(p));z.writestr('../outside.png','bad')
        with self.assertRaises(urllib.error.HTTPError) as err:self.request('/api/open',buf.getvalue(),raw=True)
        self.assertEqual(err.exception.code,400)

if __name__=='__main__':unittest.main()
