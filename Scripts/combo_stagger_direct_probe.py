"""Runtime verification of the confirmed-hit branch while ComboIndex is the third step."""
import json
from pathlib import Path
import unreal

class DirectThirdHitProbe:
    def __init__(self):
        self.start = None
        self.calls = set()
        self.trace_fired = False
        self.rows = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        path = Path(unreal.Paths.project_saved_dir()) / 'combo_stagger_direct_probe_20260930.json'
        path.write_text(json.dumps(self.rows, indent=2), encoding='utf-8')
        print('DIRECT_THIRD_HIT_DONE', path)

    def tick(self, dt):
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return self.finish()
        player = unreal.GameplayStatics.get_player_character(world, 0)
        boss = unreal.GameplayStatics.get_actor_of_class(
            world, unreal.load_class(None, '/Game/AI/BP_Boss.BP_Boss_C'))
        if not player or not boss:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if self.start is None:
            self.start = now
            player.set_actor_location(boss.get_actor_location() - boss.get_actor_forward_vector() * 125, False, False)
            player.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
                player.get_actor_location(), boss.get_actor_location()), False)
        t = now - self.start
        combat = player.get_editor_property('CombatComponent')
        stat = boss.get_editor_property('StatComponent')
        for key, at in [('a', .2), ('b', .7), ('c', 1.2)]:
            if t >= at and key not in self.calls:
                self.calls.add(key)
                combat.call_method('RequestAttack')
        if combat.get_editor_property('ComboIndex') == 2 and not self.trace_fired:
            self.trace_fired = True
            combat.call_method('DoAttackTrace')
        self.rows.append({
            't': round(t, 3), 'hp': stat.get_editor_property('CurrentHealth'),
            'stunned': stat.get_editor_property('bIsHitStunned'),
            'speed': boss.character_movement.max_walk_speed,
            'combo': combat.get_editor_property('ComboIndex'),
            'trace_fired': self.trace_fired,
            'montage': boss.get_current_montage().get_name() if boss.get_current_montage() else None,
        })
        if t > 4.5:
            self.finish()

direct_third_probe = DirectThirdHitProbe()
