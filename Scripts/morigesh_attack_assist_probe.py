"""PIE probe: disturb camera yaw between combo presses and verify Morigesh is reacquired."""
import json
from pathlib import Path
import unreal

class MorigeshAttackAssistProbe:
    def __init__(self):
        self.start = None; self.calls = set(); self.rows = []; self.done = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        if self.done: return
        self.done = True
        unreal.unregister_slate_post_tick_callback(self.handle)
        path = Path(unreal.Paths.project_saved_dir()) / 'morigesh_attack_assist_probe_20260930.json'
        path.write_text(json.dumps(self.rows, indent=2), encoding='utf-8')
        print('MORIGESH_ATTACK_ASSIST_DONE', len(self.rows), path)

    def tick(self, dt):
        try:
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not world: return self.finish()
            player = unreal.GameplayStatics.get_player_character(world, 0)
            enemy = unreal.GameplayStatics.get_actor_of_class(
                world, unreal.load_class(None, '/Game/AI/BP_Enemy.BP_Enemy_C'))
            if not player or not enemy: return
            now = unreal.GameplayStatics.get_time_seconds(world)
            if self.start is None:
                self.start = now
                player.set_editor_property('can_be_damaged', False)
                player.set_actor_location(enemy.get_actor_location() - unreal.Vector(165, 0, 0), False, False)
                player.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
                    player.get_actor_location(), enemy.get_actor_location()), False)
            t = now - self.start
            if t >= .4 and 'lock' not in self.calls:
                self.calls.add('lock'); unreal.InputService.inject_action('/Game/Input/Actions/IA_Lock', 1, 0)
            # Let the wake-up animation finish, then turn the camera 95 degrees away before every press.
            for key, at in [('a', 3.2), ('b', 3.72), ('c', 4.25)]:
                if t >= at and key not in self.calls:
                    self.calls.add(key)
                    rot = player.get_controller().get_control_rotation()
                    player.get_controller().set_control_rotation(unreal.Rotator(rot.pitch, rot.yaw + 95.0, rot.roll))
                    unreal.InputService.inject_action('/Game/Input/Actions/IA_Attack', 1, 0)
            stat = enemy.get_editor_property('StatComponent')
            target_rot = unreal.MathLibrary.find_look_at_rotation(player.get_actor_location(), enemy.get_actor_location())
            yaw_error = abs(unreal.MathLibrary.normalized_delta_rotator(player.get_actor_rotation(), target_rot).yaw)
            self.rows.append({'t': round(t, 3), 'hp': stat.get_editor_property('CurrentHealth'),
                              'dead': stat.get_editor_property('bIsDead'),
                              'locked': player.get_editor_property('bIsLocked'),
                              'combo': player.get_editor_property('CombatComponent').get_editor_property('ComboIndex'),
                              'yaw_error': round(yaw_error, 2), 'distance': round(player.get_distance_to(enemy), 2)})
            if stat.get_editor_property('bIsDead') or t > 9.0: self.finish()
        except Exception as exc:
            self.rows.append({'error': str(exc)}); self.finish()

morigesh_assist_probe = MorigeshAttackAssistProbe()
