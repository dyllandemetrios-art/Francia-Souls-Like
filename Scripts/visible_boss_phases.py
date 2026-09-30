"""One-time phase implementation. Backups and stage maps in Saved/VisiblePhasesBackup_20260929."""
import unreal,json
from pathlib import Path
GRAPH='EventGraph'
base=Path(unreal.Paths.project_dir())
exec((base/'Scripts/refine_combat_flow.py').read_text().split("if stage=='foundation':")[0].replace("'EventGraph'","GRAPH"))
MAP=base/'Saved/VisiblePhasesBackup_20260929/nodes.json'
saved=json.loads(MAP.read_text()) if MAP.exists() else {}
BaseGraph=Graph
class Graph(BaseGraph):
    def run(self):
        external=getattr(self,'external',{})
        for edge in self.edges:
            for key in ['from_','to']:
                ref,pin=edge[key].rsplit('.',1)
                if ref in external:edge[key]=external[ref]+'.'+pin
        for d in self.defaults:
            if d['node_ref'] in external:d['node_ref']=external[d['node_ref']]
        result=super().run()
        result.update(external)
        MAP.write_text(json.dumps(saved,indent=2),encoding='utf-8')
        return result
F='/Game/Enemies/Khaimera/BP_Fireball'
N='/Game/Enemies/Khaimera/AN_ReleaseFireball'
M='/Game/Enemies/Khaimera/Montages/'
def create(path,parent):
    assert not unreal.EditorAssetLibrary.does_asset_exist(path),path
    factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',parent)
    folder,name=path.rsplit('/',1)
    assert unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,None,factory)
def prop(path,component,name,value):assert svc.set_component_property(path,component,name,str(value)),(component,name)
def spawn(g,ref,cls,transform,previous):
    # Use the editor's initialized spawner. Generic NODE construction asserts in this VibeUE build.
    node=svc.create_node_by_key(g.path,GRAPH,'SPAWN K2Node_SpawnActorFromClass|Spawn Actor from Class',0,0)
    assert node
    assert svc.set_node_pin_value(g.path,GRAPH,node,'Class',cls)
    if not hasattr(g,'external'):g.external={}
    g.external[ref]=node
    g.d(ref,'CollisionHandlingOverride','AlwaysSpawn')
    g.e(transform,ref+'.SpawnTransform');g.e(previous,ref+'.execute')
    return ref+'.then'
def timer(g,ref,event,time,previous):
    g.fn(ref,'KismetSystemLibrary','K2_SetTimer');g.e(previous,ref+'.execute');g.e(g.o('E2A3')+'.self',ref+'.Object');g.d(ref,'FunctionName',event);g.d(ref,'Time',time)
    return ref+'.then'

if stage=='assets':
    for side in ['L','R']:
        path='/Game/Enemies/Khaimera/Props/BP_DroppedAxe_'+side;create(path,unreal.Actor)
        assert svc.add_component(path,'StaticMeshComponent','Axe');assert svc.set_root_component(path,'Axe')
        prop(path,'Axe','StaticMesh','/Game/Enemies/Khaimera/Props/SM_Khaimera_Axe_'+side)
        # Collision and physics configured at runtime to avoid fragile BodyInstance import strings.
        g=Graph(path,'axe_'+side);g.node('Begin','event',event='ReceiveBeginPlay');g.get('Mesh','Axe')
        g.fn('Profile','PrimitiveComponent','SetCollisionProfileName');g.e('Begin.then','Profile.execute');g.e('Mesh.Axe','Profile.self');g.d('Profile','InCollisionProfileName','PhysicsActor')
        g.fn('IgnorePawn','PrimitiveComponent','SetCollisionResponseToChannel');g.e('Profile.then','IgnorePawn.execute');g.e('Mesh.Axe','IgnorePawn.self');g.d('IgnorePawn','Channel','ECC_Pawn');g.d('IgnorePawn','NewResponse','ECR_Ignore')
        g.fn('Physics','PrimitiveComponent','SetSimulatePhysics');g.e('IgnorePawn.then','Physics.execute');g.e('Mesh.Axe','Physics.self');g.d('Physics','bSimulate',True)
        g.fn('Life','Actor','SetLifeSpan');g.e('Physics.then','Life.execute');g.d('Life','InLifespan',120)
        g.run();save(path)
    for source,name in [('Cast','AM_Khaimera_FireCast'),('Emote_Taunt_Howl_T1','AM_Khaimera_PhaseChange')]:
        assert unreal.AnimMontageService.create_montage_from_animation('/Game/ParagonKhaimera/Characters/Heroes/Khaimera/Animations/'+source,M.rstrip('/'),name)
    create(F,unreal.Actor)
    assert svc.add_component(F,'SphereComponent','Collision');assert svc.set_root_component(F,'Collision')
    prop(F,'Collision','SphereRadius','30.0');prop(F,'Collision','bGenerateOverlapEvents','true')
    assert svc.add_component(F,'NiagaraComponent','Flames','Collision')
    prop(F,'Flames','Asset','/Game/Mixed_Magic_VFX_Pack/VFX/Sperate_VFX/NS_Magma_Shot_Projectile')
    prop(F,'Flames','RelativeScale3D','(X=0.35,Y=0.35,Z=0.35)')
    assert svc.add_component(F,'ProjectileMovementComponent','Movement')
    for name,value in [('InitialSpeed','950'),('MaxSpeed','950'),('ProjectileGravityScale','0'),('bRotationFollowsVelocity','true')]:prop(F,'Movement',name,value)
    g=Graph(F,'projectile')
    g.node('Begin','event',event='ReceiveBeginPlay');g.get('Sphere','Collision');g.fn('Profile','PrimitiveComponent','SetCollisionProfileName')
    g.e('Begin.then','Profile.execute');g.e('Sphere.Collision','Profile.self');g.d('Profile','InCollisionProfileName','OverlapAllDynamic')
    g.fn('Life','Actor','SetLifeSpan');g.e('Profile.then','Life.execute');g.d('Life','InLifespan',5)
    g.node('Overlap','event',event='ReceiveActorBeginOverlap');g.fn('Owner','Actor','GetOwner');g.fn('NotOwner','KismetMathLibrary','NotEqual_ObjectObject')
    g.e('Overlap.OtherActor','NotOwner.A');g.e('Owner.ReturnValue','NotOwner.B');g.branch('IgnoreOwner');g.e('Overlap.then','IgnoreOwner.execute');g.e('NotOwner.ReturnValue','IgnoreOwner.Condition')
    g.fn('Player','GameplayStatics','GetPlayerCharacter');g.fn('IsPlayer','KismetMathLibrary','EqualEqual_ObjectObject');g.e('Overlap.OtherActor','IsPlayer.A');g.e('Player.ReturnValue','IsPlayer.B')
    g.branch('HitPlayer');g.e('IgnoreOwner.then','HitPlayer.execute');g.e('IsPlayer.ReturnValue','HitPlayer.Condition')
    g.fn('Damage','GameplayStatics','ApplyDamage');g.e('HitPlayer.then','Damage.execute');g.e('Overlap.OtherActor','Damage.DamagedActor');g.e('Owner.ReturnValue','Damage.DamageCauser');g.d('Damage','BaseDamage',20)
    g.fn('Destroy','Actor','K2_DestroyActor');g.e('Damage.then','Destroy.execute');g.e('HitPlayer.else','Destroy.execute')
    g.run();save(F)

if stage=='foundation':
    for name,kind,default in [('bPhaseTransition','bool','false'),('bIsCasting','bool','false'),('FireCastMontage','AnimMontage',M+'AM_Khaimera_FireCast'),('PhaseChangeMontage','AnimMontage',M+'AM_Khaimera_PhaseChange'),('DroppedLeft','Actor',''),('DroppedRight','Actor','')]:addvar(B,name,kind,default)
    g=Graph(B,'phase_events')
    for name in ['BeginPhaseTransition','ReleaseAxes','FinishPhaseTransition','BeginFireCast','FinishFireCast','LaunchFireball']:g.event(name,name)
    g.run();save(B)

if stage=='transition':
    g=Graph(B,'visible_transition');events=saved['phase_events']
    g.get('Mesh','Mesh');g.get('Stat','StatComponent');g.get('Phase','Phase');g.get('Howl','PhaseChangeMontage')
    g.set('Transition','bPhaseTransition',True);g.set('Casting','bIsCasting',False)
    g.e(events['BeginPhaseTransition']+'.then','Transition.execute');g.e('Transition.then','Casting.execute')
    g.mset('Invulnerable','Actor','bCanBeDamaged',False);g.e('Casting.then','Invulnerable.execute')
    g.mset('LockMovement','BPC_Stat_C','bAttackMovementLocked',True);g.e('Stat.StatComponent','LockMovement.self');g.e('Invulnerable.then','LockMovement.execute')
    g.fn('Refresh','BPC_Stat_C','RefreshMovement');g.e('Stat.StatComponent','Refresh.self');g.e('LockMovement.then','Refresh.execute')
    g.fn('Controller','Pawn','GetController');g.fn('Stop','Controller','StopMovement');g.e('Controller.ReturnValue','Stop.self');g.e('Refresh.then','Stop.execute')
    g.fn('HowlPlay','Character','PlayAnimMontage');g.e('Stop.then','HowlPlay.execute');g.e('Howl.PhaseChangeMontage','HowlPlay.AnimMontage');g.d('HowlPlay','InPlayRate',1.7)
    t=timer(g,'DropTimer','ReleaseAxes',.55,'HowlPlay.then');timer(g,'EndTimer','FinishPhaseTransition',2.5,t)
    g.node('IsMagic','comparison',operation='Equal',operand_type='Int');g.e('Phase.Phase','IsMagic.A');g.d('IsMagic','B',2);g.branch('Magic')
    g.e(events['ReleaseAxes']+'.then','Magic.execute');g.e('IsMagic.ReturnValue','Magic.Condition')
    prev='Magic.then'
    for side,field in [('L','DroppedLeft'),('R','DroppedRight')]:
        g.fn('Socket'+side,'SceneComponent','GetSocketTransform');g.e('Mesh.Mesh','Socket'+side+'.self');g.d('Socket'+side,'InSocketName','weapon_'+side.lower());g.d('Socket'+side,'TransformSpace','RTS_World')
        prev=spawn(g,'Drop'+side,'/Game/Enemies/Khaimera/Props/BP_DroppedAxe_'+side+'.BP_DroppedAxe_'+side+'_C','Socket'+side+'.ReturnValue',prev)
        g.set('Save'+side,field);g.e(prev,'Save'+side+'.execute');g.e('Drop'+side+'.ReturnValue','Save'+side+'.'+field)
        g.fn('Hide'+side,'SkinnedMeshComponent','HideBoneByName');g.e('Save'+side+'.then','Hide'+side+'.execute');g.e('Mesh.Mesh','Hide'+side+'.self');g.d('Hide'+side,'BoneName','weapon_'+side.lower());g.d('Hide'+side,'PhysBodyOption','PBO_None');prev='Hide'+side+'.then'
    prev='Magic.else'
    for side,field in [('L','DroppedLeft'),('R','DroppedRight')]:
        g.fn('Show'+side,'SkinnedMeshComponent','UnHideBoneByName');g.e(prev,'Show'+side+'.execute');g.e('Mesh.Mesh','Show'+side+'.self');g.d('Show'+side,'BoneName','weapon_'+side.lower())
        g.get('Prop'+side,field);g.fn('Valid'+side,'KismetSystemLibrary','IsValid');g.e('Prop'+side+'.'+field,'Valid'+side+'.Object');g.branch('Check'+side);g.e('Show'+side+'.then','Check'+side+'.execute');g.e('Valid'+side+'.ReturnValue','Check'+side+'.Condition')
        g.fn('Remove'+side,'Actor','K2_DestroyActor');g.e('Prop'+side+'.'+field,'Remove'+side+'.self');g.e('Check'+side+'.then','Remove'+side+'.execute')
        prev='Remove'+side+'.then'
    g.set('Ready','bPhaseTransition',False);g.e(events['FinishPhaseTransition']+'.then','Ready.execute')
    g.mset('Vulnerable','Actor','bCanBeDamaged',True);g.e('Ready.then','Vulnerable.execute')
    g.mset('Unlock','BPC_Stat_C','bAttackMovementLocked',False);g.e('Stat.StatComponent','Unlock.self');g.e('Vulnerable.then','Unlock.execute')
    g.fn('RefreshEnd','BPC_Stat_C','RefreshMovement');g.e('Stat.StatComponent','RefreshEnd.self');g.e('Unlock.then','RefreshEnd.execute')
    # Existing phase entry already runs once after changing Phase; add visible transition here.
    oldmap=json.loads((base/'Saved/EncounterBackup_20260929/nodes.json').read_text())['phase_signal']
    svc.disconnect_pin(B,GRAPH,oldmap['Announcement'],'then');g.fn('Enter','BP_Boss_C','BeginPhaseTransition')
    g.e(oldmap['Announcement']+'.then','Enter.execute');g.e('Enter.then',oldmap['Timer']+'.execute')
    g.run();save(B)

if stage=='cast':
    g=Graph(B,'fire_cast');ev=saved['phase_events']
    g.get('Mesh','Mesh');g.get('Stat','StatComponent');g.get('Montage','FireCastMontage')
    g.set('Casting','bIsCasting',True);g.e(ev['BeginFireCast']+'.then','Casting.execute')
    g.mset('Lock','BPC_Stat_C','bAttackMovementLocked',True);g.e('Casting.then','Lock.execute');g.e('Stat.StatComponent','Lock.self')
    g.fn('Refresh','BPC_Stat_C','RefreshMovement');g.e('Lock.then','Refresh.execute');g.e('Stat.StatComponent','Refresh.self')
    g.fn('Play','Character','PlayAnimMontage');g.e('Refresh.then','Play.execute');g.e('Montage.FireCastMontage','Play.AnimMontage')
    timer(g,'EndCastTimer','FinishFireCast',1.2,'Play.then')
    g.set('EndCasting','bIsCasting',False);g.e(ev['FinishFireCast']+'.then','EndCasting.execute')
    g.get('Transition','bPhaseTransition');g.branch('StillTransition');g.e('EndCasting.then','StillTransition.execute');g.e('Transition.bPhaseTransition','StillTransition.Condition')
    g.mset('Unlock','BPC_Stat_C','bAttackMovementLocked',False);g.e('StillTransition.else','Unlock.execute');g.e('Stat.StatComponent','Unlock.self')
    g.fn('RefreshEnd','BPC_Stat_C','RefreshMovement');g.e('Unlock.then','RefreshEnd.execute');g.e('Stat.StatComponent','RefreshEnd.self')
    # Notify must belong to a still-playing cast: no projectile from an interrupted montage.
    g.fn('Current','Character','GetCurrentMontage');g.fn('Same','KismetMathLibrary','EqualEqual_ObjectObject');g.e('Current.ReturnValue','Same.A');g.e('Montage.FireCastMontage','Same.B')
    g.branch('ValidCast');g.e(ev['LaunchFireball']+'.then','ValidCast.execute');g.e('Same.ReturnValue','ValidCast.Condition')
    g.fn('Hand','SceneComponent','GetSocketLocation');g.e('Mesh.Mesh','Hand.self');g.d('Hand','InSocketName','hand_r')
    g.fn('Player','GameplayStatics','GetPlayerCharacter');g.fn('PlayerLocation','Actor','K2_GetActorLocation');g.e('Player.ReturnValue','PlayerLocation.self')
    g.fn('Aim','KismetMathLibrary','FindLookAtRotation');g.e('Hand.ReturnValue','Aim.Start');g.e('PlayerLocation.ReturnValue','Aim.Target')
    g.fn('Transform','KismetMathLibrary','MakeTransform');g.e('Hand.ReturnValue','Transform.Location');g.e('Aim.ReturnValue','Transform.Rotation')
    spawn(g,'Projectile',F+'.BP_Fireball_C','Transform.ReturnValue','ValidCast.then');g.e(g.o('E2A3')+'.self','Projectile.Owner')
    g.run();save(B)

if stage=='attack':
    GRAPH='Attack01'
    g=Graph(B,'attack_modes')
    g.get('Transition','bPhaseTransition');g.branch('Wait');cut(B,'86A6');g.e(g.o('86A6')+'.then','Wait.execute');g.e('Transition.bPhaseTransition','Wait.Condition')
    g.set('WaitDuration','LastAttackDuration',.25);g.e('Wait.then','WaitDuration.execute');g.e('WaitDuration.then',g.o('7418')+'.execute')
    g.get('Phase','Phase');g.node('Second','comparison',operation='Equal',operand_type='Int');g.e('Phase.Phase','Second.A');g.d('Second','B',2)
    g.branch('Magic');g.e('Wait.else','Magic.execute');g.e('Second.ReturnValue','Magic.Condition');g.e('Magic.else',g.o('4A1F')+'.execute')
    g.fn('Cast','BP_Boss_C','BeginFireCast');g.e('Magic.then','Cast.execute');g.set('CastDuration','LastAttackDuration',1.6);g.e('Cast.then','CastDuration.execute');g.e('CastDuration.then',g.o('7418')+'.execute')
    g.run();save(B)

if stage=='notify':
    create(N,unreal.AnimNotify);assert svc.override_function(N,'Received_Notify');GRAPH='Received_Notify'
    ns=svc.get_nodes_in_graph(N,GRAPH,0,'',False);entry=next(n.node_id for n in ns if n.node_type=='K2Node_FunctionEntry');result=next(n.node_id for n in ns if n.node_type=='K2Node_FunctionResult')
    g=Graph(N,'fire_notify');g.fn('Owner','ActorComponent','GetOwner');g.e(entry+'.MeshComp','Owner.self');g.cast('Boss','BP_Boss_C');g.e(entry+'.then','Boss.execute');g.e('Owner.ReturnValue','Boss.Object')
    g.fn('Release','BP_Boss_C','LaunchFireball');g.e('Boss.then','Release.execute');g.e('Boss.AsBP Boss','Release.self');g.e('Release.then',result+'.execute');g.e('Boss.CastFailed',result+'.execute');g.d(result,'ReturnValue',True)
    g.run();save(N)
    assert unreal.AnimMontageService.add_notify(M+'AM_Khaimera_FireCast',N+'.AN_ReleaseFireball_C',.55,'ReleaseFireball')>=0
    assert unreal.EditorAssetLibrary.save_asset(M+'AM_Khaimera_FireCast')

if stage=='range':
    T='/Game/AI/Tasks/Task_ChaseTarget'
    addvar(T,'AttackApproachDistance','float','110.0')
    g=Graph(T,'magic_range');g.set('Reset','AttackApproachDistance',110)
    cut(T,'104A');g.e(g.o('104A')+'.then','Reset.execute')
    g.cast('Boss','BP_Boss_C');g.e('Reset.then','Boss.execute');g.e(g.o('104A')+'.ControlledPawn','Boss.Object')
    g.member('Phase','BP_Boss_C','Phase');g.e('Boss.AsBP Boss','Phase.self')
    g.node('Magic','comparison',operation='Equal',operand_type='Int');g.e('Phase.Phase','Magic.A');g.d('Magic','B',2)
    g.fn('Range','KismetMathLibrary','SelectFloat');g.d('Range','A',650);g.d('Range','B',110);g.e('Magic.ReturnValue','Range.bPickA')
    g.set('Distance','AttackApproachDistance');g.e('Boss.then','Distance.execute');g.e('Range.ReturnValue','Distance.AttackApproachDistance')
    g.e('Distance.then',g.o('4D5C')+'.execute');g.e('Boss.CastFailed',g.o('4D5C')+'.execute')
    g.get('ReadDistance','AttackApproachDistance');g.e('ReadDistance.AttackApproachDistance',g.o('5BDD')+'.AcceptanceRadius')
    g.run();save(T)
    # CDC: speed remains 420; phase 3 increases attack cadence, not running speed.
    for prefix,pin,value in [('33D8','PhaseSpeed','420'),('03D9','PhaseSpeed','420'),('6275','AttackPlayRate','1.5')]:
        assert svc.set_node_pin_value(B,GRAPH,old(B,prefix),pin,value)
    saved_signal=json.loads((base/'Saved/EncounterBackup_20260929/nodes.json').read_text())['phase_signal']
    assert svc.set_node_pin_value(B,GRAPH,saved_signal['Message'],'B','PHASE 2 : MAGIE DE FEU')
    assert svc.set_node_pin_value(B,GRAPH,saved_signal['Message'],'A','PHASE 3 : RETOUR DES HACHES')
    save(B)

if stage=='aggro':
    E='/Game/AI/BP_Enemy';A='/Game/AI/BP_AI_Enemy';T='/Game/AI/Tasks/Task_Strafe'
    g=Graph(E,'boss_spawn_facing')
    g.fn('Player','GameplayStatics','GetPlayerCharacter');g.fn('Target','Actor','K2_GetActorLocation');g.e('Player.ReturnValue','Target.self')
    g.fn('Facing','KismetMathLibrary','FindLookAtRotation');g.e(g.o('5CC2')+'.ReturnValue','Facing.Start');g.e('Target.ReturnValue','Facing.Target');g.e('Facing.ReturnValue',g.o('F8D6')+'.Rotation')
    g.run();save(E)
    # Ranged phase does not use the existing close-range orbit after each shot.
    assert svc.set_node_pin_value(T,GRAPH,old(T,'22FF'),'B','2')
    save(T)
    g=Graph(A,'acquire_player')
    g.event('Acquire','AcquirePlayerTarget');g.fn('Player','GameplayStatics','GetPlayerPawn')
    g.fn('Valid','KismetSystemLibrary','IsValid');g.e('Player.ReturnValue','Valid.Object');g.branch('CanAcquire');g.e('Acquire.then','CanAcquire.execute');g.e('Valid.ReturnValue','CanAcquire.Condition');g.e('CanAcquire.then',g.o('60FF')+'.execute')
    g.fn('IsPlayer','KismetMathLibrary','EqualEqual_ObjectObject');g.e(g.o('E40D')+'.Pawn','IsPlayer.A');g.e('Player.ReturnValue','IsPlayer.B')
    g.branch('SeenPlayer');cut(A,'E40D');g.e(g.o('E40D')+'.then','SeenPlayer.execute');g.e('IsPlayer.ReturnValue','SeenPlayer.Condition');g.e('SeenPlayer.then',g.o('60FF')+'.execute')
    cut(A,'B650','ObjectValue');cut(A,'CD65','NewFocus');g.e('Player.ReturnValue',g.o('B650')+'.ObjectValue');g.e('Player.ReturnValue',g.o('CD65')+'.NewFocus')
    g.run();save(A)
    g=Graph(B,'damage_aggro')
    g.fn('Controller','Pawn','GetController');g.cast('AI','BP_AI_Enemy_C');g.e('Controller.ReturnValue','AI.Object')
    cut(B,'9643');g.e(g.o('9643')+'.then','AI.execute');g.fn('Acquire','BP_AI_Enemy_C','AcquirePlayerTarget');g.e('AI.AsBP AI Enemy','Acquire.self');g.e('AI.then','Acquire.execute')
    g.e('Acquire.then',g.o('2863')+'.execute');g.e('AI.CastFailed',g.o('2863')+'.execute')
    g.run();save(B)
