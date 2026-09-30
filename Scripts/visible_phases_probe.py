"""PIE flow test with real inputs, pausing melee in phase 2 to observe ranged attacks."""
import unreal,json
from pathlib import Path
class VisiblePhaseProbe:
    def __init__(self):
        self.rows=[];self.start=None;self.sample=-1;self.attack=-1;self.phase2=None;self.seen=set();self.done=False
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
    def inject_action(self,n,x=1,y=0):unreal.InputService.inject_action('/Game/Input/Actions/'+n,x,y)
    def finish(self):
        if self.done:return
        self.done=True;unreal.unregister_slate_post_tick_callback(self.handle)
        (Path(unreal.Paths.project_saved_dir())/'visible_phases_probe.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        print('VISIBLE_PHASE_PROBE_DONE',len(self.rows))
    def tick(self,dt):
        try:
            w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not w:return self.finish()
            p=unreal.GameplayStatics.get_player_character(w,0)
            if not p:return
            if self.start is None:
                self.start=unreal.GameplayStatics.get_time_seconds(w)
                p.set_editor_property('can_be_damaged',False)
            t=unreal.GameplayStatics.get_time_seconds(w)-self.start
            b=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Boss.BP_Boss_C'))
            e=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Enemy.BP_Enemy_C'))
            a=b or e
            if a:
                st=a.get_editor_property('StatComponent');dead=st.get_editor_property('bIsDead')
                if not dead and not p.get_editor_property('bIsLocked'):self.inject_action('IA_Lock')
                phase=b.get_editor_property('Phase') if b else 0
                if phase==2 and self.phase2 is None:self.phase2=t
                observe=phase==2 and t-self.phase2<18
                dist=p.get_distance_to(a)
                if not dead and observe:
                    if dist<620:self.inject_action('IA_Move',0,-1)
                elif not dead:
                    if dist>145:self.inject_action('IA_Move',0,1)
                    if dist<210 and int(t/.65)!=self.attack:
                        self.attack=int(t/.65);self.inject_action('IA_Attack')
                if b and dead:
                    if not hasattr(self,'win'):self.win=t
                    if 2<t-self.win<4:self.inject_action('IA_Move',1,0)
                    if t-self.win>5:return self.finish()
            shots=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Enemies/Khaimera/BP_Fireball.BP_Fireball_C'))
            for shot in shots:self.seen.add(shot.get_name())
            if t-self.sample>.15:
                self.sample=t;row={'t':round(t,2),'shots_total':len(self.seen),'shots_live':len(shots),'player_hp':p.get_editor_property('StatComponent').get_editor_property('CurrentHealth'),'player_speed':p.character_movement.max_walk_speed}
                if a:row.update(target=a.get_class().get_name(),hp=st.get_editor_property('CurrentHealth'),distance=dist)
                if b:
                    row.update(phase=phase,transition=b.get_editor_property('bPhaseTransition'),casting=b.get_editor_property('bIsCasting'),left_hidden=b.mesh.is_bone_hidden_by_name('weapon_l'),right_hidden=b.mesh.is_bone_hidden_by_name('weapon_r'),montage=str(b.get_current_montage()),boss_speed=b.character_movement.max_walk_speed)
                    for label,key in [('left','DroppedLeft'),('right','DroppedRight')]:
                        prop=b.get_editor_property(key)
                        if prop and unreal.SystemLibrary.is_valid(prop):row[label+'_prop']=str(prop.get_actor_location())
                if shots:row['shot']=str(shots[0].get_actor_location())
                self.rows.append(row)
            if t>140:self.finish()
        except Exception as ex:
            self.rows.append({'error':str(ex)});self.finish()
visible_probe=VisiblePhaseProbe()

