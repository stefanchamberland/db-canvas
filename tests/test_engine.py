import json, shutil, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageChops
from engine import Layer, Project, render, export_project, run, probe

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.d=Path(self.temp.name)
        self.image=self.d/'photo.png';Image.new('RGB',(320,160),'#167f9b').save(self.image)
    def tearDown(self):self.temp.cleanup()
    def test_seam_keeps_same_continuous_pixels(self):
        # A deliberately asymmetric gradient must survive slicing without shifting the crop.
        gradient=Image.new('RGB',(320,160))
        gradient.putdata([(x%256,y%256,(x+y)%256) for y in range(160) for x in range(320)])
        gradient.save(self.image)
        p=Project(width=160,height=160,count=2,layers=[Layer(path=str(self.image),x=0,y=0,w=320,h=160,border=0)])
        stitched=Image.new('RGB',(320,160));stitched.paste(render(p,0),(0,0));stitched.paste(render(p,1),(160,0))
        self.assertIsNone(ImageChops.difference(gradient,stitched).getbbox())
    def test_portable_project_survives_moving_folder(self):
        p=Project(width=160,height=160,count=1,layers=[Layer(path=str(self.image),x=0,y=0,w=160,h=80,border=0)])
        source=self.d/'original';source.mkdir();p.save(source/'example.dbcanvas')
        moved=self.d/'moved';shutil.move(source,moved);self.image.unlink()
        reopened=Project.load(moved/'example.dbcanvas');self.assertEqual(render(reopened).size,(160,160))
    def test_transparent_logo_preserves_underlying_photo(self):
        logo=self.d/'logo.png'
        im=Image.new('RGBA',(40,40),(0,0,0,0))
        im.putpixel((20,20),(255,255,255,255));im.save(logo)
        p=Project(width=160,height=160,count=1,layers=[
            Layer(path=str(self.image),x=0,y=0,w=160,h=160,border=0,fit='cover'),
            Layer(path=str(logo),x=110,y=110,w=40,h=40,border=0)])
        result=render(p)
        self.assertEqual(result.getpixel((110,110)),(22,127,155))
        self.assertEqual(result.getpixel((130,130)),(255,255,255))
        tile=render(Project(width=40,height=40,count=1,layers=[
            Layer(path=str(logo),x=0,y=0,w=40,h=40,border=0)]),transparent=True)
        self.assertEqual(tile.getpixel((0,0))[3],0)
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
    def test_mixed_carousel_preserves_video_and_audio(self):
        video=self.d/'source.mp4'
        run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=160x160:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',video])
        p=Project(width=160,height=160,count=2,duration=.6,layers=[
            Layer(path=str(self.image),x=0,y=0,w=160,h=160,border=0),
            Layer(path=str(video),kind='video',x=180,y=10,w=110,h=120,border=4,start=.1,end=.4,loop=True,volume=.5),
            Layer(kind='text',x=170,y=140,w=110,h=16,border=0,text='Location',font_size=9)])
        out=self.d/'mixed';files=export_project(p,out)
        self.assertEqual([x.suffix for x in files],['.jpg','.mp4'])
        info=probe(files[1]);self.assertEqual((info['width'],info['height']),(160,160));self.assertTrue(info['audio']);self.assertAlmostEqual(info['duration'],.6,delta=.1)
        # Verify decoded motion changes over time, rather than exporting a still video poster.
        from engine import source_image
        l=Layer(path=str(files[1]),kind='video',start=0,end=.6)
        a=source_image(l,.05);b=source_image(l,.25)
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
    def test_silent_video_exports_with_silent_audio_stream(self):
        video=self.d/'silent.mp4'
        run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=160x90:rate=30','-t','0.4','-an','-c:v','libx264',video])
        p=Project(width=160,height=160,count=1,duration=.4,layers=[
            Layer(path=str(video),kind='video',x=0,y=35,w=160,h=90,border=0,end=.4)])
        files=export_project(p,self.d/'silent-export')
        info=probe(files[0])
        self.assertEqual((info['width'],info['height']),(160,160))
        self.assertTrue(info['audio'])
        self.assertAlmostEqual(info['duration'],.4,delta=.1)
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
    def test_reel_combines_still_scenes_and_soundtrack(self):
        audio=self.d/'music.wav';run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','0.5',audio])
        p=Project(mode='Reel',width=160,height=160,count=2,duration=.4,music=str(audio),layers=[Layer(path=str(self.image),x=0,y=0,w=160,h=160,border=0)])
        files=export_project(p,self.d/'reel');self.assertEqual([p.name for p in files],['reel.mp4'])
        info=probe(files[0]);self.assertTrue(info['audio']);self.assertAlmostEqual(info['duration'],.8,delta=.15)
    def test_export_does_not_overwrite_existing_files(self):
        out=self.d/'existing';out.mkdir();(out/'keep.txt').write_text('keep')
        with self.assertRaises(ValueError):export_project(Project(width=160,height=160,count=1),out)
        self.assertEqual((out/'keep.txt').read_text(),'keep')

if __name__=='__main__':unittest.main()
