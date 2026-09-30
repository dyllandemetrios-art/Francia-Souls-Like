"""Runtime-only probe: create Khaimera, perform one real three-hit combo, record stagger."""
import json
from pathlib import Path
import unreal

class ComboStaggerProbe:
    def __init__(self):
        self.start = None
        self.boss_start = None
        self.calls = set()
        self.rows = []
        self.done = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        if self.done:
            return
        self.done = True
        unreal.unregister_slate_post_tick_callback(self.handle)
        path = Path(unreal.Paths.project_saved_dir()) / 'combo_stagger_probe_20260930.json'
        path.write_text(json.dumps(self.rows, indent=2), encoding='utf-8')
        print('COMBO_STAGGER_PROBE_DONE', len(self.rows), path)

    def tick(self, dt):
        try:
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not world:
                return self.finish()
            now = unreal.GameplayStatics.get_time_seconds(world)
            player = unreal.GameplayStatics.get_player_character(world, 0)
            if not player:
                return
            if self.start is None:
                self.start = now
                player.set_editor_property('can_be_damaged', False)
                enemy = unreal.GameplayStatics.get_actor_of_class(
                    world, unreal.load_class(None, '/Game/AI/BP_Enemy.BP_Enemy_C'))
                if enemy:
                    enemy.call_method('SpawnBossNow')
            boss = unreal.GameplayStatics.get_actor_of_class(
                world, unreal.load_class(None, '/Game/AI/BP_Boss.BP_Boss_C'))
            if not boss:
                return
            if self.boss_start is None:
                self.boss_start = now
                # Face each other at trace range; all subsequent attacks use normal montage notifies.
                player.set_actor_location(boss.get_actor_location() - boss.get_actor_forward_vector() * 150, False, False)
                player.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
                    player.get_actor_location(), boss.get_actor_location()), False)
                controller = boss.get_controller()
                if controller and controller.get_editor_property('brain_component'):
                    controller.get_editor_property('brain_component').stop_logic('Combo stagger probe')
                if controller:
                    controller.stop_movement()
            t = now - self.boss_start
            combat = player.get_editor_property('CombatComponent')
            stat = boss.get_editor_property('StatComponent')
            for key, at in [('a', .40), ('b', .88), ('c', 1.38)]:
                if t >= at and key not in self.calls:
                    self.calls.add(key)
                    combat.call_method('RequestAttack')
            self.rows.append({
                't': round(t, 3),
                'boss_hp': stat.get_editor_property('CurrentHealth'),
                'boss_stunned': stat.get_editor_property('bIsHitStunned'),
                'boss_speed': boss.character_movement.max_walk_speed,
                'combo_index': combat.get_editor_property('ComboIndex'),
                'attacking': combat.get_editor_property('bIsAttacking'),
                'boss_montage': boss.get_current_montage().get_name() if boss.get_current_montage() else None,
            })
            if t > 5.0:
                self.finish()
        except Exception as exc:
            self.rows.append({'error': str(exc)})
            self.finish()

combo_stagger_probe = ComboStaggerProbe()
