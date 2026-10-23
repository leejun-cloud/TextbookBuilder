#!/usr/bin/env python3
"""인쇄·조립 회귀검사. 정상/변조 명세, 실제 PDF, 양면·변경 감지를 시험한다."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw,ImageChops
import fitz
from pypdf import PdfWriter
from textbuilder import BookDocument,Page,blk,load,RenderOptions
from textbuilder.model import Metadata
from textbuilder.activity_geometry import ActivityError,load_plan,pack_cutouts,compare_pair,outline
from textbuilder.cut_paste import build_book
from textbuilder.print_qc import audit_pdf,audit_cutout_geometry
from textbuilder.typst_gen import block_data,REPO_ROOT
from textbuilder.renderers.typst_cli import TypstRenderer


def fixture(folder):
    image=Image.new('RGB',(1800,1200),'#f1f4f8'); draw=ImageDraw.Draw(image)
    draw.rectangle((180,180,499,579),fill='#186577')
    draw.ellipse((720,180,1079,479),fill='#ed773f')
    draw.polygon([(1140,180),(1499,180),(1409,539),(1229,449)],fill='#854fa1')
    image.save(folder/'scene.png')
    data={'schema':'cut-paste/v1','language':'en',
          'activities':[{'id':'01','title':'Match the shapes',
            'scene':{'src':'scene.png','x_mm':20,'y_mm':55,'width_mm':142},
            'pieces':[{'id':'a','label':'A','crop_px':[180,180,320,400],'outline':'rectangle'},
                      {'id':'b','label':'B','crop_px':[720,180,360,300],'outline':'ellipse'},
                      {'id':'c','label':'C','crop_px':[1140,180,360,360],
                       'outline':[[0,0],[1,0],[.75,1],[.25,.75]]}]}]}
    manifest=folder/'activity.json'; manifest.write_text(json.dumps(data),encoding='utf-8')
    return data,manifest


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.folder=Path(self.tmp.name)
        self.data,self.manifest=fixture(self.folder)
    def tearDown(self):
        self.tmp.cleanup()
    def save(self):
        self.manifest.write_text(json.dumps(self.data),encoding='utf-8')
    def assert_blocked(self):
        self.save()
        with self.assertRaises(ActivityError): load_plan(self.manifest)


class GeometryTests(FixtureTest):
    def test_shared_size_and_shape(self):
        plan=load_plan(self.manifest); sheets=pack_cutouts(plan)
        for target,piece in zip(plan['activities'][0]['pieces'],sheets[0]):
            self.assertEqual(compare_pair(target,piece),[])
        self.assertAlmostEqual(sheets[0][0]['width_mm'],320/1800*142)
    def test_mutations_detected(self):
        original=load_plan(self.manifest)['activities'][0]['pieces'][0]
        for change in [{'width_mm':50},{'height_mm':50},{'rotation':90},{'flip':True},
                       {'outline':'ellipse'},{'source_sha256':'wrong'},{'crop_px':[0,0,320,400]},{'id':'wrong'}]:
            with self.subTest(change=change):
                mutated={**original,**change}; self.assertTrue(compare_pair(original,mutated))
    def test_double_size_manifest_field_rejected(self):
        self.data['activities'][0]['pieces'][0]['width_mm']=50; self.assert_blocked()
    def test_flip_field_rejected(self):
        self.data['activities'][0]['pieces'][0]['flip']=True; self.assert_blocked()
    def test_duplicate_piece_rejected(self):
        self.data['activities'][0]['pieces'][1]['id']='a'; self.assert_blocked()
    def test_missing_piece_list_rejected(self):
        self.data['activities'][0]['pieces']=[]; self.assert_blocked()
    def test_outside_crop_rejected(self):
        self.data['activities'][0]['pieces'][0]['crop_px'][0]=1799; self.assert_blocked()
    def test_overlapping_crops_rejected(self):
        self.data['activities'][0]['pieces'][1]['crop_px']=[190,190,360,300]; self.assert_blocked()
    def test_small_piece_rejected(self):
        self.data['activities'][0]['pieces'][0]['crop_px'][2]=20; self.assert_blocked()
    def test_low_resolution_rejected(self):
        self.data['page']={'min_dpi':600}; self.assert_blocked()
    def test_inside_margin_rejected(self):
        self.data['activities'][0]['scene']['x_mm']=10; self.assert_blocked()
    def test_nan_dimensions_rejected(self):
        self.data['activities'][0]['scene']['width_mm']=float('nan'); self.assert_blocked()
    def test_self_crossing_outline_rejected(self):
        with self.assertRaises(ActivityError): outline([[0,0],[1,1],[1,0],[0,1]])
    def test_pack_does_not_resize_large_piece(self):
        plan=load_plan(self.manifest); plan['activities'][0]['pieces'][0]['width_mm']=170
        with self.assertRaises(ActivityError): pack_cutouts(plan)
    def test_pack_more_than_one_sheet(self):
        plan=load_plan(self.manifest)
        plan['activities']*=12
        sheets=pack_cutouts(plan)
        self.assertGreater(len(sheets),1)
        self.assertEqual(sum(map(len,sheets)),36)


class PDFTests(FixtureTest):
    def test_real_book_and_blank_backs(self):
        files,report=build_book(self.manifest,self.folder/'book.pdf')
        self.assertEqual(report['status'],'machine_pass'); self.assertEqual(report['page_count'],4)
        self.assertEqual(report['appendix_start'],3); self.assertEqual(report['blank_pages'],[2,4])
        self.assertTrue(report['unverified'])
        check=audit_pdf(files['book'],expected_size_mm=(182,257),expected_pages=4,blank_pages=[2,4],min_image_dpi=300)
        self.assertEqual(check['errors'],[])
    def test_wrong_page_size_and_count_rejected(self):
        files,_=build_book(self.manifest,self.folder/'book.pdf')
        result=audit_pdf(files['book'],expected_size_mm=(210,297),expected_pages=99)
        self.assertEqual(result['status'],'blocked'); self.assertGreaterEqual(len(result['errors']),5)
    def test_actual_pdf_detects_changed_outline_drawing(self):
        from textbuilder import cut_paste
        correct=cut_paste._outline
        def wrong(canvas,piece,x,y):
            if piece['outline']=='ellipse':
                return correct(canvas,{**piece,'width_mm':piece['width_mm']*2},x,y)
            return correct(canvas,piece,x,y)
        with patch.object(cut_paste,'_outline',side_effect=wrong):
            with self.assertRaisesRegex(ActivityError,'실제 PDF 윤곽'):
                build_book(self.manifest,self.folder/'book.pdf')
        self.assertFalse((self.folder/'book.pdf').exists())
    def test_actual_pdf_detects_one_missing_cutout(self):
        from textbuilder import cut_paste
        original=cut_paste._dotted
        def omit_one(canvas,piece,x,y):
            if 'cutouts' in str(canvas._filename) and piece['id']=='b':
                return
            return original(canvas,piece,x,y)
        with patch.object(cut_paste,'_dotted',side_effect=omit_one):
            with self.assertRaisesRegex(ActivityError,'점선 수 불일치'):
                build_book(self.manifest,self.folder/'book.pdf')
    def test_cut_front_cannot_be_claimed_blank(self):
        files,_=build_book(self.manifest,self.folder/'book.pdf')
        self.assertEqual(audit_pdf(files['book'],blank_pages=[3])['status'],'blocked')
    def test_empty_and_non_pdf_rejected(self):
        for payload in (b'',b'not a PDF'):
            path=self.folder/'bad.pdf'; path.write_bytes(payload)
            self.assertEqual(audit_pdf(path)['status'],'blocked')
    def test_prefix_alignment_and_labels(self):
        for count in (1,2):
            writer=PdfWriter()
            for _ in range(count): writer.add_blank_page(width=182*72/25.4,height=257*72/25.4)
            prefix=self.folder/f'prefix{count}.pdf'
            with prefix.open('wb') as out: writer.write(out)
            files,report=build_book(self.manifest,self.folder/f'book{count}.pdf',body_pdf=prefix)
            self.assertEqual(report['appendix_start']%2,1)
            with fitz.open(files['cutouts']) as pdf:
                self.assertIn(f'p. {count+1}',pdf[0].get_text())
    def test_existing_output_preserved_on_failure(self):
        path=self.folder/'book.pdf'; path.write_bytes(b'previous approved file')
        self.data['activities'][0]['pieces'][0]['flip']=True; self.save()
        with self.assertRaises(ActivityError): build_book(self.manifest,path)
        self.assertEqual(path.read_bytes(),b'previous approved file')
    def test_changed_bundle_is_detected(self):
        from scripts.qc_print import verify_bundle
        files,_=build_book(self.manifest,self.folder/'book.pdf')
        self.assertEqual(verify_bundle(files['report'],self.manifest),[])
        Path(files['cutouts']).write_bytes(b'changed')
        self.assertTrue(verify_bundle(files['report'],self.manifest))
    def test_changed_source_is_detected(self):
        from scripts.qc_print import verify_bundle
        files,_=build_book(self.manifest,self.folder/'book.pdf')
        image=Image.open(self.folder/'scene.png'); image.putpixel((0,0),(0,0,0)); image.save(self.folder/'scene.png'); image.close()
        self.assertTrue(verify_bundle(files['report'],self.manifest))
    def test_assembled_pixels_restore_original(self):
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.units import mm
        files,_=build_book(self.manifest,self.folder/'book.pdf')
        baseline=self.folder/'baseline.pdf'; c=Canvas(str(baseline),pagesize=(182*mm,257*mm))
        c.drawImage(str(self.folder/'scene.png'),20*mm,(257-55-142*1200/1800)*mm,width=142*mm,height=142*1200/1800*mm)
        c.showPage(); c.save()
        clip=fitz.Rect(21*mm,56*mm,161*mm,(55+142*1200/1800-1)*mm)
        with fitz.open(files['assembled']) as a,fitz.open(baseline) as b:
            pa=a[0].get_pixmap(dpi=144,clip=clip); pb=b[0].get_pixmap(dpi=144,clip=clip)
            ia=Image.frombytes('RGB',(pa.width,pa.height),pa.samples)
            ib=Image.frombytes('RGB',(pb.width,pb.height),pb.samples)
            histogram=ImageChops.difference(ia,ib).convert('L').histogram()
            bad=sum(histogram[10:]); total=pa.width*pa.height
            self.assertLess(bad/total,.005)


class ExportRegressionTests(unittest.TestCase):
    def test_font_override_reaches_template(self):
        from textbuilder.typst_gen import document_data
        doc=BookDocument(theme='kids-card-purple'); doc.metadata.extra['font_override']='Chosen Test Font'
        data,_=document_data(doc)
        self.assertEqual(data['theme']['fonts']['body'][0],'Chosen Test Font')
    def test_final_rejects_wrong_real_pdf_and_preserves_previous(self):
        doc=BookDocument(metadata=Metadata(title='test'),pages=[Page(blocks=[blk('text',text='test')])])
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'out.pdf'; output.write_bytes(b'previous')
            def compile_stub(cmd,**kw):
                writer=PdfWriter(); writer.add_blank_page(width=210*72/25.4,height=297*72/25.4)
                with open(cmd[-1],'wb') as stream: writer.write(stream)
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            renderer=TypstRenderer(exe='stub')
            with patch.object(renderer,'available',return_value=(True,'')),patch('textbuilder.renderers.typst_cli.generate',return_value=('source',[])),patch('textbuilder.renderers.typst_cli.subprocess.run',side_effect=compile_stub):
                result=renderer.render(doc,RenderOptions(out_path=str(output),final=True))
            self.assertFalse(result.ok); self.assertEqual(output.read_bytes(),b'previous')
            self.assertEqual(json.loads(Path(str(output)+'.qc.json').read_text())['status'],'blocked')
    def test_final_accepts_valid_pdf_and_reports_actual_count(self):
        doc=BookDocument(metadata=Metadata(title='test'),pages=[Page(blocks=[blk('text',text='test')])])
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'out.pdf'
            def compile_stub(cmd,**kw):
                writer=PdfWriter(); writer.add_blank_page(width=182*72/25.4,height=257*72/25.4)
                with open(cmd[-1],'wb') as stream: writer.write(stream)
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            renderer=TypstRenderer(exe='stub')
            with patch.object(renderer,'available',return_value=(True,'')),patch('textbuilder.renderers.typst_cli.generate',return_value=('source',[])),patch('textbuilder.renderers.typst_cli.subprocess.run',side_effect=compile_stub):
                result=renderer.render(doc,RenderOptions(out_path=str(output),final=True))
            self.assertTrue(result.ok); self.assertEqual(result.meta['pages'],1)
            self.assertEqual(audit_pdf(output)['status'],'machine_pass')
    def test_normalized_json_page_size_override(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'book.json'; path.write_text(BookDocument().to_json())
            self.assertEqual(load(str(path),page_size='A4').dimensions_mm(),(210,297))
    def test_custom_size_must_be_positive(self):
        doc=BookDocument(); doc.page_setup.size='custom'; doc.page_setup.width_mm=-1; doc.page_setup.height_mm=257
        self.assertTrue(doc.validate())
    def test_final_blocks_warnings_before_compiler(self):
        doc=BookDocument(); renderer=TypstRenderer(exe='stub')
        with patch.object(renderer,'available',return_value=(True,'')),patch('textbuilder.renderers.typst_cli.generate',return_value=('source',['missing image'])),patch('textbuilder.renderers.typst_cli.subprocess.run') as run:
            result=renderer.render(doc,RenderOptions(final=True))
            self.assertFalse(result.ok); run.assert_not_called()
    def test_empty_output_is_not_success(self):
        doc=BookDocument(metadata=Metadata(title='test'),pages=[Page(blocks=[blk('text',text='test')])])
        with tempfile.TemporaryDirectory() as td:
            def compile_stub(cmd,**kw): Path(cmd[-1]).touch(); return SimpleNamespace(returncode=0,stdout='',stderr='')
            renderer=TypstRenderer(exe='stub')
            with patch.object(renderer,'available',return_value=(True,'')),patch('textbuilder.renderers.typst_cli.generate',return_value=('source',[])),patch('textbuilder.renderers.typst_cli.subprocess.run',side_effect=compile_stub):
                self.assertFalse(renderer.render(doc,RenderOptions(out_path=str(Path(td)/'out.pdf'))).ok)
    def test_crop_is_materialized_and_size_kept(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as td:
            source=Path(td)/'source.png'; image=Image.new('RGB',(100,100),'red'); ImageDraw.Draw(image).rectangle((50,0,99,99),fill='blue'); image.save(source)
            doc=BookDocument(source=str(source),assets_root=td)
            warnings=[]
            result=block_data(doc,blk('image',src='source.png',attrs={'crop':[.5,0,.5,1],'width':'25mm','height':'5cm'}),warnings)
            self.assertEqual(warnings,[]); self.assertEqual(result['width_mm'],25); self.assertEqual(result['height_mm'],50)
            with Image.open(Path(REPO_ROOT)/result['src'].lstrip('/')) as cropped:
                self.assertEqual(cropped.size,(50,100)); self.assertEqual(cropped.getpixel((0,0)),(0,0,255))


if __name__=='__main__':
    (ROOT/'build').mkdir(exist_ok=True)
    unittest.main()
