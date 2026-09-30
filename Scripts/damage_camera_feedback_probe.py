"""Runtime-only verification that both confirmed-damage paths move the player camera."""
import json
from pathlib import Path
import unreal

class DamageCameraProbe:
    def __init__(self):
        self.start = None; self.player_hit = False; self.enemy_hit = False; self.rows = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        path = Path(unreal.Paths.project_saved_dir())/'damage_camera_feedback_probe_20260930.json'
        path.write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        print('DAMAGE_CAMERA_PROBE_DONE',path)
    def tick(self,dt):
        w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not w:return self.finish()
        p=unreal.GameplayStatics.get_player_character(w,0)
        e=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Enemy.BP_Enemy_C'))
        if not p or not e:return
        now=unreal.GameplayStatics.get_time_seconds(w)
        if self.start is None:
            self.start=now;p.set_editor_property('can_be_damaged',True)
        t=now-self.start
        if t>.5 and not self.player_hit:
            self.player_hit=True;unreal.GameplayStatics.apply_damage(p,1,None,e,None)
        if t>1.8 and not self.enemy_hit:
            self.enemy_hit=True;unreal.GameplayStatics.apply_damage(e,1,p.get_controller(),p,None)
        pcm=unreal.GameplayStatics.get_player_camera_manager(w,0)
        cam=pcm.get_camera_rotation();control=p.get_controller().get_control_rotation()
        delta=unreal.MathLibrary.normalized_delta_rotator(cam,control)
        self.rows.append({'t':round(t,3),'player_hp':p.get_editor_property('StatComponent').get_editor_property('CurrentHealth'),
                          'enemy_hp':e.get_editor_property('StatComponent').get_editor_property('CurrentHealth'),
                          'pitch_delta':round(delta.pitch,3),'yaw_delta':round(delta.yaw,3),'roll_delta':round(delta.roll,3)})
        if t>3.2:self.finish()
damage_camera_probe=DamageCameraProbe()
