"""One-time encounter repair. Run stages separately; do not rerun completed stages."""
import unreal
from pathlib import Path
import json
base=Path(unreal.Paths.project_dir())
exec((base/'Scripts/refine_combat_flow.py').read_text().split("if stage=='foundation':")[0])
MAP=base/'Saved/EncounterBackup_20260929/nodes.json'
saved=json.loads(MAP.read_text()) if MAP.exists() else {}
E='/Game/AI/BP_Enemy'; H='/Game/UI/WBP_HUD'

if stage=='approach':
    g=Graph(E,'approach')
    g.branch('Near');g.fn('Wake','BP_Enemy_C','Awaken')
    cut(E,'96F8','then')
    g.e(g.o('96F8')+'.then','Near.execute')
    g.e(g.o('5F03')+'.ReturnValue','Near.Condition')
    g.e('Near.then','Wake.execute')
    g.run()
    # Prompt is no longer an interaction; always hidden through the existing setter.
    cut(E,'D6A0','bNewVisibility')
    assert svc.set_variable_default_value(E,'InteractRange','600.0')
    # Remove unverified lingering spawn effect; preserve actual boss spawn and death delay.
    cut(E,'59E2');assert svc.connect_nodes(E,'EventGraph',old(E,'59E2'),'then',old(E,'A1F7'),'execute')
    save(E)

if stage=='lock':
    addvar(P,'EncounterEnemyClass','TSubclassOf<Actor>')
    assert svc.set_variable_default_value(P,'EncounterEnemyClass',E+'.BP_Enemy_C')
    g=Graph(P,'encounter_lock')
    g.get('EnemyClass','EncounterEnemyClass');g.fn('Enemy','GameplayStatics','GetActorOfClass')
    g.e('EnemyClass.EncounterEnemyClass','Enemy.ActorClass')
    g.fn('BossValid','KismetSystemLibrary','IsValid');g.e(g.o('EAEA')+'.ReturnValue','BossValid.Object')
    g.fn('Choose','KismetMathLibrary','SelectObject')
    g.e(g.o('EAEA')+'.ReturnValue','Choose.A');g.e('Enemy.ReturnValue','Choose.B');g.e('BossValid.ReturnValue','Choose.bSelectA')
    cut(P,'EAEA','then');g.e(g.o('EAEA')+'.then','Enemy.execute');g.e('Enemy.then',g.o('02BD')+'.execute')
    for node,pin in [('AF99','Object'),('6C67','OtherActor'),('73A9','LockedTarget')]:
        cut(P,node,pin);g.e('Choose.ReturnValue',g.o(node)+'.'+pin)
    g.run();save(P)

if stage=='phase':
    addvar(B,'PhaseAnnouncement','String')
    g=Graph(B,'phase_signal')
    g.event('Clear','ClearPhaseAnnouncement');g.set('ClearText','PhaseAnnouncement','');g.e('Clear.then','ClearText.execute')
    g.get('Phase','Phase');g.node('Third','comparison',operation='Equal',operand_type='Int');g.e('Phase.Phase','Third.A');g.d('Third','B',3)
    g.fn('Message','KismetMathLibrary','SelectString');g.d('Message','A','PHASE 3 : FURIE - ASSAUTS ENCHAINES');g.d('Message','B','PHASE 2 : KHAIMERA ACCELERE')
    g.e('Third.ReturnValue','Message.bPickA');g.set('Announcement','PhaseAnnouncement');g.e('Message.ReturnValue','Announcement.PhaseAnnouncement')
    cut(B,'16EE');g.e(g.o('16EE')+'.then','Announcement.execute')
    g.fn('Timer','KismetSystemLibrary','K2_SetTimer');g.e('Announcement.then','Timer.execute');g.e(g.o('E2A3')+'.self','Timer.Object')
    g.d('Timer','FunctionName','ClearPhaseAnnouncement');g.d('Timer','Time',3.5)
    g.run();save(B)

if stage=='hud':
    addvar(H,'EncounterEnemyClass','TSubclassOf<Actor>')
    assert svc.set_variable_default_value(H,'EncounterEnemyClass',E+'.BP_Enemy_C')
    g=Graph(H,'encounter_hud')
    # Refresh the boss reference when absent; the boss is now spawned later.
    g.e(g.o('AD73')+'.else',g.o('8226')+'.execute')
    g.member('Announcement','BP_Boss_C','PhaseAnnouncement');g.e(g.o('8266')+'.BossRef','Announcement.self')
    g.e('Announcement.PhaseAnnouncement',g.o('132F')+'.B')
    # No boss yet: reuse the encounter bar for the guardian.
    g.get('EnemyClass','EncounterEnemyClass');g.fn('Enemy','GameplayStatics','GetActorOfClass');g.e('EnemyClass.EncounterEnemyClass','Enemy.ActorClass')
    g.e(g.o('B360')+'.CastFailed','Enemy.execute');g.cast('CastEnemy','BP_Enemy_C');g.e('Enemy.then','CastEnemy.execute');g.e('Enemy.ReturnValue','CastEnemy.Object')
    g.member('Stats','BP_Enemy_C','StatComponent');g.e('CastEnemy.AsBP Enemy','Stats.self')
    for ref,var in [('HP','CurrentHealth'),('Max','MaxHealth'),('Dead','bIsDead')]:
        g.member(ref,'BPC_Stat_C',var);g.e('Stats.StatComponent',ref+'.self')
    g.fn('Ratio','KismetMathLibrary','Divide_DoubleDouble');g.e('HP.CurrentHealth','Ratio.A');g.e('Max.MaxHealth','Ratio.B')
    g.fn('Bar','ProgressBar','SetPercent');g.e('CastEnemy.then','Bar.execute');g.e(g.o('9D93')+'.BossBar','Bar.self');g.e('Ratio.ReturnValue','Bar.InPercent')
    g.fn('Label','TextBlock','SetText');g.e('Bar.then','Label.execute');g.e(g.o('E832')+'.BossLabel','Label.self');g.d('Label','InText','GARDIEN')
    g.member('Dormant','BP_Enemy_C','bDormant');g.e('CastEnemy.AsBP Enemy','Dormant.self')
    g.fn('Hint','KismetMathLibrary','SelectString');g.e('Dormant.bDormant','Hint.bPickA');g.d('Hint','A','APPROCHEZ DU GARDIEN');g.d('Hint','B','')
    g.fn('AfterDeath','KismetMathLibrary','SelectString');g.e('Dead.bIsDead','AfterDeath.bPickA');g.d('AfterDeath','A','KHAIMERA ARRIVE...');g.e('Hint.ReturnValue','AfterDeath.B')
    g.fn('PlayerDeath','KismetMathLibrary','SelectString');g.e(g.o('2E8C')+'.bIsDead','PlayerDeath.bPickA');g.d('PlayerDeath','A','VOUS ETES MORT');g.e('AfterDeath.ReturnValue','PlayerDeath.B')
    g.fn('Text','KismetTextLibrary','Conv_StringToText');g.e('PlayerDeath.ReturnValue','Text.InString')
    g.fn('Result','TextBlock','SetText');g.e('Label.then','Result.execute');g.e(g.o('B528')+'.EncounterResult','Result.self');g.e('Text.ReturnValue','Result.InText')
    g.run();save(H)

if stage=='level':
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing=actors.get_all_level_actors()
    assert not any(a.get_class().get_name()=='BP_Enemy_C' for a in existing)
    enemy=actors.spawn_actor_from_class(unreal.load_class(None,E+'.BP_Enemy_C'),unreal.Vector(1200,0,100),unreal.Rotator(yaw=180))
    assert enemy
    enemy.set_actor_label('Gardien_Approche')
    for a in existing:
        if a.get_class().get_name() in ['BP_Boss_C','BP_ThirdPersonCharacter_C']:assert actors.destroy_actor(a)
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    print('LEVEL: guardian waits; boss spawned by guardian death; residual mannequin removed')
