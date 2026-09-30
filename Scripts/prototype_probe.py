"""PIE-only probe. Execute inside Unreal Python; does not save runtime changes."""
import unreal
import json
import time
from pathlib import Path

class PrototypeProbe:
    def __init__(self, mode='combat'):
        self.mode = mode
        self.rows = []
        self.start = None
        self.last_sample = -1
        self.fired = set()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def action(self, name, x=1, y=0):
        unreal.InputService.inject_action('/Game/Input/Actions/' + name, x, y)

    def once(self, key, t, at, fn):
        if t >= at and key not in self.fired:
            self.fired.add(key)
            fn()

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        path = Path(unreal.Paths.project_saved_dir()) / ('prototype_' + self.mode + '.json')
        path.write_text(json.dumps(self.rows, indent=2), encoding='utf-8')
        print('PROTOTYPE_PROBE_DONE', self.mode, len(self.rows), str(path))

    def tick(self, dt):
        try:
            w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not w:
                return
            p = unreal.GameplayStatics.get_player_character(w, 0)
            if not p:
                return
            if self.start is None:
                self.start = unreal.GameplayStatics.get_time_seconds(w)
                self.b = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/AI/BP_Boss.BP_Boss_C'))
                if self.mode not in ['mortality', 'final_combat']:
                    p.set_editor_property('can_be_damaged', False)
            t = unreal.GameplayStatics.get_time_seconds(w) - self.start
            b = self.b
            ps = p.get_editor_property('StatComponent')
            bs = b.get_editor_property('StatComponent')
            pc = p.get_editor_property('CombatComponent')
            if self.mode == 'lock':
                self.once('lock', t, .5, lambda: self.action('IA_Lock'))
                if 1 < t < 3: self.action('IA_Move', 1, 0)
                self.once('off', t, 3.5, lambda: self.action('IA_Lock'))
                self.once('on', t, 4.5, lambda: self.action('IA_Lock'))
                self.once('kill', t, 6, lambda: unreal.GameplayStatics.apply_damage(b, 9999, p.get_controller(), p, None))
                self.once('deadlock', t, 7, lambda: self.action('IA_Lock'))
                limit = 9
            elif self.mode in ['combat', 'final_combat']:
                self.once('lock', t, .5, lambda: self.action('IA_Lock'))
                if not bs.get_editor_property('bIsDead') and not ps.get_editor_property('bIsDead'):
                    if p.get_distance_to(b) > 140: self.action('IA_Move', 0, 1)
                    bm=b.get_current_montage()
                    can_dodge=(self.mode=='final_combat' and bm and 'Attack' in bm.get_name()
                        and not pc.get_editor_property('bIsAttacking') and not pc.get_editor_property('bIsDodging'))
                    if can_dodge:
                        self.once('evade'+str(int(t/1.2)),t,1,lambda:self.action('IA_Dodge'))
                    else:
                        interval=.8 if self.mode=='final_combat' else .45
                        self.once('attack'+str(int(t/interval)), t, 1, lambda: self.action('IA_Attack'))
                if bs.get_editor_property('bIsDead') and not ps.get_editor_property('bIsDead'):
                    if not hasattr(self,'victory_time'):
                        self.victory_time=t
                    # Verify that the surviving player can actually move after combat.
                    if 3 < t-self.victory_time < 5:
                        self.action('IA_Move',1,0)
                limit = 65
            elif self.mode == 'dodge':
                self.once('lock', t, .5, lambda: self.action('IA_Lock'))
                if 1 < t < 3: self.action('IA_Move', 1, 0)
                self.once('dodge', t, 1.5, lambda: self.action('IA_Dodge'))
                self.once('attack', t, 4, lambda: self.action('IA_Attack'))
                self.once('queue', t, 4.5, lambda: self.action('IA_Attack'))
                self.once('enable-damage', t, 4.8, lambda: p.set_editor_property('can_be_damaged', True))
                self.once('kill-combo', t, 5, lambda: unreal.GameplayStatics.apply_damage(p, 9999, b.get_controller(), b, None))
                limit = 12
            elif self.mode == 'boundaries':
                self.once('lock',t,.5,lambda:self.action('IA_Lock'))
                for key,at,damage in [('60pct',1.5,240),('30pct',3,180),('below30',4.5,1),('dead',6,9999)]:
                    self.once(key,t,at,lambda damage=damage:unreal.GameplayStatics.apply_damage(b,damage,p.get_controller(),p,None))
                limit = 8
            elif self.mode == 'mortality':
                self.once('lock', t, .5, lambda: self.action('IA_Lock'))
                if ps.get_editor_property('bIsDead'):
                    self.once('deadattack', t, 0, lambda: self.action('IA_Attack'))
                    self.once('deaddodge', t, 0, lambda: self.action('IA_Dodge'))
                limit = 18
            else:
                limit = 10
            if t - self.last_sample >= .1:
                self.last_sample = t
                pl=p.get_actor_location(); bl=b.get_actor_location()
                pm=p.get_current_montage(); bm=b.get_current_montage()
                rot=p.get_control_rotation()
                self.rows.append(dict(t=round(t,3), hp=ps.get_editor_property('CurrentHealth'),
                    stamina=ps.get_editor_property('CurrentStamina'), dead=ps.get_editor_property('bIsDead'),
                    boss_hp=bs.get_editor_property('CurrentHealth'), boss_dead=bs.get_editor_property('bIsDead'),
                    phase=b.get_editor_property('Phase'), rate=b.get_editor_property('AttackPlayRate'),
                    recovery=b.get_editor_property('AttackRecovery'), lock=p.get_editor_property('bIsLocked'),
                    p=[pl.x,pl.y,pl.z], b=[bl.x,bl.y,bl.z], yaw=rot.yaw,pitch=rot.pitch,
                    speed=p.character_movement.max_walk_speed, boss_speed=b.character_movement.max_walk_speed,
                    accel=p.character_movement.max_acceleration,hit_stunned=ps.get_editor_property('bIsHitStunned'),
                    attack_lock=ps.get_editor_property('bAttackMovementLocked'),
                    attacking=pc.get_editor_property('bIsAttacking'),dodging=pc.get_editor_property('bIsDodging'),
                    pm=pm.get_name() if pm else None,bm=bm.get_name() if bm else None))
                widgets=unreal.WidgetLibrary.get_all_widgets_of_class(w,unreal.load_class(None,'/Game/UI/WBP_HUD.WBP_HUD_C'),False)
                if widgets:
                    hud=widgets[0]
                    self.rows[-1].update(boss_bar=hud.get_editor_property('BossBar').percent,
                        boss_label=str(hud.get_editor_property('BossLabel').text),
                        result=str(hud.get_editor_property('EncounterResult').text))
            if t >= limit:
                self.finish()
        except Exception as exc:
            self.rows.append({'error': str(exc)})
            self.finish()

probe = PrototypeProbe(globals().get('probe_mode', 'lock'))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
