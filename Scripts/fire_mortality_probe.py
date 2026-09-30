"""Real-input approach to P2, then expose player to autonomous fire attacks until death."""
import unreal,json
from pathlib import Path
exec((Path(unreal.Paths.project_dir())/'Scripts/encounter_flow_probe.py').read_text(encoding='utf-8-sig').split('encounter_probe=EncounterProbe()')[0])
class FireMortalityProbe(EncounterProbe):
    def __init__(self):
        self.exposed=False;self.death_time=None;self.shots=set()
        super().__init__(True)
    def action(self,n,x=1,y=0):
        if not self.exposed:super().action(n,x,y)
    def finish(self):
        super().finish()
        (Path(unreal.Paths.project_saved_dir())/'fire_mortality_20260930.json').write_text(json.dumps({'rows':self.rows,'shots':len(self.shots)},indent=2),encoding='utf-8')
    def tick(self,dt):
        w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if w:
            p=unreal.GameplayStatics.get_player_character(w,0)
            b=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/AI/BP_Boss.BP_Boss_C'))
            if p and b and b.get_editor_property('Phase')==2:
                self.exposed=True
                if p.get_distance_to(b)<550 and not p.get_editor_property('StatComponent').get_editor_property('bIsDead'):
                    unreal.InputService.inject_action('/Game/Input/Actions/IA_Move',0,-1)
                else:p.set_editor_property('can_be_damaged',True)
            for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Enemies/Khaimera/BP_Fireball.BP_Fireball_C')):self.shots.add(a.get_name())
            if p and p.get_editor_property('StatComponent').get_editor_property('bIsDead'):
                now=unreal.GameplayStatics.get_time_seconds(w)
                if self.death_time is None:self.death_time=now
                if now-self.death_time>3:return self.finish()
        super().tick(dt)
fire_mortality=FireMortalityProbe()
