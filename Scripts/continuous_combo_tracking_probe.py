"""PIE probe: disturb the camera throughout combo step 3 and measure target facing."""
import json
from pathlib import Path
import unreal

class ContinuousComboTrackingProbe:
    def __init__(self):
        self.start=None; self.calls=set(); self.rows=[]; self.done=False
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
    def finish(self):
        if self.done:return
        self.done=True;unreal.unregister_slate_post_tick_callback(self.handle)
        path=Path(unreal.Paths.project_saved_dir())/'continuous_combo_tracking_probe_20260930.json'
        path.write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        print('CONTINUOUS_COMBO_TRACKING_DONE',len(self.rows),path)
    def tick(self,dt):
        try:
            w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not w:return self.finish()
            p=unreal.GameplayStatics.get_player_character(w,0)
            e=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Enemy.BP_Enemy_C'))
            if not p or not e:return
            now=unreal.GameplayStatics.get_time_seconds(w)
            if self.start is None:
                self.start=now;p.set_editor_property('can_be_damaged',False)
                p.set_actor_location(e.get_actor_location()-unreal.Vector(160,0,0),False,False)
            t=now-self.start
            if t>.35 and 'lock' not in self.calls:self.calls.add('lock');unreal.InputService.inject_action('/Game/Input/Actions/IA_Lock',1,0)
            # Montage lengths are ~2.4 s / 3.53 s / 4.9 s. Queue one input
            # during each active step instead of collapsing all presses into
            # the single boolean buffer.
            for key,at in [('a',3.1),('b',4.0),('c',6.0)]:
                if t>=at and key not in self.calls:self.calls.add(key);unreal.InputService.inject_action('/Game/Input/Actions/IA_Attack',1,0)
            combat=p.get_editor_property('CombatComponent');combo=combat.get_editor_property('ComboIndex');attacking=combat.get_editor_property('bIsAttacking')
            if t>9.0 and t<12.4:
                rot=p.get_controller().get_control_rotation();p.get_controller().set_control_rotation(unreal.Rotator(rot.pitch,rot.yaw+22,rot.roll))
            target=unreal.MathLibrary.find_look_at_rotation(p.get_actor_location(),e.get_actor_location())
            err=abs(unreal.MathLibrary.normalized_delta_rotator(p.get_actor_rotation(),target).yaw)
            if t>8.5:self.rows.append({'t':round(t,3),'combo':combo,'attacking':attacking,'yaw_error':round(err,2),'hp':e.get_editor_property('StatComponent').get_editor_property('CurrentHealth'),'distance':round(p.get_distance_to(e),2)})
            if t>14:return self.finish()
        except Exception as ex:self.rows.append({'error':str(ex)});self.finish()
continuous_combo_tracking_probe=ContinuousComboTrackingProbe()
