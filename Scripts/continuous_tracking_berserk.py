"""One-time migration: continuous locked attack tracking and red phase-3 Khaimera look."""
import json
from pathlib import Path
import unreal

COMBAT='/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/BPC_Combat'
BOSS='/Game/AI/BP_Boss'; GRAPH='EventGraph'; S=unreal.BlueprintService
OUT=Path(unreal.Paths.project_saved_dir())/'TrackingBerserkBackup_20260930'; MAP=OUT/'nodes.json'
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(),'Already applied'
OUT.mkdir(parents=True,exist_ok=True)

def save(path):
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)),path
    assert unreal.EditorAssetLibrary.save_asset(path),path
def build(path,nodes,edges,defaults=[]):
    r=S.build_graph(path,GRAPH,nodes,edges,defaults,False,False)
    print('BUILD',path,r.success,list(r.errors),list(r.warnings))
    assert r.success and not r.errors and not r.warnings
    return dict(r.ref_to_node_id)

# Root-motion attacks keep turning toward the locked target for their whole duration.
tick=next(n.node_id for n in S.get_nodes_in_graph(COMBAT,GRAPH,0,'',False) if n.node_title=='Event Tick')
tracking=build(COMBAT,[
 {'ref':'Attacking','type':'variable_get','params':{'variable':'bIsAttacking'}},
 {'ref':'Gate','type':'branch','params':{}},
 {'ref':'Face','type':'function_call','params':{'class':'BPC_Combat_C','function':'FaceAttackTarget'}},
],[
 {'from_':tick+'.then','to':'Gate.execute'}, {'from_':'Attacking.bIsAttacking','to':'Gate.Condition'},
 {'from_':'Gate.then','to':'Face.execute'},
])
save(COMBAT)

# Create and compile the phase visual event before calling it.
event=build(BOSS,[{'ref':'Event','type':'custom_event','params':{'name':'ApplyBerserkLook'}}],[])
event_id=event['Event'];save(BOSS)
nodes=[
 {'ref':'Mesh','type':'member_get','params':{'class':'Character','member':'Mesh'}},
]
edges=[];defaults=[];previous=event_id+'.then'
colors=[
 ('Skin','SkinColor','(R=1.0,G=0.035,B=0.015,A=1.0)'),
 ('Base','BaseColortint','(R=0.62,G=0.025,B=0.012,A=1.0)'),
 ('Paint','BodyPaintTint','(R=1.0,G=0.02,B=0.005,A=1.0)'),
 ('GlowIn','PassiveGlow_Color_In','(R=1.0,G=0.0,B=0.0,A=1.0)'),
 ('GlowOut','PassiveGlow_Color_Out','(R=1.0,G=0.11,B=0.015,A=1.0)'),
 ('Emissive','EmissiveColor','(R=1.0,G=0.015,B=0.0,A=1.0)'),
]
for ref,param,value in colors:
    nodes.append({'ref':ref,'type':'function_call','params':{'class':'MeshComponent','function':'SetVectorParameterValueOnMaterials'}})
    edges += [{'from_':previous,'to':ref+'.execute'},{'from_':'Mesh.Mesh','to':ref+'.self'}]
    defaults += [{'node_ref':ref,'pin_name':'ParameterName','value':param},{'node_ref':ref,'pin_name':'ParameterValue','value':value}]
    previous=ref+'.then'
for ref,param,value in [('GlowPower','PassiveGlow_Intensity',5.0),('SkinGlow','GlowIntensity',4.0),('Weapons','Weapons_Glow',1.0),('Ult','UltEmissiveON',1.0)]:
    nodes.append({'ref':ref,'type':'function_call','params':{'class':'MeshComponent','function':'SetScalarParameterValueOnMaterials'}})
    edges += [{'from_':previous,'to':ref+'.execute'},{'from_':'Mesh.Mesh','to':ref+'.self'}]
    defaults += [{'node_ref':ref,'pin_name':'ParameterName','value':param},{'node_ref':ref,'pin_name':'ParameterValue','value':str(value)}]
    previous=ref+'.then'
berserk_body=build(BOSS,nodes,edges,defaults);save(BOSS)

phase_branch='C47059784D761649ED59F6AA0B1AB852';show_left='CA16F5824C19E72B83D6FA9C887781FE'
assert S.disconnect_pin(BOSS,GRAPH,phase_branch,'else')
berserk_call=build(BOSS,[{'ref':'Call','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplyBerserkLook'}}],[
 {'from_':phase_branch+'.else','to':'Call.execute'},{'from_':'Call.then','to':show_left+'.execute'}])
save(BOSS)

MAP.write_text(json.dumps({'tracking':tracking,'berserk_event':event_id,'berserk_body':berserk_body,'berserk_call':berserk_call},indent=2),encoding='utf-8')
print('CONTINUOUS_TRACKING_BERSERK_APPLIED')
