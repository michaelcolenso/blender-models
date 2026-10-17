"""Editable full-frame VSE cut, retaining the source-derived 3D installation scenes."""
import hashlib
import json
import shutil
from pathlib import Path

import bpy

import compose_immersive as film

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
SOURCE=OUT/'media/source-3D.blend'

def geometry(obj):
    if obj.type=='CURVE':data={'points':[[list(p.co) for p in s.points] for s in obj.data.splines],'radius':obj.data.bevel_depth}
    elif obj.type=='MESH':data={'vertices':[list(v.co) for v in obj.data.vertices]}
    else:return None
    data['transform']=[list(obj.location),list(obj.rotation_euler),list(obj.scale)]
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def curves_linear():
    for action in bpy.data.actions:
        if not action.name.startswith('Immersive'):continue
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:key.interpolation='LINEAR'

def build():
    if not SOURCE.exists():shutil.copy2(ROOT.parent/'studio-upgrade/output/Highland-studio-upgrade.blend',SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    original={sc.name:{o.name:geometry(o) for o in sc.objects if o.get('element_id') and o.type in {'CURVE','MESH'}} for sc in bpy.data.scenes}
    master=bpy.data.scenes.new('MASTER - Immersive film')
    bpy.context.window.scene=master
    master.render.resolution_x=film.W;master.render.resolution_y=film.H;master.render.resolution_percentage=100
    master.render.fps=24;master.frame_start=1;master.frame_end=2160;master.render.use_sequencer=True
    master.view_settings.view_transform='Standard';master.view_settings.look='None'
    master.sequencer_colorspace_settings.name='sRGB'
    editor=master.sequence_editor_create();strips=editor.strips
    paper=strips.new_effect(name='Continuous warm field',type='COLOR',channel=1,frame_start=1,length=2160)
    paper.color=tuple(int(film.D['paper'][k:k+2],16)/255 for k in (1,3,5))
    plate=strips.new_movie(name='Clean model plate - no inset',filepath=str(OUT/'media/model-90s.mp4'),channel=2,frame_start=1,fit_method='ORIGINAL')
    plate.frame_final_duration=2160;plate.blend_type='ALPHA_OVER'
    for f in range(1,2161):
        z,cx,cy=film.reframe((f-1)/24)
        plate.transform.scale_x=film.W/960*z;plate.transform.scale_y=film.W/960*z
        plate.transform.offset_x=(.5-cx)*film.W*z;plate.transform.offset_y=(cy-.5)*film.H*z
        for prop in ['scale_x','scale_y','offset_x','offset_y']:plate.transform.keyframe_insert(prop,frame=f)
    audio=strips.new_sound(name='Approved narration and score',filepath=str(OUT/'media/approved-audio.m4a'),channel=3,frame_start=1)
    audio.frame_final_duration=2160
    groups={}
    for f in range(2160):
        for event in film.frame_events(f/24):
            if event['type']!='text':continue
            groups.setdefault((event['id'],event['text']),[]).append((f+1,event))
    # Titles never overlap each other. Four shared tracks carry title, detail,
    # context and the permanent footer; no framing graphics surround the model.
    for (label,_),frames in groups.items():
        event=frames[0][1]
        if label=='footer':channel=20
        elif label.startswith('legend-'):channel=12+['Cold','Hot','Return','Access'].index(label[7:])
        elif label in {'flow-meaning','exceptions','required-hold'}:channel=11
        elif label.endswith('-detail'):channel=9
        else:channel=8
        text=strips.new_effect(name='Immersive '+label,type='TEXT',channel=channel,frame_start=frames[0][0],length=frames[-1][0]-frames[0][0]+1)
        text.text=event['text'];text.font=bpy.data.fonts.load(str(film.SANS if event['sans'] else film.SERIF),check_existing=True)
        text.anchor_x='LEFT';text.anchor_y='TOP';text.alignment_x='LEFT';text.use_shadow=False
        text.color=tuple(int(event['color'][k:k+2],16)/255 for k in (1,3,5))+(1,)
        for f,e in frames:
            text.location=(e['x']/film.W,1-e['y']/film.H);text.font_size=round(e['size']);text.blend_alpha=e['alpha']
            for prop in ['location','font_size','blend_alpha']:text.keyframe_insert(prop,frame=f)
    for sc in bpy.data.scenes:
        for obj in sc.objects:
            if obj.get('element_id') and obj.type in {'CURVE','MESH'} and sc.name in original:
                assert geometry(obj)==original[sc.name][obj.name],obj.name
    assert plate.frame_final_start==1 and plate.frame_final_end==2161
    assert max(s.channel for s in strips)<128
    for t,title in [(0,'Exterior'),(8,'Verify and protect'),(18,'Open and prepare'),(29,'Install replacement'),(45,'Test and inspect'),(58,'Transfer service'),(67,'Commission circulation'),(73,'Restore'),(85,'Whole system')]:
        master.timeline_markers.new(title,frame=round(t*24)+1)
    master['presentation']='Full-frame architectural film. Titles sit near the work; no inset, sidebar, border or progress rails.'
    master['picture_source']='Validated 960x540 Cycles plate, two native scene samples/second interpolated to 24 fps; 1080p editorial composition.'
    master['edit_note']='Movie plate and titles are editable in this master. Original source-derived 3D scenes retain their full camera/piping animations; re-render those scenes for new model imagery.'
    if master.animation_data and master.animation_data.action:master.animation_data.action.name='Immersive editorial motion'
    curves_linear()
    for t in [1.8,6.2,33.5,55.5,60.5,69.5,88]:
        f=round(t*24)+1;master.frame_set(f)
        expected={e['text'] for e in film.frame_events((f-1)/24) if e['type']=='text' and e['alpha']>.1}
        actual={s.text for s in strips if s.type=='TEXT' and s.frame_final_start<=f<s.frame_final_end and s.blend_alpha>.1}
        assert expected==actual,(t,expected-actual,actual-expected)
    master.frame_set(1)
    for area in bpy.context.window.screen.areas:
        if area.type=='VIEW_3D':
            area.type='SEQUENCE_EDITOR';area.spaces.active.view_type='SEQUENCER_PREVIEW'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative()
    target=OUT/'Highland-immersive-editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target))
    (OUT/'blender-validation.json').write_text(json.dumps({'passed':True,'source_3D_geometry_unchanged':True,'source_objects_compared':{k:len(v) for k,v in original.items()},
       'master_picture_range':[1,2161],'master_frame_size':[1920,1080],'max_vse_channel':max(s.channel for s in strips),'title_text_and_intervals_match_film':True,
       'layout':'Full-frame movie and unboxed editable title strips; original 3D scenes retained.'},indent=2)+'\n')
    print('IMMERSIVE_EDITABLE_READY',target,flush=True)

if __name__=='__main__':build()
