"""One-time migration: functional title menu and three gameplay difficulties."""
import json, shutil
from pathlib import Path
import unreal

S=unreal.BlueprintService; G='EventGraph'
P='/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/BP_DarkKnight_Alert'
E='/Game/AI/BP_Enemy'; B='/Game/AI/BP_Boss'; W='/Game/UI/WBP_MainMenu'
OUT=Path(unreal.Paths.project_saved_dir())/'MainMenuBackup_20260930'; MAP=OUT/'nodes.json'
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
assert not MAP.exists(),'Already applied'
OUT.mkdir(parents=True,exist_ok=True)
for path in [P,E,B,W]:
    src=Path(unreal.Paths.project_content_dir())/Path(path.removeprefix('/Game/')+'.uasset')
    shutil.copy2(src,OUT/src.name)

def save(path):
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)),path
    assert unreal.EditorAssetLibrary.save_asset(path),path
def build(path,nodes,edges,defaults=()):
    r=S.build_graph(path,G,nodes,edges,list(defaults),False,False)
    print(path,r.success,list(r.errors),list(r.warnings));assert r.success and not r.errors and not r.warnings
    return dict(r.ref_to_node_id)
def disconnect(path,node,pin='then'):
    S.disconnect_pin(path,G,node,pin)

# Player owns the selection for the whole encounter.
assert S.add_member_variable(P,'DifficultyLevel','int','1')
player_apply=build(P,[
 {'ref':'Apply','type':'custom_event','params':{'name':'ApplySelectedDifficulty'}},
 {'ref':'EnemyClass','type':'variable_get','params':{'variable':'EncounterEnemyClass'}},
 {'ref':'Enemy','type':'function_call','params':{'class':'GameplayStatics','function':'GetActorOfClass'}},
 {'ref':'EnemyCast','type':'cast','params':{'target_class':'BP_Enemy_C'}},
 {'ref':'EnemyApply','type':'function_call','params':{'class':'BP_Enemy_C','function':'ApplySelectedDifficulty'}},
 {'ref':'BossClass','type':'variable_get','params':{'variable':'BossClass'}},
 {'ref':'Boss','type':'function_call','params':{'class':'GameplayStatics','function':'GetActorOfClass'}},
 {'ref':'BossCast','type':'cast','params':{'target_class':'BP_Boss_C'}},
 {'ref':'BossApply','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplySelectedDifficulty'}},
],[
 {'from_':'Apply.then','to':'Enemy.execute'},{'from_':'EnemyClass.EncounterEnemyClass','to':'Enemy.ActorClass'},
 {'from_':'Enemy.then','to':'EnemyCast.execute'},{'from_':'Enemy.ReturnValue','to':'EnemyCast.Object'},
 {'from_':'EnemyCast.then','to':'EnemyApply.execute'},{'from_':'EnemyCast.AsBP Enemy','to':'EnemyApply.self'},
 {'from_':'EnemyCast.CastFailed','to':'Boss.execute'},{'from_':'EnemyApply.then','to':'Boss.execute'},
 {'from_':'BossClass.BossClass','to':'Boss.ActorClass'},{'from_':'Boss.then','to':'BossCast.execute'},
 {'from_':'Boss.ReturnValue','to':'BossCast.Object'},{'from_':'BossCast.then','to':'BossApply.execute'},
 {'from_':'BossCast.AsBP Boss','to':'BossApply.self'},
])

# Common per-enemy difficulty event. Reads player DifficultyLevel and writes real stats/damage.
def add_difficulty(path, stat_class, combat_class, easy_hp, normal_hp, hard_hp, easy_dmg, normal_dmg, hard_dmg):
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
      {'ref':'Stats','type':'member_get','params':{'class':path.rsplit('/',1)[1]+'_C','member':'StatComponent'}},
      {'ref':'Combat','type':'member_get','params':{'class':path.rsplit('/',1)[1]+'_C','member':'CombatComponent'}},
      {'ref':'Max','type':'member_set','params':{'class':stat_class,'member':'MaxHealth'}},
      {'ref':'Current','type':'member_set','params':{'class':stat_class,'member':'CurrentHealth'}},
      {'ref':'Damage','type':'member_set','params':{'class':combat_class,'member':'AttackDamage'}},
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
    defaults=[]
    for ref,pin,val in [('Player','PlayerIndex',0),('Easy','B',0),('Hard','B',2),
      ('HpNH','A',hard_hp),('HpNH','B',normal_hp),('HpFinal','A',easy_hp),
      ('DmgNH','A',hard_dmg),('DmgNH','B',normal_dmg),('DmgFinal','A',easy_dmg)]:
        defaults.append({'node_ref':ref,'pin_name':pin,'value':str(val)})
    ids=build(path,nodes,edges,defaults);save(path);return ids

enemy_ids=add_difficulty(E,'BPC_Stat_C','BPC_Combat_C',60,75,105,10,15,21)
boss_ids=add_difficulty(B,'BPC_Stat_C','BPC_Combat_C',320,400,520,15,20,28)

# Boss applies the selected value when spawned after the guardian.
boss_begin_last='DE0D2FB748485CF58B3EBD85D2FE464F'
fixed_damage='3B49DDA14034164397779B85D8B01C2E'
# Resolve the current AttackDamage setter by its connection from CurrentHealth.
detail=S.get_node_details(B,G,boss_begin_last)
linked=[str(x).split(':')[0] for p in detail.output_pins if p.pin_name=='then' for x in p.connections]
assert len(linked)==1
fixed_damage=linked[0]
call=build(B,[{'ref':'ApplyCall','type':'function_call','params':{'class':'BP_Boss_C','function':'ApplySelectedDifficulty'}}],[
 {'from_':fixed_damage+'.then','to':'ApplyCall.execute'}])
save(B)

# Add the title screen after the existing HUD setup, then pause with a visible cursor.
assert S.add_member_variable(P,'MainMenuClass','TSubclassOf<UserWidget>','/Game/UI/WBP_MainMenu.WBP_MainMenu_C')
menu=build(P,[
 {'ref':'MenuClass','type':'variable_get','params':{'variable':'MainMenuClass'}},
 {'ref':'Create','type':'function_call','params':{'class':'WidgetBlueprintLibrary','function':'Create'}},
 {'ref':'Add','type':'function_call','params':{'class':'UserWidget','function':'AddToViewport'}},
 {'ref':'Cursor','type':'member_set','params':{'class':'PlayerController','member':'bShowMouseCursor'}},
 {'ref':'Pause','type':'function_call','params':{'class':'GameplayStatics','function':'SetGamePaused'}},
],[
 {'from_':'7F61B89C4B63D61E54D30CAAB7168C8F.then','to':'Create.execute'},
 {'from_':'MenuClass.MainMenuClass','to':'Create.WidgetType'},
 {'from_':'6735982747F8038958B94AA5B1B163E9.AsPlayer Controller','to':'Create.OwningPlayer'},
 {'from_':'Create.then','to':'Add.execute'},{'from_':'Create.ReturnValue','to':'Add.self'},
 {'from_':'Add.then','to':'Cursor.execute'},{'from_':'6735982747F8038958B94AA5B1B163E9.AsPlayer Controller','to':'Cursor.self'},
 {'from_':'Cursor.then','to':'Pause.execute'},
],[
 {'node_ref':'Add','pin_name':'ZOrder','value':'100'},{'node_ref':'Cursor','pin_name':'bShowMouseCursor','value':'true'},
 {'node_ref':'Pause','pin_name':'bPaused','value':'true'},
])
save(P)

# Each button selects a level, applies it, closes the menu and resumes play.
widget_maps={}
for event_name, level in [('SelectEasy',0),('SelectNormal',1),('SelectHard',2)]:
    ids=build(W,[
      {'ref':'Event','type':'custom_event','params':{'name':event_name}},
      {'ref':'Player','type':'function_call','params':{'class':'GameplayStatics','function':'GetPlayerCharacter'}},
      {'ref':'Cast','type':'cast','params':{'target_class':'BP_DarkKnight_Alert_C'}},
      {'ref':'SetDifficulty','type':'member_set','params':{'class':'BP_DarkKnight_Alert_C','member':'DifficultyLevel'}},
      {'ref':'Apply','type':'function_call','params':{'class':'BP_DarkKnight_Alert_C','function':'ApplySelectedDifficulty'}},
      {'ref':'Controller','type':'function_call','params':{'class':'UserWidget','function':'GetOwningPlayer'}},
      {'ref':'Cursor','type':'member_set','params':{'class':'PlayerController','member':'bShowMouseCursor'}},
      {'ref':'Unpause','type':'function_call','params':{'class':'GameplayStatics','function':'SetGamePaused'}},
      {'ref':'Self','type':'spawner_key','params':{'key':'NODE K2Node_Self'}},
      {'ref':'Remove','type':'function_call','params':{'class':'Widget','function':'RemoveFromParent'}},
    ],[
      {'from_':'Event.then','to':'Player.execute'},{'from_':'Player.then','to':'Cast.execute'},{'from_':'Player.ReturnValue','to':'Cast.Object'},
      {'from_':'Cast.then','to':'SetDifficulty.execute'},{'from_':'Cast.AsBP Dark Knight Alert','to':'SetDifficulty.self'},
      {'from_':'SetDifficulty.then','to':'Apply.execute'},{'from_':'Cast.AsBP Dark Knight Alert','to':'Apply.self'},
      {'from_':'Apply.then','to':'Controller.execute'},{'from_':'Controller.then','to':'Cursor.execute'},
      {'from_':'Controller.ReturnValue','to':'Cursor.self'},{'from_':'Cursor.then','to':'Unpause.execute'},
      {'from_':'Unpause.then','to':'Remove.execute'},{'from_':'Self.self','to':'Remove.self'},
    ],[
      {'node_ref':'Player','pin_name':'PlayerIndex','value':'0'},
      {'node_ref':'SetDifficulty','pin_name':'DifficultyLevel','value':str(level)},
      {'node_ref':'Cursor','pin_name':'bShowMouseCursor','value':'false'},
      {'node_ref':'Unpause','pin_name':'bPaused','value':'false'},
    ])
    widget_maps[event_name]=ids
save(W)
for button,event in [('EasyButton','SelectEasy'),('NormalButton','SelectNormal'),('HardButton','SelectHard')]:
    assert unreal.WidgetService.bind_event(W,button,'OnClicked',event),(button,event)
save(W)

MAP.write_text(json.dumps({'player_apply':player_apply,'enemy':enemy_ids,'boss':boss_ids,'boss_begin':call,'menu':menu,'widget':widget_maps},indent=2),encoding='utf-8')
print('MAIN_MENU_DIFFICULTY_APPLIED')
