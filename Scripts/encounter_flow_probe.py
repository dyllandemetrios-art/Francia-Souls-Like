"""PIE integration probe. Real movement/attack inputs; player protected for deterministic flow coverage."""
import unreal,json
from pathlib import Path
class EncounterProbe:
    def __init__(self,protected=True):
        self.protected=protected
        self.rows=[];self.start=None;self.last=-1;self.attack=-1;self.target=None;self.done=False
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
    def action(self,n,x=1,y=0):unreal.InputService.inject_action('/Game/Input/Actions/'+n,x,y)
    def finish(self):
        if self.done:return
        self.done=True;unreal.unregister_slate_post_tick_callback(self.handle)
        (Path(unreal.Paths.project_saved_dir())/'encounter_flow_20260929.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        print('ENCOUNTER_PROBE_DONE',len(self.rows))
    def tick(self,dt):
        try:
            w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not w:return self.finish()
            p=unreal.GameplayStatics.get_player_character(w,0)
            if not p:return
            if self.start is None:
                self.start=unreal.GameplayStatics.get_time_seconds(w)
                if self.protected:p.set_editor_property('can_be_damaged',False)
            t=unreal.GameplayStatics.get_time_seconds(w)-self.start
            boss=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Boss.BP_Boss_C'))
            enemy=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Enemy.BP_Enemy_C'))
            a=boss or enemy
            if a:
                stat=a.get_editor_property('StatComponent');dead=stat.get_editor_property('bIsDead')
                if a!=self.target:
                    self.target=a
                    if not p.get_editor_property('bIsLocked'):self.action('IA_Lock')
                if not dead and t>1:
                    if p.get_distance_to(a)>145:self.action('IA_Move',0,1)
                    if p.get_distance_to(a)<200 and int(t/.55)!=self.attack:
                        self.attack=int(t/.55);self.action('IA_Attack')
                if boss and dead:
                    if not hasattr(self,'win'):self.win=t
                    if 2<t-self.win<4:self.action('IA_Move',1,0)
                    if t-self.win>5:return self.finish()
            if t-self.last>.2:
                self.last=t
                row={'t':round(t,2),'pos':str(p.get_actor_location()),'speed':p.character_movement.max_walk_speed,'locked':p.get_editor_property('bIsLocked'),'player_hp':p.get_editor_property('StatComponent').get_editor_property('CurrentHealth'),'protected':self.protected}
                if a:row.update(target=a.get_class().get_name(),hp=stat.get_editor_property('CurrentHealth'),dead=dead,dist=p.get_distance_to(a))
                if enemy:row.update(dormant=enemy.get_editor_property('bDormant'),controller=bool(enemy.get_controller()))
                if boss:row.update(phase=boss.get_editor_property('Phase'),announcement=boss.get_editor_property('PhaseAnnouncement'))
                for h in unreal.WidgetLibrary.get_all_widgets_of_class(w,unreal.load_class(None,'/Game/UI/WBP_HUD.WBP_HUD_C'),False):
                    row.update(label=str(h.get_editor_property('BossLabel').get_text()),message=str(h.get_editor_property('EncounterResult').get_text()))
                self.rows.append(row)
            if t>100:self.finish()
        except Exception as ex:
            self.rows.append({'error':str(ex)});self.finish()
encounter_probe=EncounterProbe()
