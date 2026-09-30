"""Finish the partially-created berserk graph with typed LinearColor nodes."""
import json
from pathlib import Path
import unreal

BOSS='/Game/AI/BP_Boss'; G='EventGraph'; S=unreal.BlueprintService
OUT=Path(unreal.Paths.project_saved_dir())/'TrackingBerserkBackup_20260930'; MAP=OUT/'nodes.json'
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(),'Already repaired'

targets={
 'Skin':('AF5A3F634522560000961DAB3BA98BDF',(1.0,.035,.015,1.0)),
 'Base':('67A66D8C4E22990CBCEC65AC45CCF8DB',(.62,.025,.012,1.0)),
 'Paint':('1FE70E8D4650513B15C88A8F6FB6E9B0',(1.0,.02,.005,1.0)),
 'GlowIn':('6B690B8A4D1FC87ED1E3ED8F1AAB9225',(1.0,0.0,0.0,1.0)),
 'GlowOut':('8C6E484C45643B822B9DE6B80A27B08D',(1.0,.11,.015,1.0)),
 'Emissive':('B585518644D26867BDA25E8C91DBDD96',(1.0,.015,0.0,1.0)),
}
nodes=[];edges=[];defaults=[]
for ref,(target,rgba) in targets.items():
    nodes.append({'ref':'Color'+ref,'type':'function_call','params':{'class':'KismetMathLibrary','function':'MakeColor'}})
    edges.append({'from_':'Color'+ref+'.ReturnValue','to':target+'.ParameterValue'})
    for pin,value in zip(['R','G','B','A'],rgba):defaults.append({'node_ref':'Color'+ref,'pin_name':pin,'value':str(value)})
r=S.build_graph(BOSS,G,nodes,edges,defaults,False,False)
print('COLOR_REPAIR',r.success,list(r.errors),list(r.warnings));assert r.success and not r.errors and not r.warnings
assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(BOSS));assert unreal.EditorAssetLibrary.save_asset(BOSS)
phase='C47059784D761649ED59F6AA0B1AB852';show='CA16F5824C19E72B83D6FA9C887781FE'
assert S.disconnect_pin(BOSS,G,phase,'else')
call=S.build_graph(BOSS,G,[{'ref':'Call','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplyBerserkLook'}}],[
 {'from_':phase+'.else','to':'Call.execute'},{'from_':'Call.then','to':show+'.execute'}],[],False,False)
print('BERSERK_CALL',call.success,list(call.errors),list(call.warnings));assert call.success and not call.errors and not call.warnings
assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(BOSS));assert unreal.EditorAssetLibrary.save_asset(BOSS)
MAP.write_text(json.dumps({'tracking_saved':True,'berserk_event':'4266B80045DD0D8D57D45088635BB9F2','colors':dict(r.ref_to_node_id),'call':dict(call.ref_to_node_id)},indent=2),encoding='utf-8')
print('BERSERK_COLORS_REPAIRED')
