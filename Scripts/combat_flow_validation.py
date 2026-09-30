"""PIE regression scenarios for state ownership, input queues and stamina.
Only runtime actors are changed. Stops boss AI during these isolated scenarios.
Run with PIE stopped, through Unreal Python. Does not modify/save game assets.
"""
import unreal
import json
from pathlib import Path

class CombatFlowValidation:
    def __init__(self):
        self.start=None;self.done=set();self.rows=[];self.checks=[];self.last=-1
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
    def check(self,name,ok,**details):
        self.checks.append(dict(name=name,passed=bool(ok),**details))
    def once(self,key,t,at,fn):
        if t>=at and key not in self.done:
            self.done.add(key);fn()
    def state(self,t):
        st=self.st;co=self.co;p=self.p
        pm=p.get_current_montage()
        return dict(t=round(t,3),hp=st.get_editor_property('CurrentHealth'),stamina=st.get_editor_property('CurrentStamina'),
            dead=st.get_editor_property('bIsDead'),hit=st.get_editor_property('bIsHitStunned'),
            attack_lock=st.get_editor_property('bAttackMovementLocked'),attack=co.get_editor_property('bIsAttacking'),
            dodge=co.get_editor_property('bIsDodging'),queued_dodge=co.get_editor_property('bDodgeQueued'),
            speed=p.character_movement.max_walk_speed,accel=p.character_movement.max_acceleration,
            baseline_speed=st.get_editor_property('SavedMaxWalkSpeedHit'),baseline_accel=st.get_editor_property('SavedMaxAccelHit'),
            montage=pm.get_name() if pm else None)
    def queued_dodge(self):
        before=self.st.get_editor_property('CurrentStamina')
        cost=self.st.get_editor_property('AttackStaminaCost')
        self.co.call_method('RequestAttack')
        for _ in range(5):self.co.call_method('Dodge')
        after=self.st.get_editor_property('CurrentStamina')
        self.check('queued_dodge_charged_only_when_started',after==before-cost and self.co.get_editor_property('bDodgeQueued') and not self.co.get_editor_property('bIsDodging'),before=before,after=after)
    def hit_during_attack(self):
        self.co.call_method('RequestAttack')
        unreal.GameplayStatics.apply_damage(self.p,10,self.b.get_controller(),self.b,None)
        before=self.st.get_editor_property('CurrentStamina')
        self.co.call_method('RequestAttack');self.co.call_method('Dodge')
        s=self.state(3)
        self.check('hit_cancels_actions_and_rejects_new_requests_without_cost',s['hit'] and not s['attack'] and not s['dodge'] and not s['attack_lock'] and s['stamina']==before,state=s)
    def recovered(self):
        s=self.state(4.3)
        self.check('repeated_hits_restore_baseline',not s['hit'] and s['speed']==500 and s['accel']==1600 and s['baseline_speed']==500 and s['baseline_accel']==1600,state=s)
    def combo_spam(self):
        before=self.st.get_editor_property('CurrentStamina');cost=self.st.get_editor_property('AttackStaminaCost')
        for _ in range(10):self.co.call_method('RequestAttack')
        after=self.st.get_editor_property('CurrentStamina')
        self.check('combo_buffer_does_not_charge_repeated_presses',after==before-cost,before=before,after=after)
    def empty_stamina(self):
        for _ in range(12):self.st.call_method('ConsumeAttackStamina')
        self.co.call_method('RequestAttack');self.co.call_method('Dodge')
        s=self.state(8)
        self.check('empty_stamina_rejects_actions',s['stamina']==0 and not s['attack'] and not s['dodge'],state=s)
    def phase_during_hit(self):
        unreal.GameplayStatics.apply_damage(self.b,170,self.p.get_controller(),self.p,None)
        bs=self.b.get_editor_property('StatComponent')
        self.check('phase_change_respects_hit_stun',self.b.get_editor_property('Phase')==2 and bs.get_editor_property('bIsHitStunned') and self.b.character_movement.max_walk_speed==0,phase=self.b.get_editor_property('Phase'),speed=self.b.character_movement.max_walk_speed)
    def death_during_attack(self):
        self.co.call_method('RequestAttack');self.co.call_method('Dodge')
        unreal.GameplayStatics.apply_damage(self.p,9999,self.b.get_controller(),self.b,None)
    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        path=Path(unreal.Paths.project_saved_dir())/'combat_flow_validation.json'
        path.write_text(json.dumps(dict(checks=self.checks,rows=self.rows),indent=2),encoding='utf-8')
        print('COMBAT_FLOW_VALIDATION',sum(c['passed'] for c in self.checks),'/',len(self.checks),str(path))
    def tick(self,dt):
        try:
            w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not w:return
            if self.start is None:
                self.p=unreal.GameplayStatics.get_player_character(w,0)
                if not self.p:return
                self.start=unreal.GameplayStatics.get_time_seconds(w)
                self.b=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Boss.BP_Boss_C'))
                ctrl=self.b.get_controller()
                ctrl.get_editor_property('brain_component').stop_logic('Isolated combat regression tests')
                ctrl.stop_movement()
                self.st=self.p.get_editor_property('StatComponent');self.co=self.p.get_editor_property('CombatComponent')
                self.check('component_references_initialized',self.co.get_editor_property('StatRef')==self.st and self.st.get_editor_property('CombatRef')==self.co)
            t=unreal.GameplayStatics.get_time_seconds(w)-self.start
            self.once('queue',t,.4,self.queued_dodge)
            self.once('queue_finished',t,2.7,lambda:self.check('queued_dodge_executed_and_recovered',any(r['dodge'] for r in self.rows) and self.p.character_movement.max_walk_speed==500,state=self.state(t)))
            self.once('hit',t,3,self.hit_during_attack)
            self.once('hit_again',t,3.2,lambda:unreal.GameplayStatics.apply_damage(self.p,10,self.b.get_controller(),self.b,None))
            self.once('recovered',t,4.3,self.recovered)
            self.once('spam',t,5,self.combo_spam)
            self.once('empty',t,8,self.empty_stamina)
            self.once('regen',t,11.5,lambda:self.check('stamina_regenerates',self.st.get_editor_property('CurrentStamina')>20,stamina=self.st.get_editor_property('CurrentStamina')))
            self.once('phase',t,12,self.phase_during_hit)
            self.once('phase_recover',t,13,lambda:self.check('phase_speed_restored_after_hit',self.b.character_movement.max_walk_speed==520,speed=self.b.character_movement.max_walk_speed))
            self.once('death',t,15,self.death_during_attack)
            if t-self.last>=.08:
                self.last=t;self.rows.append(self.state(t))
            if t>=18:
                s=self.state(t)
                self.check('death_remains_final',s['dead'] and not s['attack'] and not s['dodge'] and not s['queued_dodge'] and s['speed']==0 and s['montage']=='AM_DKM_Death',state=s)
                self.finish()
        except Exception as ex:
            self.check('probe_exception',False,error=str(ex));self.finish()

flow_validation=CombatFlowValidation()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
