"""Resume main-menu migration after dependency ordering stopped the first pass."""
import json
from pathlib import Path
import unreal
S=unreal.BlueprintService;G='EventGraph'
P='/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/BP_DarkKnight_Alert'
E='/Game/AI/BP_Enemy';B='/Game/AI/BP_Boss';W='/Game/UI/WBP_MainMenu'
MAP=Path(unreal.Paths.project_saved_dir())/'MainMenuBackup_20260930'/'nodes.json'
assert not MAP.exists()

def save(path):
 assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)),path
 assert unreal.EditorAssetLibrary.save_asset(path),path
def build(path,nodes,edges,defaults=()):
 r=S.build_graph(path,G,nodes,edges,list(defaults),False,False)
 print('BUILD',path,r.success,list(r.errors),list(r.warnings));assert r.success and not r.errors
 return dict(r.ref_to_node_id)

def add_difficulty(path,easy_hp,normal_hp,hard_hp,easy_dmg,normal_dmg,hard_dmg):
 owner=path.rsplit('/',1)[1]+'_C'
 nodes=[
  {'ref':'Event','type':'custom_event','params':{'name':'ApplySelectedDifficulty'}},
  {'ref':'Player','type':'function_call','params':{'class':'GameplayStatics','function':'GetPlayerCharacter'}},
  {'ref':'Cast','type':'cast','params':{'target_class':'BP_DarkKnight_Alert_C'}},
  {'ref':'Difficulty','type':'member_get','params':{'class':'BP_DarkKnight_Alert_C','member':'DifficultyLevel'}},
  {'ref':'Easy','type':'comparison','params':{'operation':'Equal','operand_type':'Int'}},
  {'ref':'Hard','type':'comparison','params':{'operation':'Equal','operand_type':'Int'}},
  {'ref':'HpNH','type':'function_call','params':{'class':'KismetMathLibrary','function':'SelectFloat'}},
  {'ref':'HpFinal','type':'function_call','params':{'class':'KismetMathLibrary','function':'SelectFloat'}},
  {'ref':'DmgNH','type':'function_call','params':{'class':'KismetMathLibrary','function':'SelectFloat'}},
  {'ref':'DmgFinal','type':'function_call','params':{'class':'KismetMathLibrary','function':'SelectFloat'}},
  {'ref':'Stats','type':'member_get','params':{'class':owner,'member':'StatComponent'}},
  {'ref':'Combat','type':'member_get','params':{'class':owner,'member':'CombatComponent'}},
  {'ref':'Max','type':'member_set','params':{'class':'BPC_Stat_C','member':'MaxHealth'}},
  {'ref':'Current','type':'member_set','params':{'class':'BPC_Stat_C','member':'CurrentHealth'}},
  {'ref':'Damage','type':'member_set','params':{'class':'BPC_Combat_C','member':'AttackDamage'}},
 ]
 edges=[
  {'from_':'Event.then','to':'Player.execute'},{'from_':'Player.then','to':'Cast.execute'},{'from_':'Player.ReturnValue','to':'Cast.Object'},
  {'from_':'Cast.AsBP Dark Knight Alert','to':'Difficulty.self'},{'from_':'Difficulty.DifficultyLevel','to':'Easy.A'},
  {'from_':'Difficulty.DifficultyLevel','to':'Hard.A'},{'from_':'Hard.ReturnValue','to':'HpNH.bPickA'},
  {'from_':'HpNH.ReturnValue','to':'HpFinal.B'},{'from_':'Easy.ReturnValue','to':'HpFinal.bPickA'},
  {'from_':'Hard.ReturnValue','to':'DmgNH.bPickA'},{'from_':'DmgNH.ReturnValue','to':'DmgFinal.B'},
  {'from_':'Easy.ReturnValue','to':'DmgFinal.bPickA'},{'from_':'Stats.StatComponent','to':'Max.self'},
  {'from_':'Stats.StatComponent','to':'Current.self'},{'from_':'Combat.CombatComponent','to':'Damage.self'},
  {'from_':'HpFinal.ReturnValue','to':'Max.MaxHealth'},{'from_':'HpFinal.ReturnValue','to':'Current.CurrentHealth'},
  {'from_':'DmgFinal.ReturnValue','to':'Damage.AttackDamage'},{'from_':'Cast.then','to':'Max.execute'},
  {'from_':'Max.then','to':'Current.execute'},{'from_':'Current.then','to':'Damage.execute'},
 ]
 vals=[('Player','PlayerIndex',0),('Easy','B',0),('Hard','B',2),('HpNH','A',hard_hp),('HpNH','B',normal_hp),('HpFinal','A',easy_hp),('DmgNH','A',hard_dmg),('DmgNH','B',normal_dmg),('DmgFinal','A',easy_dmg)]
 ids=build(path,nodes,edges,[{'node_ref':a,'pin_name':b,'value':str(c)} for a,b,c in vals]);save(path);return ids

enemy=add_difficulty(E,60,75,105,10,15,21)
boss=add_difficulty(B,320,400,520,15,20,28)

# Add calls that could not resolve before those events existed.
player_nodes=build(P,[
 {'ref':'EnemyApply','type':'function_call','params':{'class':'BP_Enemy_C','function':'ApplySelectedDifficulty'}},
 {'ref':'BossApply','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplySelectedDifficulty'}},
],[])
# Identify the new player casts by following the custom-event chain.
ev=next(n.node_id for n in S.get_nodes_in_graph(P,G,0,'',True) if n.node_title=='ApplySelectedDifficulty')
def next_exec(node,pin='then'):
 d=S.get_node_details(P,G,node)
 p=next(p for p in d.output_pins if p.pin_name==pin);return str(p.connections[0]).split(':')[0]
get_enemy=next_exec(ev);cast_enemy=next_exec(get_enemy);get_boss=next_exec(cast_enemy,'CastFailed');cast_boss=next_exec(get_boss)
assert S.connect_nodes(P,G,cast_enemy,'then',player_nodes['EnemyApply'],'execute')
assert S.connect_nodes(P,G,cast_enemy,'AsBP Enemy',player_nodes['EnemyApply'],'self')
assert S.connect_nodes(P,G,player_nodes['EnemyApply'],'then',get_boss,'execute')
assert S.connect_nodes(P,G,cast_boss,'then',player_nodes['BossApply'],'execute')
assert S.connect_nodes(P,G,cast_boss,'AsBP Boss',player_nodes['BossApply'],'self')
save(P)

# Apply boss settings on spawn, after the historical fixed values.
last='DE0D2FB748485CF58B3EBD85D2FE464F'
d=S.get_node_details(B,G,last);fixed=str(next(p for p in d.output_pins if p.pin_name=='then').connections[0]).split(':')[0]
boss_begin=build(B,[{'ref':'Call','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplySelectedDifficulty'}}],[{'from_':fixed+'.then','to':'Call.execute'}]);save(B)

# Player title overlay.
assert S.add_member_variable(P,'MainMenuClass','TSubclassOf<UserWidget>','/Game/UI/WBP_MainMenu.WBP_MainMenu_C')
menu=build(P,[
 {'ref':'MenuClass','type':'variable_get','params':{'variable':'MainMenuClass'}},
 {'ref':'Create','type':'function_call','params':{'class':'WidgetBlueprintLibrary','function':'Create'}},
 {'ref':'Add','type':'function_call','params':{'class':'UserWidget','function':'AddToViewport'}},
 {'ref':'Cursor','type':'member_set','params':{'class':'PlayerController','member':'bShowMouseCursor'}},
 {'ref':'Pause','type':'function_call','params':{'class':'GameplayStatics','function':'SetGamePaused'}},
],[
 {'from_':'7F61B89C4B63D61E54D30CAAB7168C8F.then','to':'Create.execute'},{'from_':'MenuClass.MainMenuClass','to':'Create.WidgetType'},
 {'from_':'6735982747F8038958B94AA5B1B163E9.AsPlayer Controller','to':'Create.OwningPlayer'},
 {'from_':'Create.then','to':'Add.execute'},{'from_':'Create.ReturnValue','to':'Add.self'},{'from_':'Add.then','to':'Cursor.execute'},
 {'from_':'6735982747F8038958B94AA5B1B163E9.AsPlayer Controller','to':'Cursor.self'},{'from_':'Cursor.then','to':'Pause.execute'},
],[{'node_ref':'Add','pin_name':'ZOrder','value':'100'},{'node_ref':'Cursor','pin_name':'bShowMouseCursor','value':'true'},{'node_ref':'Pause','pin_name':'bPaused','value':'true'}]);save(P)

widget={}
for name,level in [('SelectEasy',0),('SelectNormal',1),('SelectHard',2)]:
 ids=build(W,[
  {'ref':'Event','type':'custom_event','params':{'name':name}}, {'ref':'Player','type':'function_call','params':{'class':'GameplayStatics','function':'GetPlayerCharacter'}},
  {'ref':'Cast','type':'cast','params':{'target_class':'BP_DarkKnight_Alert_C'}},{'ref':'Set','type':'member_set','params':{'class':'BP_DarkKnight_Alert_C','member':'DifficultyLevel'}},
  {'ref':'Apply','type':'function_call','params':{'class':'BP_DarkKnight_Alert_C','function':'ApplySelectedDifficulty'}},
  {'ref':'Controller','type':'function_call','params':{'class':'UserWidget','function':'GetOwningPlayer'}},{'ref':'Cursor','type':'member_set','params':{'class':'PlayerController','member':'bShowMouseCursor'}},
  {'ref':'Unpause','type':'function_call','params':{'class':'GameplayStatics','function':'SetGamePaused'}},{'ref':'Self','type':'spawner_key','params':{'key':'NODE K2Node_Self'}},
  {'ref':'Remove','type':'function_call','params':{'class':'Widget','function':'RemoveFromParent'}},
 ],[
  {'from_':'Event.then','to':'Player.execute'},{'from_':'Player.then','to':'Cast.execute'},{'from_':'Player.ReturnValue','to':'Cast.Object'},
  {'from_':'Cast.then','to':'Set.execute'},{'from_':'Cast.AsBP Dark Knight Alert','to':'Set.self'},{'from_':'Set.then','to':'Apply.execute'},
  {'from_':'Cast.AsBP Dark Knight Alert','to':'Apply.self'},{'from_':'Apply.then','to':'Controller.execute'},{'from_':'Controller.then','to':'Cursor.execute'},
  {'from_':'Controller.ReturnValue','to':'Cursor.self'},{'from_':'Cursor.then','to':'Unpause.execute'},{'from_':'Unpause.then','to':'Remove.execute'},{'from_':'Self.self','to':'Remove.self'},
 ],[{'node_ref':'Player','pin_name':'PlayerIndex','value':'0'},{'node_ref':'Set','pin_name':'DifficultyLevel','value':str(level)},{'node_ref':'Cursor','pin_name':'bShowMouseCursor','value':'false'},{'node_ref':'Unpause','pin_name':'bPaused','value':'false'}])
 widget[name]=ids
save(W)
for button,event in [('EasyButton','SelectEasy'),('NormalButton','SelectNormal'),('HardButton','SelectHard')]:assert unreal.WidgetService.bind_event(W,button,'OnClicked',event)
save(W)
MAP.write_text(json.dumps({'enemy':enemy,'boss':boss,'player_calls':player_nodes,'boss_begin':boss_begin,'menu':menu,'widget':widget},indent=2),encoding='utf-8')
print('MAIN_MENU_DIFFICULTY_REPAIRED')
