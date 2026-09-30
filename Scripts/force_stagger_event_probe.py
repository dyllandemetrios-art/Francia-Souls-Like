"""Runtime-only duration check for ForceFinisherStagger."""
import json
from pathlib import Path
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
boss = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/AI/BP_Boss.BP_Boss_C'))
stat = boss.get_editor_property('StatComponent')
force_stagger_rows = []
force_stagger_start = unreal.GameplayStatics.get_time_seconds(world)
stat.call_method('ForceFinisherStagger')

def force_stagger_tick(dt):
    now = unreal.GameplayStatics.get_time_seconds(world) - force_stagger_start
    force_stagger_rows.append({'t': round(now, 3), 'stunned': stat.get_editor_property('bIsHitStunned'),
                               'speed': boss.character_movement.max_walk_speed,
                               'montage': boss.get_current_montage().get_name() if boss.get_current_montage() else None})
    if now > 1.6:
        unreal.unregister_slate_post_tick_callback(force_stagger_handle)
        path = Path(unreal.Paths.project_saved_dir()) / 'force_stagger_event_probe_20260930.json'
        path.write_text(json.dumps(force_stagger_rows, indent=2), encoding='utf-8')
        print('FORCE_STAGGER_EVENT_DONE', path)

force_stagger_handle = unreal.register_slate_post_tick_callback(force_stagger_tick)
