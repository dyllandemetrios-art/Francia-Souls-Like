"""One-time Blueprint migration, invoked in stages from Unreal Python.
Do not rerun completed stages. Backups and node maps live in Saved/CombatFlowBackup_20260926.
"""
import unreal
import json
from pathlib import Path

ROOT='/Game/Characters/Dark_Knight/Dark_Knight_Male/Blueprints/'
C=ROOT+'BPC_Combat'; S=ROOT+'BPC_Stat'; P=ROOT+'BP_DarkKnight_Alert'; B='/Game/AI/BP_Boss'
svc=unreal.BlueprintService
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
MAP=Path(unreal.Paths.project_saved_dir())/'CombatFlowBackup_20260926'/'nodes.json'
saved=json.loads(MAP.read_text()) if MAP.exists() else {}

def old(path,prefix):
    matches=[n.node_id for n in svc.get_nodes_in_graph(path,'EventGraph',0,'',False) if n.node_id.startswith(prefix)]
    assert len(matches)==1,(path,prefix,matches)
    return matches[0]
def cut(path,prefix,pin='then'):
    return svc.disconnect_pin(path,'EventGraph',old(path,prefix),pin)
def save(path):
    assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(path)),path
    assert unreal.EditorAssetLibrary.save_asset(path),path
def addvar(path,name,kind,default=''):
    assert not svc.variable_exists(path,name),name
    assert svc.add_member_variable(path,name,kind,default),name

class Graph:
    def __init__(self,path,stage):
        self.path=path;self.stage=stage;self.nodes=[];self.edges=[];self.defaults=[]
    def node(self,ref,kind,**params):
        self.nodes.append({'ref':ref,'type':kind,'params':params});return ref
    def fn(self,ref,cls,method):return self.node(ref,'function_call',**{'class':cls,'function':method})
    def get(self,ref,var):return self.node(ref,'variable_get',variable=var)
    def set(self,ref,var,value=None):
        self.node(ref,'variable_set',variable=var)
        if value is not None:self.d(ref,var,value)
        return ref
    def member(self,ref,cls,var):return self.node(ref,'member_get',**{'class':cls,'member':var})
    def mset(self,ref,cls,var,value=None):
        self.node(ref,'member_set',**{'class':cls,'member':var})
        if value is not None:self.d(ref,var,value)
        return ref
    def event(self,ref,name):return self.node(ref,'custom_event',name=name)
    def branch(self,ref):return self.node(ref,'branch')
    def cast(self,ref,cls):return self.node(ref,'cast',target_class=cls)
    def e(self,a,b):self.edges.append({'from_':a,'to':b})
    def d(self,ref,pin,value):self.defaults.append({'node_ref':ref,'pin_name':pin,'value':str(value).lower() if isinstance(value,bool) else str(value)})
    def prev(self,stage,ref):return saved[stage][ref]
    def o(self,prefix):return old(self.path,prefix)
    def run(self):
        assert self.stage not in saved,self.stage
        r=svc.build_graph(self.path,'EventGraph',self.nodes,self.edges,self.defaults,False,False)
        print('BUILD',self.stage,r.success,list(r.errors),list(r.warnings))
        saved[self.stage]=dict(r.ref_to_node_id)
        MAP.write_text(json.dumps(saved,indent=2),encoding='utf-8')
        assert r.success and not r.errors and not r.warnings,self.stage
        # Verify every requested edge against actual pins, rather than trusting compile success.
        for edge in self.edges:
            a,ap=edge['from_'].rsplit('.',1);b,bp=edge['to'].rsplit('.',1)
            ai=saved[self.stage].get(a,a);bi=saved[self.stage].get(b,b)
            detail=svc.get_node_details(self.path,'EventGraph',bi)
            target=next(q for q in detail.input_pins if q.pin_name==bp)
            assert ai+':'+ap in [str(v) for v in target.connections],edge
        return saved[self.stage]

if stage=='foundation':
    for name,kind in [('bIsHitStunned','bool'),('bAttackMovementLocked','bool'),('CombatComponentClass','TSubclassOf<ActorComponent>'),('CombatRef','BPC_Combat_C')]:addvar(S,name,kind)
    for name,kind in [('bDodgeQueued','bool'),('StatRef','BPC_Stat_C')]:addvar(C,name,kind)
    g=Graph(S,'stat_events');g.event('Refresh','RefreshMovement');g.run();save(S)
    g=Graph(C,'combat_events');g.event('Cancel','CancelCombat');g.event('PendingDodge','TryPendingDodge');g.run();save(C)
    assert svc.set_variable_default_value(S,'CombatComponentClass',C+'.BPC_Combat_C')
    save(S)

if stage=='stat':
    g=Graph(S,'stat_flow')
    g.fn('Owner','ActorComponent','GetOwner');g.cast('Character','Character');g.member('Movement','Character','CharacterMovement')
    g.e('Owner.ReturnValue','Character.Object');g.e('Character.AsCharacter','Movement.self')
    g.get('HitStun','bIsHitStunned');g.get('AttackLock','bAttackMovementLocked');g.get('Dead','bIsDead')
    g.fn('Busy','KismetMathLibrary','BooleanOR');g.fn('Blocked','KismetMathLibrary','BooleanOR')
    g.e('HitStun.bIsHitStunned','Busy.A');g.e('AttackLock.bAttackMovementLocked','Busy.B');g.e('Busy.ReturnValue','Blocked.A');g.e('Dead.bIsDead','Blocked.B')
    for ref,var in [('Speed','SavedMaxWalkSpeedHit'),('Accel','SavedMaxAccelHit')]:
        g.get(ref,var);g.fn(ref+'Select','KismetMathLibrary','SelectFloat')
        g.d(ref+'Select','A',0);g.e(ref+'.'+var,ref+'Select.B');g.e('Blocked.ReturnValue',ref+'Select.bPickA')
    g.mset('ApplySpeed','CharacterMovementComponent','MaxWalkSpeed');g.mset('ApplyAccel','CharacterMovementComponent','MaxAcceleration')
    g.e(g.prev('stat_events','Refresh')+'.then','Character.execute')
    g.e('Character.then','ApplySpeed.execute');g.e('Movement.CharacterMovement','ApplySpeed.self');g.e('SpeedSelect.ReturnValue','ApplySpeed.MaxWalkSpeed')
    g.e('ApplySpeed.then','ApplyAccel.execute');g.e('Movement.CharacterMovement','ApplyAccel.self');g.e('AccelSelect.ReturnValue','ApplyAccel.MaxAcceleration')
    # Capture locomotion exactly once, before combat. Existing saved fields become the baseline.
    g.cast('InitCharacter','Character');g.e('Owner.ReturnValue','InitCharacter.Object')
    g.member('InitMovement','Character','CharacterMovement');g.e('InitCharacter.AsCharacter','InitMovement.self')
    for ref,var in [('InitSpeed','MaxWalkSpeed'),('InitAccel','MaxAcceleration')]:
        g.member(ref,'CharacterMovementComponent',var);g.e('InitMovement.CharacterMovement',ref+'.self')
    g.set('SaveSpeed','SavedMaxWalkSpeedHit');g.set('SaveAccel','SavedMaxAccelHit')
    cut(S,'E13CF087');g.e(g.o('E13CF087')+'.then','InitCharacter.execute');g.e('InitCharacter.then','SaveSpeed.execute')
    g.e('InitSpeed.MaxWalkSpeed','SaveSpeed.SavedMaxWalkSpeedHit');g.e('SaveSpeed.then','SaveAccel.execute');g.e('InitAccel.MaxAcceleration','SaveAccel.SavedMaxAccelHit')
    g.get('CombatClass','CombatComponentClass');g.fn('FindCombat','Actor','GetComponentByClass');g.cast('CombatCast','BPC_Combat_C');g.set('StoreCombat','CombatRef')
    g.e('Owner.ReturnValue','FindCombat.self');g.e('CombatClass.CombatComponentClass','FindCombat.ComponentClass');g.e('FindCombat.ReturnValue','CombatCast.Object')
    g.e('SaveAccel.then','CombatCast.execute');g.e('CombatCast.AsBPC Combat','StoreCombat.CombatRef');g.e('CombatCast.then','StoreCombat.execute')
    g.e('StoreCombat.then',g.o('83FD29BA')+'.execute');g.e('CombatCast.CastFailed',g.o('83FD29BA')+'.execute')
    g.get('Combat','CombatRef');g.fn('CombatValid','KismetSystemLibrary','IsValid');g.e('Combat.CombatRef','CombatValid.Object')
    # Cancel current combo/dodge immediately on a hit or death; clear their timers before replacing the montage.
    g.set('Stunned','bIsHitStunned',True);cut(S,'527DC131','else');g.e(g.o('527DC131')+'.else','Stunned.execute')
    for tag,source,dest in [('Hit','Stunned.then',g.o('B598DE2F')+'.execute'),('Death',g.o('756193C7')+'.then',g.o('A74946A5')+'.execute')]:
        if tag=='Death':cut(S,'756193C7')
        g.branch(tag+'HasCombat');g.fn(tag+'Cancel','BPC_Combat_C','CancelCombat')
        g.e(source,tag+'HasCombat.execute');g.e('CombatValid.ReturnValue',tag+'HasCombat.Condition')
        g.e(tag+'HasCombat.then',tag+'Cancel.execute');g.e('Combat.CombatRef',tag+'Cancel.self')
        g.e(tag+'Cancel.then',dest);g.e(tag+'HasCombat.else',dest)
    cut(S,'B598DE2F');g.fn('HitRefresh','BPC_Stat_C','RefreshMovement')
    g.e(g.o('B598DE2F')+'.then','HitRefresh.execute');g.e('HitRefresh.then',g.o('A298D1F5')+'.execute')
    # Expiring a hit-stun only releases its own movement lock.
    cut(S,'4D46E204');g.set('Unstunned','bIsHitStunned',False);g.fn('EndRefresh','BPC_Stat_C','RefreshMovement')
    g.e(g.o('4D46E204')+'.then','Unstunned.execute');g.e('Unstunned.then','EndRefresh.execute')
    g.run();save(S)

if stage=='combat':
    g=Graph(C,'combat_flow')
    g.fn('Owner','ActorComponent','GetOwner');g.get('StatClass','StatComponentClass');g.fn('FindStat','Actor','GetComponentByClass')
    g.e('Owner.ReturnValue','FindStat.self');g.e('StatClass.StatComponentClass','FindStat.ComponentClass')
    g.cast('InitStat','BPC_Stat_C');g.set('StoreStat','StatRef');g.e('FindStat.ReturnValue','InitStat.Object');g.e('InitStat.AsBPC Stat','StoreStat.StatRef')
    g.e(g.o('02BEF5D0')+'.then','InitStat.execute');g.e('InitStat.then','StoreStat.execute')
    g.cast('InitCharacter','Character');g.e('Owner.ReturnValue','InitCharacter.Object');g.e('StoreStat.then','InitCharacter.execute')
    g.member('Movement','Character','CharacterMovement');g.e('InitCharacter.AsCharacter','Movement.self')
    for ref,var in [('Friction','GroundFriction'),('Braking','BrakingDecelerationWalking')]:
        g.member(ref,'CharacterMovementComponent',var);g.e('Movement.CharacterMovement',ref+'.self')
    g.set('SaveFriction','SavedGroundFriction');g.set('SaveBraking','SavedBrakingDecel')
    g.e('InitCharacter.then','SaveFriction.execute');g.e('Friction.GroundFriction','SaveFriction.SavedGroundFriction');g.e('SaveFriction.then','SaveBraking.execute');g.e('Braking.BrakingDecelerationWalking','SaveBraking.SavedBrakingDecel')
    g.get('Stat','StatRef')
    for ref,var in [('Dead','bIsDead'),('Hit','bIsHitStunned'),('Stamina','CurrentStamina'),('AttackCost','AttackStaminaCost'),('DodgeCost','DodgeStaminaCost')]:
        g.member(ref,'BPC_Stat_C',var);g.e('Stat.StatRef',ref+'.self')
    g.fn('Unavailable','KismetMathLibrary','BooleanOR');g.e('Dead.bIsDead','Unavailable.A');g.e('Hit.bIsHitStunned','Unavailable.B')
    g.get('Dodging','bIsDodging');g.get('Attacking','bIsAttacking');g.get('DodgeQueued','bDodgeQueued');g.get('AttackQueued','bComboQueued')
    for action in ['Attack','Dodge']:
        g.node(action+'Budget','comparison',operation='GreaterEqual',operand_type='Float')
        g.e('Stamina.CurrentStamina',action+'Budget.A');g.e(action+'Cost.'+action+'StaminaCost',action+'Budget.B')
    # RequestAttack buffers a single step while attacking or dodging. No input-level stamina charge.
    cut(C,'4B768CB9');g.branch('AttackAvailable');g.branch('AttackDuringDodge');g.branch('StartBudget');g.fn('PayStart','BPC_Stat_C','ConsumeAttackStamina')
    g.e(g.o('4B768CB9')+'.then','AttackAvailable.execute');g.e('Unavailable.ReturnValue','AttackAvailable.Condition')
    g.e('AttackAvailable.else','AttackDuringDodge.execute');g.e('Dodging.bIsDodging','AttackDuringDodge.Condition')
    g.e('AttackDuringDodge.then',g.o('AF24923B')+'.execute');g.e('AttackDuringDodge.else',g.o('836158C8')+'.execute')
    cut(C,'836158C8','else');g.e(g.o('836158C8')+'.else','StartBudget.execute');g.e('AttackBudget.ReturnValue','StartBudget.Condition')
    g.e('StartBudget.then','PayStart.execute');g.e('Stat.StatRef','PayStart.self');g.e('PayStart.then',g.o('322F87DA')+'.execute')
    # One owner of movement speed: request/release a lock in BPC_Stat.
    cut(C,'081D990E');g.mset('LockMove','BPC_Stat_C','bAttackMovementLocked',True);g.fn('LockRefresh','BPC_Stat_C','RefreshMovement')
    g.e(g.o('081D990E')+'.then','LockMove.execute');g.e('Stat.StatRef','LockMove.self');g.e('LockMove.then','LockRefresh.execute');g.e('Stat.StatRef','LockRefresh.self')
    g.e('LockRefresh.then',g.o('4F19B88C')+'.execute')
    cut(C,'D33DF842');g.mset('UnlockMove','BPC_Stat_C','bAttackMovementLocked',False);g.fn('UnlockRefresh','BPC_Stat_C','RefreshMovement')
    g.e(g.o('D33DF842')+'.then','UnlockMove.execute');g.e('Stat.StatRef','UnlockMove.self');g.e('UnlockMove.then','UnlockRefresh.execute');g.e('Stat.StatRef','UnlockRefresh.self')
    g.e('UnlockRefresh.then',g.o('CFFA0352')+'.execute')
    # At each combo boundary, dodge has priority; the next hit is charged only if committed.
    cut(C,'F1EE85AC');g.branch('StepAvailable');g.branch('StepDodge');g.branch('NextBudget');g.fn('PayNext','BPC_Stat_C','ConsumeAttackStamina')
    g.e(g.o('F1EE85AC')+'.then','StepAvailable.execute');g.e('Unavailable.ReturnValue','StepAvailable.Condition');g.e('StepAvailable.then',g.prev('combat_events','Cancel')+'.execute') if False else None
    g.fn('CancelStep','BPC_Combat_C','CancelCombat');g.e('StepAvailable.then','CancelStep.execute')
    g.e('StepAvailable.else','StepDodge.execute');g.e('DodgeQueued.bDodgeQueued','StepDodge.Condition')
    g.e('StepDodge.then',g.o('A6930953')+'.execute');g.e('StepDodge.else',g.o('1F0AC557')+'.execute')
    cut(C,'1F0AC557');g.e(g.o('1F0AC557')+'.then','NextBudget.execute');g.e('AttackBudget.ReturnValue','NextBudget.Condition')
    g.e('NextBudget.then','PayNext.execute');g.e('Stat.StatRef','PayNext.self');g.e('PayNext.then',g.o('C4E82D5B')+'.execute');g.e('NextBudget.else',g.o('A6930953')+'.execute')
    # Queue dodge during attack; reject it while stunned/dead/already dodging, without charging.
    cut(C,'D90D48E0');g.branch('DodgeAvailable');g.branch('AlreadyDodging');g.branch('DodgeDuringAttack');g.set('QueueDodge','bDodgeQueued',True)
    g.e(g.o('D90D48E0')+'.then','DodgeAvailable.execute');g.e('Unavailable.ReturnValue','DodgeAvailable.Condition');g.e('DodgeAvailable.else','AlreadyDodging.execute');g.e('Dodging.bIsDodging','AlreadyDodging.Condition')
    g.e('AlreadyDodging.else','DodgeDuringAttack.execute');g.e('Attacking.bIsAttacking','DodgeDuringAttack.Condition');g.e('DodgeDuringAttack.then','QueueDodge.execute');g.e('DodgeDuringAttack.else',g.o('5ACF409C')+'.execute')
    cut(C,'356516D2');g.branch('DodgeBudgetGate');g.fn('PayDodge','BPC_Stat_C','ConsumeDodgeStamina')
    g.e(g.o('356516D2')+'.then','DodgeBudgetGate.execute');g.e('DodgeBudget.ReturnValue','DodgeBudgetGate.Condition');g.e('DodgeBudgetGate.then','PayDodge.execute');g.e('Stat.StatRef','PayDodge.self');g.e('PayDodge.then',g.o('4FB2D346')+'.execute')
    # End attack -> execute one pending dodge. End dodge -> execute one pending attack.
    g.fn('TryDodgeCall','BPC_Combat_C','TryPendingDodge');g.e(g.o('AA54798F')+'.then','TryDodgeCall.execute')
    g.branch('HasDodge');g.set('ClearPendingDodge','bDodgeQueued',False);g.set('ClearOldCombo','bComboQueued',False);g.fn('PendingDodgeCall','BPC_Combat_C','Dodge')
    g.e(g.prev('combat_events','PendingDodge')+'.then','HasDodge.execute');g.e('DodgeQueued.bDodgeQueued','HasDodge.Condition');g.e('HasDodge.then','ClearPendingDodge.execute');g.e('ClearPendingDodge.then','ClearOldCombo.execute');g.e('ClearOldCombo.then','PendingDodgeCall.execute')
    g.branch('HasAttack');g.set('ClearPendingAttack','bComboQueued',False);g.fn('PendingAttackCall','BPC_Combat_C','RequestAttack')
    g.e(g.o('23DC6C78')+'.then','HasAttack.execute');g.e('AttackQueued.bComboQueued','HasAttack.Condition');g.e('HasAttack.then','ClearPendingAttack.execute');g.e('ClearPendingAttack.then','PendingAttackCall.execute')
    # Explicit interruption, shared by hit-react and death. Do not stop the new reaction montage.
    g.node('Self','spawner_key',key='NODE K2Node_Self')
    g.fn('ClearComboTimer','KismetSystemLibrary','K2_ClearTimer');g.fn('ClearDodgeTimer','KismetSystemLibrary','K2_ClearTimer')
    g.e(g.prev('combat_events','Cancel')+'.then','ClearComboTimer.execute');g.e('Self.self','ClearComboTimer.Object');g.d('ClearComboTimer','FunctionName','OnStepTimerElapsed')
    g.e('ClearComboTimer.then','ClearDodgeTimer.execute');g.e('Self.self','ClearDodgeTimer.Object');g.d('ClearDodgeTimer','FunctionName','OnDodgeFinished')
    previous='ClearDodgeTimer.then'
    for ref,var in [('CancelAttacking','bIsAttacking'),('CancelDodging','bIsDodging'),('CancelCombo','bComboQueued'),('CancelDodgeQueue','bDodgeQueued')]:
        g.set(ref,var,False);g.e(previous,ref+'.execute');previous=ref+'.then'
    g.e(previous,g.o('D33DF842')+'.execute')
    # Prevent an outgoing/blending attack notify from damaging during a reaction or dodge.
    cut(C,'3D7C8CBE');g.branch('TraceAvailable');g.fn('TraceBusy','KismetMathLibrary','BooleanOR')
    g.e('Unavailable.ReturnValue','TraceBusy.A');g.e('Dodging.bIsDodging','TraceBusy.B');g.e('TraceBusy.ReturnValue','TraceAvailable.Condition')
    g.e(g.o('3D7C8CBE')+'.then','TraceAvailable.execute');g.e('TraceAvailable.else',g.o('8279D66A')+'.execute')
    g.run();save(C)

if stage=='player_phase':
    # Leave input binding in the character; all acceptance and stamina decisions now belong to combat.
    for gate,target in [('739273B9','660FE2E6'),('2B0F8B37','9ADCC399')]:
        nd=svc.get_node_details(P,'EventGraph',old(P,gate))
        pin=next(q for q in nd.input_pins if q.pin_name=='execute')
        assert len(pin.connections)==1
        src,sp=str(pin.connections[0]).split(':')
        svc.disconnect_pin(P,'EventGraph',src,sp)
        assert svc.connect_nodes(P,'EventGraph',src,sp,old(P,target),'execute')
    save(P)
    # Phase speed becomes the baseline; RefreshMovement respects any active hit-stun.
    g=Graph(B,'phase_flow')
    direct=old(B,'938320');baseline=old(B,'D152FC')
    nd=svc.get_node_details(B,'EventGraph',direct)
    sources=[str(x) for q in nd.input_pins if q.pin_name=='execute' for x in q.connections]
    for source in sources:
        nid,pin=source.split(':');svc.disconnect_pin(B,'EventGraph',nid,pin)
        assert svc.connect_nodes(B,'EventGraph',nid,pin,baseline,'execute')
    cut(B,'D152FC');g.fn('Refresh','BPC_Stat_C','RefreshMovement')
    g.e(baseline+'.then','Refresh.execute');g.e(old(B,'9FE149')+'.StatComponent','Refresh.self');g.e('Refresh.then',old(B,'C7B8CE')+'.execute')
    g.run();save(B)
