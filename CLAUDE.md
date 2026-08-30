<!-- BEGIN PROJECT STATE (maintenu à la main — ne pas régénérer via un outil, éditer directement) -->
# Francia_Souls_Like — état du projet (dernière MAJ: 28/08/2026)

## Contexte
Projet séparé de **Francia** (autre .uproject, autre Content). Le Dark Knight Male
vient de Francia et est **migré par copie disque brute** (pas de Content Migration
UE classique) vers `/Game/Characters/Dark_Knight/...` — chemins identiques dans les
deux projets donc aucun redirecteur cassé. Robocopy source→dest si besoin de
recopier :
```
robocopy "D:\Unreal Engine\Francia\Content\Characters\Dark_Knight\Dark_Knight_Male" "D:\Unreal Engine\Francia_Souls_Like\Content\Characters\Dark_Knight\Dark_Knight_Male" /E /XO
```

## ⚠️ Gotcha connu — NE PAS toucher
- **`ABP_Unarmed.uasset` (dans Dark_Knight_Male/Animations) est CASSÉ / signalé buggé par
  l'utilisateur.** Il référence des animations du squelette Mannequin standard
  (`MM_Jump`, `MM_Fall_Loop`, `MM_Land` sous `.../Mannequins/Anims/Unarmed/Jump`) via un
  Control Rig de retargeting, alors que le mesh Dark Knight utilise son propre squelette
  `SK_DKM_Full`. Chargement de ces MM_* échoue avec `Invalid USkeleton supplied` tant que
  `SK_Mannequin` et le retargeter ne sont pas aussi migrés — chaîne de dépendance fragile.
  → **Ne pas réutiliser/éditer ABP_Unarmed. Tout est reconstruit en neuf sur SK_DKM_Full,
  sans dépendance au squelette Mannequin.**

## Convention: guerrier "Alert" (le seul mode utilisé)
Animations `Anim_DKM_*_Alert_*` (Idle/Walk/Run) sur le squelette `SK_DKM_Full`, mesh
`SKM_DKM_Full_With_Sword` (épée déjà skinnée — pas d'attache d'arme séparée nécessaire).
Run_Alert n'existe qu'en Fwd/FwdLeft/FwdRight ; Bwd/Left/Right/BwdLeft/BwdRight à vitesse
"run" réutilisent les anims Walk_Alert (c'est le pattern déjà utilisé par le
`BS_StrafeMovement` d'origine du pack, reproduit à l'identique pour la version Alert).

## Fait
- [x] Assets Dark_Knight_Male migrés et vérifiés (aucune dépendance externe cassée hors ABP_Unarmed, ignoré).
- [x] Input ZQSD : `IMC_Default` → `IA_Move` remappé (Z=avant/W ex, Q=gauche/A ex, S et D inchangés — identiques en AZERTY). Modifiers copiés (SwizzleAxis sur Z, Negate sur Q). Sauvegardé.
- [x] `BS_DKM_Alert_Movement` (`.../Dark_Knight_Male/Animations/`) — Blend Space 2D (Direction
  -180..180 grid 8 / Speed 0..500 grid 4), 14 samples calqués sur `BS_StrafeMovement` mais avec
  les anims `_Alert` (Idle_Alert au centre, Run_Alert_Fwd/FwdLeft/FwdRight à vitesse run, le
  reste des directions en Walk_Alert à vitesse run — même pattern que l'original).
- [x] `ABP_DKM_Alert` (même dossier) — AnimBP neuf sur `SK_DKM_Full`, indépendant d'ABP_Unarmed.
  EventGraph : BlueprintUpdateAnimation → TryGetPawnOwner → GetVelocity/VSize → Speed,
  GetActorRotation + CalculateDirection → Direction. AnimGraph : BlendSpacePlayer(BS_DKM_Alert_Movement)
  X=Direction Y=Speed → Output Pose. Compile clean.
- [x] `BP_DarkKnight_Alert` (`.../Dark_Knight_Male/Blueprints/`) — **hérite de
  `BP_ThirdPersonCharacter`** (pas un Character vierge : ça donne gratuitement tout le
  pipeline input Enhanced Input — fonctions Move/Aim, IA_Move/IA_Look/IA_Jump déjà bindées,
  CameraBoom+FollowCamera déjà en place, mapping context géré par le PlayerController). On ne
  surcharge que : `Mesh.SkeletalMeshAsset` = SKM_DKM_Full_With_Sword, `Mesh.AnimClass` =
  ABP_DKM_Alert, `Mesh` relative loc/rot copiés du parent, `CharacterMovement.bOrientRotationToMovement=false`,
  `bUseControllerRotationYaw=true` (strafe : le perso garde le dos face caméra en bougeant sur le côté).
  **Piège appris** : un Character Blueprint vierge (parent = `Character` nu) n'a AUCUNE logique
  d'input — `BlueprintService.set_component_property` échoue aussi silencieusement (retourne False)
  sur les composants natifs hérités comme `CharacterMesh0`/`Mesh` ; passer par le CDO en Python
  (`unreal.get_default_object(bp.generated_class())` puis `get_editor_property("mesh")` etc.) au
  lieu de `set_component_property`.
- [x] `BP_ThirdPersonGameMode.DefaultPawnClass` = `BP_DarkKnight_Alert` (remplace le Manny). Si le
  GameMode ou le BP perso sont supprimés/recréés au même chemin, **repasser cette référence** —
  elle devient `None` silencieusement après un delete+recreate tant qu'on ne la resaisit pas.
- [x] Vérifié en PIE (capture `game`) : perso bien droit, caméra ancrée derrière lui, avance
  avec Z (percute un pilier du niveau ThirdPerson par défaut), strafe latéral avec D — le perso
  garde le dos à la caméra pendant le strafe (comportement souls-like voulu).

## Piège récurrent — PIE headless
- `LevelEditorSubsystem.editor_request_begin_play()` / `.editor_request_end_play()` pour piloter
  le PIE en Python (pas de toolset `EditorAppToolset.StartPIE` enregistré dans ce build — la
  liste réelle des toolsets VibeUE est dans le message d'erreur si `vibeue.exec_tool` échoue).
- **`is_in_play_in_editor()` ou tout appel Python peut faire planter le game thread pendant
  ~2min** si une popup modale apparaît côté éditeur (ex: au premier lancement du PIE). Symptôme :
  le prochain `execute_python_code` time-out. Vérifier
  `Saved/VibeUE/Signals/editor-<pid>-health.json` (`gameThreadStallSeconds`) plutôt que de
  spammer des appels — il faut cliquer la popup manuellement dans l'éditeur, aucun outil ne le
  fait à distance.
- `unreal.EditorAssetLibrary.load_asset(...)` peut retourner `None` de façon intermittente
  pendant que le PIE tourne (le monde dupliqué par le PIE perturbe la résolution de chemin) —
  si un load échoue bizarrement, vérifier `is_in_play_in_editor()` d'abord.
- `InputService.inject_action` n'a d'effet que sur UN tick moteur — inutile d'enchaîner
  plusieurs `inject_action` dans un seul `execute_python_code` (le jeu ne tick pas pendant que
  le script Python bloque le game thread). Utiliser `inject_key(key, "down")` puis un appel
  séparé plus tard pour `"up"` — le temps réel qui passe ENTRE deux appels MCP fait avancer le
  jeu normalement.

## Fait (suite) — Combo d'attaque
- [x] 3 Montages (`AM_DKM_Attack_01/02/03`, dossier `.../Animations/Montages/`) créés depuis les
  AnimSequences `Anim_DKM_Attack_01/02/03` via `AnimMontageService.create_montage_from_animation`.
  Slot par défaut = "DefaultSlot" (existe automatiquement, pas eu besoin de le créer sur le squelette).
- [x] `ABP_DKM_Alert` AnimGraph modifié : `BlendSpacePlayer.Pose → Slot('DefaultSlot').Source →
  Slot.Pose → Output Pose` (au lieu de brancher direct BlendSpace→Output). C'est ce qui permet aux
  montages de s'afficher par-dessus la locomotion.
- [x] `BPC_Combat` (`.../Dark_Knight_Male/Blueprints/`, ActorComponent) — logique de combo, **sans
  Delay ni Function classiques** (pas de `create_function` disponible dans ce build — aucun toolset
  natif Epic n'est enregistré, seulement les services VibeUE ; solution : tout en **Custom Events**,
  qui supportent les nœuds latents et sont appelables comme des fonctions via `function_call`
  `{"class":"BPC_Combat_C","function":"<NomEvent>"}`, self-pin auto-résolu pour un appel intra-classe).
  - Variables : `ComboIndex`(int), `bIsAttacking`(bool), `bComboQueued`(bool), `Montage1/2/3`(AnimMontage).
  - `RequestAttack` (custom event, appelé depuis l'input) : si pas en train d'attaquer → démarre
    combo (ComboIndex=0, appelle `PlayStep`) ; sinon → `bComboQueued=true` (bufferise l'input).
  - `PlayStep` (custom event) : branche sur `ComboIndex` (0/1/2) → joue Montage1/2/3 via
    `Character.PlayAnimMontage` (self = `GetOwner()` casté en Character — **pas** en Actor : le
    self-pin de `GetOwner` doit être typé `class:"ActorComponent"`, sinon erreur de compile "this
    blueprint (self) is not an Actor") → `KismetSystemLibrary.K2_SetTimer(Object=<K2Node_Self>,
    FunctionName="OnStepTimerElapsed", Time=<durée retournée par PlayAnimMontage>)`.
  - `OnStepTimerElapsed` (custom event, appelé par le timer) : si `bComboQueued AND ComboIndex<2` →
    incrémente et rappelle `PlayStep` ; sinon → reset (`bIsAttacking=false`, `ComboIndex=0`).
  - **Piège appris** : le pin `Object` de `K2_SetTimer` (et de tout appel qui a besoin d'une
    référence "self" explicite en tant que valeur, pas comme target de node) ne peut PAS recevoir
    la string `"self"` comme pin default — il faut un vrai node `K2Node_Self` câblé. Le trouver
    via `discover_nodes(bp_path, "Get a reference to self")` → spawner key `"SPAWN
    K2Node_Self|Get a reference to self"` → `create_node_by_key` puis `connect_nodes`.
  - **Piège appris** : `add_function_parameter` échoue silencieusement (retourne False) sur un
    Custom Event — ça ne marche que sur de vraies fonctions (indisponibles ici). Contournement :
    l'event lit directement les variables membres (`ComboIndex` etc.) au lieu de recevoir des
    paramètres.
- [x] Composant `CombatComponent` (instance de `BPC_Combat`) ajouté à `BP_DarkKnight_Alert`, avec
  `Montage1/2/3` pointés vers les 3 AM_DKM_Attack créés (set via CDO comme pour le Mesh).
- [x] Input `IA_Attack` (Boolean) créé, mappé sur **clic gauche** dans `IMC_Default`. Câblé dans
  `BP_DarkKnight_Alert.EventGraph` : `IA_Attack.Started → CombatComponent.RequestAttack` (via
  `add_function_call_on_variable`, qui résout automatiquement le type du composant).
- [x] Vérifié en PIE (capture `game`) : clic gauche déclenche bien l'anim d'attaque (épée levée),
  jouée par-dessus la pose Idle_Alert, caméra toujours dans le dos. Combo 2e/3e coup pas vérifié
  visuellement (timing de capture trop imprécis en headless) mais la logique compile clean et suit
  exactement le même chemin que le 1er coup.

## Fait (suite) — BPC_Stat (santé) + Dodge
- [x] `BPC_Stat` (ActorComponent) : `MaxHealth`/`CurrentHealth`/`bIsDead` + variables "porteuses"
  `PendingDamage`/`PendingHeal` (même contournement que `ComboIndex` — pas de paramètres sur les
  Custom Events dans ce build). Events `ApplyDamage` (lit `PendingDamage`, clamp 0..Max, si
  santé ≤0 → `bIsDead=true` + joue `DeathMontage` via `Character.PlayAnimMontage`) et `Heal`
  (lit `PendingHeal`, clamp). `DeathMontage` = `AM_DKM_Death` créé depuis `Anim_DKM_Death` (même
  pattern que les Attack montages). Composant `StatComponent` ajouté à `BP_DarkKnight_Alert`.
  **Pour infliger des dégâts depuis ailleurs** : `Set PendingDamage` puis appeler `ApplyDamage`
  sur le composant (2 appels, pas un seul avec paramètre — limitation du build).
- [x] Dodge ajouté dans `BPC_Combat` (pas un composant séparé — dépend de `bIsAttacking` du même
  composant). Variables `bIsDodging`, `DodgeMontage` (AnimMontage, **laissé vide** — à toi de
  l'assigner sur le composant `CombatComponent` de `BP_DarkKnight_Alert` une fois l'anim
  importée), `DodgeDistance`(600), `DodgeDuration`(0.35s). Event `Dodge` : si ni en train
  d'attaquer ni déjà en dodge → `LaunchCharacter` (impulsion vers l'avant, XY override, Z libre
  pour garder la gravité) + `PlayAnimMontage(DodgeMontage)` (ne fait rien si vide, sans crash) +
  timer `OnDodgeFinished` qui reset `bIsDodging`. **Fonctionnel dès maintenant sans animation**
  (juste l'impulsion), l'anim s'ajoutera automatiquement une fois `DodgeMontage` assigné.
- [x] Input `IA_Dodge` (Boolean) créé, mappé sur **Left Shift**. Câblé dans
  `BP_DarkKnight_Alert.EventGraph` : `IA_Dodge.Started → CombatComponent.Dodge`.
- [x] Testé en PIE : Shift gauche ne crash rien, `is_in_play_in_editor` reste vrai après. Pas de
  vérification visuelle fine du déplacement (impulsion trop rapide pour la capture headless).

## Récap composants sur `BP_DarkKnight_Alert`
`CombatComponent` (BPC_Combat : combo d'attaque + dodge) et `StatComponent` (BPC_Stat : santé + endurance).

## Fait (suite) — Robustesse mesh/anim + Endurance + Bindings gamepad
- [x] **Diagnostic "perso cassé"** : le mesh/AnimClass n'étaient assignés que via édition directe
  du CDO en Python (fragile en théorie face à un reload complet). **Fix** : `BP_DarkKnight_Alert`
  force maintenant lui-même son mesh (`DefaultMeshOverride`) et son AnimClass
  (`DefaultAnimClassOverride`, type `TSubclassOf<AnimInstance>`) dans son propre **Event
  BeginPlay** via `SetSkeletalMeshAsset`/`SetAnimInstanceClass` — garanti correct à CHAQUE
  lancement, indépendamment de tout état de CDO. Testé en PIE après ce fix : pose Idle_Alert
  correcte dès le spawn, épée bien présente sur le mesh (confirmée aussi par le screenshot
  d'attaque où la lame est visible, levée) — pas réussi à reproduire "épée au sol" ; probablement
  un test sur un état antérieur (avant la rotation du mesh corrigée / avant l'héritage de
  `BP_ThirdPersonCharacter`). Si ça persiste après ce fix, il faut une repro précise (screenshot).
- [x] **Toujours en alerte** : déjà le cas de fait — `ABP_DKM_Alert` n'utilise QUE
  `BS_DKM_Alert_Movement` (anims `_Alert`), aucun état "normal"/désarmé n'existe dans le graphe.
  Rien à changer ici, c'est la seule locomotion qui existe dans ce projet.
- [x] **Endurance** ajoutée dans `BPC_Stat` : `MaxStamina`(100), `CurrentStamina`(100),
  `StaminaRegenPerSec`(15/s), `StaminaRegenDelay`(1s avant que la régén reprenne après une
  dépense), `AttackStaminaCost`(20), `DodgeStaminaCost`(25), `bRegenPaused`. Boucle de régén via
  `K2_SetTimer` looping (0.2s) démarrée au `BeginPlay` du composant. Events
  `ConsumeAttackStamina`/`ConsumeDodgeStamina` (dépensent + mettent la régén en pause
  `StaminaRegenDelay` secondes) + `EndRegenPause`. Tous ces chiffres sont de simples variables du
  composant — ajustables directement dans les Class Defaults de `BPC_Stat` sans toucher au graphe.
- [x] **Gate stamina** câblé dans `BP_DarkKnight_Alert` : `IA_Attack`/`IA_Dodge` vérifient
  maintenant `StatComponent.CurrentStamina >= coût` (lecture cross-composant via `member_get`)
  AVANT d'appeler `ConsumeXStamina` puis l'action réelle. Plus d'attaque/dodge illimité. Testé en
  PIE : la stamina baisse bien après une attaque (confirmé numériquement, 100→89 avec un peu de
  régén déjà repartie entre les deux lectures).
- [x] **Gamepad** : `IA_Attack` → `Gamepad_FaceButton_Right` (X/Carré), `IA_Dodge` →
  `Gamepad_LeftShoulder` (LB/L1). Move/Look/Jump déjà hérités du template ThirdPerson
  (`Gamepad_Left2D`/`Gamepad_Right2D`/`Gamepad_FaceButton_Bottom`).

## Table des touches actuelle (IMC_Default)
| Action | Clavier/Souris | Manette |
|---|---|---|
| Déplacement | Z/Q/S/D (+ flèches) | Stick gauche |
| Regarder | Souris | Stick droit |
| Saut | Espace | A/Croix (FaceButton_Bottom) |
| Attaque (combo) | Clic gauche | X/Carré (FaceButton_Right) |
| Dodge | Shift gauche | LB/L1 (LeftShoulder) |

## 🔴 LE bug des "jambes figées" — root cause réelle (corrigé)
**Symptôme** : le perso glissait sans animer les jambes, quelle que soit la vitesse.
**Cause** : dans `ABP_DKM_Alert.EventGraph`, le nœud `Vector Length` (VSize) avait son pin **`A`
JAMAIS connecté** à `GetVelocity.ReturnValue` (`DefaultValue="0, 0, 0"`). La connexion avait
échoué dans un `build_graph` antérieur — le nœud VSize n'existait pas encore au moment où la
connexion a été tentée (warning `Connection 7: Source ref 'VSize' not found`), et je n'ai jamais
repris cette connexion en créant le nœud ensuite. Résultat : `Speed = VSize(0,0,0) = 0` en
permanence → le Blend Space restait bloqué sur l'échantillon Idle → **jambes immobiles**, alors
que `Direction` (lui correctement câblé) fonctionnait.
**Preuve du diagnostic** : en PIE, `VELOCITY=(0, 53.9, 0)` mais `Speed var = 0.0`.
**Fix** : `connect_nodes(GetVelocity.ReturnValue → VectorLength.A)`. Vérifié après coup :
`Speed var = 9.6098` pour une vélocité de `9.609` — la variable suit exactement la vitesse, et
capture d'écran montrant une vraie pose de marche (jambes dissociées) au lieu du idle symétrique.

**LEÇON GÉNÉRALE (importante)** : `build_graph` peut retourner des **warnings** de connexions
ignorées (`Connection N: Source/Target ref 'X' not found`) tout en rapportant un succès partiel,
et le Blueprint **compile sans erreur** malgré un pin d'entrée resté sur sa valeur par défaut.
Un "compiled: True, compile_errors: 0" NE PROUVE PAS que le graphe est correct. Après tout
`build_graph`, **auditer les pins d'entrée réellement connectés** :
```python
for n in unreal.BlueprintService.get_nodes_in_graph(bp, graph, 0, "", True):
    for p in n.pins:
        if p.is_input and not p.is_connected and p.pin_name not in ("self","execute"):
            print("PIN NON CONNECTE:", n.node_title, p.pin_name, p.default_value)
```
ou `get_node_details(bp, graph, node_id)` pour un nœud précis (montre `connections` par pin).

## ⚠️ RÉGRESSION corrigée — ne PAS refaire ça
Le "fix de robustesse" BeginPlay (`SetSkeletalMeshAsset` + `SetAnimInstanceClass` appelés à
chaque lancement) a **cassé l'AnimInstance** : pose T ("mode Jésus") au spawn ET pendant le
déplacement. Root cause probable : appeler `SetSkeletalMeshAsset` réinitialise l'AnimInstance, et
enchaîner `SetAnimInstanceClass` juste après dans le même exec ne relie pas proprement le nouveau
instance à temps. **Ces 2 appels ont été supprimés du BeginPlay.** Le CDO seul (mesh + AnimClass
mis via `unreal.get_default_object(...).set_editor_property(...)` puis `compile_blueprint` +
`save_asset`) est ce qui marche réellement — confirmé par test PIE : idle correct (pose Alert,
pas de T-pose) ET animation de déplacement correcte (testé avec Z maintenu, foulée visible). **Ne
plus toucher au mesh/AnimClass depuis BeginPlay.** Si un souci de persistance réapparaît un jour,
diagnostiquer d'abord avant de rajouter du code — ne pas répéter cette régression.

**Piège annexe découvert pendant cette session** : après un `editor_request_end_play()`, vérifier
`is_in_play_in_editor()` avant de continuer — il peut rester `True` un moment (ou la première
requête ne pas avoir été traitée), et toute édition de Blueprint pendant que le PIE tourne encore
échoue silencieusement (`load_asset` retourne `None`, `delete_node`/`build_graph` retournent
`False` sans erreur explicite). Toujours confirmer `False` avant d'éditer.

## Réglages locomotion / dodge (validés en PIE)
- `MaxWalkSpeed` passé de 600 → **500** pour coller exactement au max du Blend Space (Y 0..500).
  Sinon la vitesse réelle dépassait l'échantillon max → patinage de pieds. Accélération 1600,
  freinage 1800, friction sol 9 (réactif, orienté souls-like).
- **Dodge directionnel** (`BPC_Combat`) : la direction n'est plus figée sur l'avant. Chaîne
  `GetVelocity → Normalize` + `VSize > 50` → `KismetMathLibrary.SelectVector(A=vel normalisée,
  B=ActorForward, bPickA=enMouvement)` → `* DodgeDistance` → `LaunchCharacter`. Donc : esquive
  dans la direction du déplacement, et vers l'avant si à l'arrêt. `DodgeDistance` = 900.
  **Validé en PIE** : strafe latéral → +226 sur Y / 0 sur X ; à l'arrêt → +225 sur X / 0 sur Y.
- `DodgeMontage` toujours vide (anim non fournie) — l'esquive fonctionne sans, l'anim se
  branchera automatiquement une fois assignée sur le `CombatComponent`.

## Méthode de test runtime en PIE (leçons)
- `inject_key(k,"down")` ne **maintient pas** la touche de façon fiable sur plusieurs frames
  (vélocité observée ~54 au lieu de 500) : bon pour déclencher une action ponctuelle, mauvais
  pour tester une locomotion soutenue.
- Pour un test déterministe : écrire directement `movement.set_editor_property("velocity", ...)`
  puis appeler l'event dans **le même script** (aucun tick entre deux instructions d'un même
  script), et lire le résultat au tool call suivant.
- Mesurer un **delta de position** plutôt qu'une vélocité : la vélocité retombe à 0 entre deux
  appels MCP (~1 s de temps réel s'écoule), la position elle est cumulative et persiste.
- Ne PAS bricoler `set_actor_location` + friction/gravité sur l'instance vivante pour "aider" le
  test : ça a laissé le CharacterMovement dans un état cassé (perso gelé en MOVE_FALLING,
  position figée alors que le temps monde avançait). Redémarrer le PIE proprement à la place.
- Un event Blueprint (Custom Event) est appelable depuis Python sur l'instance :
  `comp.call_method("Dodge")` — très pratique pour tester une mécanique sans passer par l'input.

## Fait (suite) — Saut désactivé + immobilité en combat + direction du combo
- [x] **Saut désactivé** : mappings `IA_Jump` retirés d'`IMC_Default` (clavier + manette) ET
  `JumpZVelocity` mis à 0 sur `BP_DarkKnight_Alert` en double sécurité. Espace/Croix ne font plus
  rien.
- [x] **Immobilité pendant attaque** (`BPC_Combat`) : au début de `RequestAttack` (une seule fois
  par combo, pas à chaque coup), sauvegarde `CharacterMovement.MaxWalkSpeed`/`MaxAcceleration`
  dans `SavedMaxWalkSpeed`/`SavedMaxAcceleration`, puis force les deux à 0. Restauré à la fin du
  combo (branche `OnStepTimerElapsed` qui reset `bIsAttacking`). **Piège appris** : impossible de
  faire un `variable_set` cross-composant générique sur une propriété d'un component NATIF
  (`CharacterMovementComponent`) — le node produit n'a ni pin `self` ni pin de donnée. Solution :
  chercher le spawner dédié via `discover_nodes(bp, "Set Max Walk Speed")` →
  `"SPAWN K2Node_VariableSet|Set Max Walk Speed"` → `create_node_by_key`, qui lui a un vrai pin
  `self`. **Validé numériquement en PIE** (appel direct `comp.call_method("RequestAttack")`) :
  `MaxWalkSpeed`/`MaxAcceleration` passent bien à `0.0` immédiatement, `SavedMaxWalkSpeed` gardait
  la valeur d'origine (500), et redevenaient 500 une fois le combo terminé.
- [x] **Direction du combo suit la caméra à chaque coup** (pas figée sur la direction du 1er coup) :
  dans `PlayStep`, juste avant le lunge (`LaunchCharacter`), on lit `GetControlRotation` (yaw
  seul, pitch/roll à 0 via `BreakRotator`/`MakeRotator`) et on fait `SetActorRotation` dessus —
  donc `GetActorForwardVector` (utilisé pour le lunge) reflète toujours la direction visée AU
  MOMENT de CE coup, pas celle du début du combo. Câblage vérifié compilé + tous pins connectés.
  **Non prouvé en live** : le test via `ctrl.set_control_rotation()` en Python pour simuler un
  changement de visée pendant le combo 2e coup n'a pas tenu (la rotation contrôleur revenait à 0
  toute seule — probablement le système d'input vivant qui reprend la main sur la rotation entre
  deux appels MCP, pas un bug du graphe). Le graphe est structurellement correct (lit
  `GetControlRotation` en direct à chaque `PlayStep`, pas une valeur mise en cache) mais **à
  reconfirmer par un test manuel réel** (tourner la souris pendant le combo).

## Fait (suite) — Dodge sur clic droit + combo rapide (0.5s/coup)
- [x] `IA_Dodge` déplacé de **Shift gauche** → **clic droit** (+ direction du déplacement en
  cours, inchangé). Shift n'est plus lié à rien.
- [x] **Diagnostic lenteur des attaques** : les AnimSequences sources (`Anim_DKM_Attack_01/02/03`)
  durent respectivement **2.4s / 3.5s / 4.9s** — bien trop long pour un rythme souls-like.
- [x] `BPC_Combat` : nouvelle variable `ComboStepDuration` (float, 0.5s) — **remplace** l'ancien
  système où le timer d'enchaînement attendait `PlayAnimMontage.ReturnValue` (la durée réelle du
  montage). Chaque coup dure maintenant exactement `ComboStepDuration`, quelle que soit la durée
  de l'anim source ; le montage suivant coupe/blend automatiquement celui en cours (comportement
  standard de `PlayAnimMontage`). Réglable direct dans les Class Defaults sans toucher au graphe.
- [x] `InPlayRate` des 3 `Play Anim Montage` (Play1/2/3) mis à **2.2** pour que le geste visuel
  suive le rythme plus rapide au lieu de sembler figé/lent au début du swing.
  **Approximatif** : `AttackTraceDelay` (0.25s, moment où les dégâts sont appliqués) n'a pas été
  recalculé précisément par rapport aux keyframes de l'anim — à ajuster à l'oeil si le coup
  "touche" visuellement avant/après l'impact réel de la lame.
- [x] Vérifié structurellement (pas par un timing live, round-trip MCP trop lent pour mesurer
  0.5s) : `Timer1/2/3.Time` connectés à `ComboStepDuration`, `InPlayRate`=2.2 sur les 3 Play nodes.
  Cette même classe `BPC_Combat` étant partagée par les ennemis Khaimera/Morigesh, le rythme
  rapide s'applique aussi à eux automatiquement.

## Fait (suite) — Retour en arrière demandé + gate directionnel du dodge
- [x] **Vitesse d'attaque remise à la normale** : `InPlayRate` des 3 `Play Anim Montage` repassé à
  1.0, `Timer1/2/3.Time` re-branché sur `PlayX.ReturnValue` (durée réelle du montage) au lieu de
  `ComboStepDuration`. La variable `ComboStepDuration` existe toujours sur le composant mais n'est
  plus utilisée par le graphe (laissée telle quelle, inoffensive).
  **Contexte important** : l'utilisateur a précisé que `Anim_DKM_Attack_01/02/03` ne sont **pas 3
  attaques indépendantes** mais une seule animation qui **s'incrémente** (01 = coup 1 seul, 02 =
  coup 1+2, 03 = coup 1+2+3 complet). Le système actuel (3 montages distincts joués en séquence)
  ne correspond donc plus au design voulu — **refonte en attente**, voir plus bas.
- [x] `IA_Dodge` remis sur **Shift gauche** (le passage sur clic droit demandé plus tôt a été
  annulé par l'utilisateur).
- [x] **Gate directionnel sur le dodge** : l'event `Dodge` (BPC_Combat) vérifie maintenant
  `Pawn.GetLastMovementInputVector()` (magnitude > 0.1) EN PLUS de `!bIsAttacking && !bIsDodging`
  — impossible de esquiver à l'arrêt, une touche ZQSD doit être maintenue. Compilé clean, tous
  pins connectés.

## ⚠️ EN ATTENTE — refonte du combo (bloqué sur info utilisateur)
L'utilisateur a ajouté 2 AnimNotify sur `AM_DKM_Attack_03` (qui contient le combo complet 3 coups
en une seule anim) pour piloter le nombre de coups selon le nombre de clics. Idée : jouer
**uniquement `AM_DKM_Attack_03`** en continu ; à chaque notify (`ComboGate1`≈2.4s,
`ComboGate2`≈3.5s — points de transition entre les coups, déduits des durées d'Attack_01/02), si
le joueur n'a PAS re-cliqué avant ce point → `Montage_Stop` (coupe le combo là). Si buffer actif
→ laisser continuer. Remplace tout le système `Montage1/2/3` + `PlayStep` par index actuel.
**Bloqué** : je ne peux pas lire les notifies existants sur le montage via l'API disponible
(`AnimMontageService.list_notifies` / `get_notify_info` retournent vide/None même en écriture
confirmée — bug d'outillage). J'ai ajouté puis retiré 2 notifies tests (`ComboGate1`/`ComboGate2`
à 2.4s/3.5s) pour ne pas dupliquer les siennes à l'aveugle. **Attendre le nom exact des 2
notifies de l'utilisateur** (ou repartir sur les miennes aux mêmes instants si l'utilisateur
confirme) avant de reconstruire `BPC_Combat`.
- Reproche justifié de l'utilisateur : `BPC_Combat` est un vrai sac de nœuds sans commentaires
  après plusieurs sessions d'ajouts. **Prévu** : nettoyer avec `add_comment_around_nodes` par bloc
  logique (Attack/Combo, Dodge, Hit trace, Hit stop, Movement freeze) + `auto_layout_graph`, à
  faire EN MÊME TEMPS que la refonte du combo pour ne pas nettoyer deux fois.

## Fait (suite) — Caméra verrouillée à distance fixe + vérification position post-combo
- [x] **Diagnostic "le perso revient à sa position initiale"** : testé numériquement en PIE, combo
  complet 3 coups (bufferisé via `comp.call_method("RequestAttack")` x3 avec dilation temps
  ralentie pour observer chaque étape) — position finale stable à `178.96` sur X (pas de reset à
  0), `bIsAttacking=False`. **Pas de bug de position/root motion** (root motion est d'ailleurs
  désactivée sur ces anims, translation totale nulle — pas la cause possible). Le déplacement
  total (~60 unités/coup à cause de la friction sol qui freine vite le lunge) est probablement
  juste trop discret pour se remarquer — **si tu veux plus de percussion, augmenter
  `LungeStrength`** (450 actuellement) sur `CombatComponent`.
- [x] **Caméra verrouillée à distance fixe** (`bDoCollisionTest=false` sur `CameraBoom`) : avant,
  le bras se rétractait automatiquement près des murs/obstacles (comportement `SpringArm` par
  défaut), donc la distance caméra-perso variait — pas "lock". Vérifié en PIE : distance
  **exactement 400 unités** en terrain ouvert ET collé à un mur extérieur (avant : aurait
  varié). **Piège appris** : `CameraBoom` est un composant SCS du PARENT `BP_ThirdPersonCharacter`
  (`is_inherited: False` là-bas), pas de `BP_DarkKnight_Alert` — `set_component_property`/
  `get_component_property` retournent silencieusement `False`/`None` sur l'enfant pour un
  composant hérité (même limitation que `Mesh` découverte plus tôt cette session). Il faut éditer
  le composant à sa source (le parent) via `BlueprintService.set_component_property`, la valeur
  se propage automatiquement à tous les enfants qui ne l'ont pas surchargée.
  **CameraLag était déjà désactivé** (position ET rotation, `bEnableCameraLag=False`) — pas la
  cause du souci de caméra.

## Fait (suite) — Lunge recalibré + trace ancrée sur la main + tentative BPI
- [x] **Lunge d'attaque nettement plus perceptible** : le gel de mouvement pendant l'attaque
  couvre maintenant aussi `GroundFriction` (→0→2.0 final, testé) et `BrakingDecelerationWalking`
  (→700), pas seulement `MaxWalkSpeed`/`MaxAcceleration` — avant, la friction du sol tuait le
  lunge en une fraction de seconde (~58 unités total sur tout un combo). **Calibré et validé en
  PIE** : ~112 unités par coup, ~337 unités sur un combo complet de 3 coups, tout est bien
  restauré à la fin (`MaxWalkSpeed=500`, `GroundFriction=9`). `LungeStrength`=450 (à ajuster dans
  les Class Defaults si besoin — attention, une première tentative à 750 + friction 0 + braking
  150 donnait plus de 1600 unités sur 2 coups, beaucoup trop).
- [x] **Diagnostic caméra "pas lock"** : recherché dans tous les Blueprints concernés (perso,
  controller, parent ThirdPerson, BPC_Combat) — **aucun code ne modifie `TargetArmLength` au
  runtime**. Le fix précédent (`bDoCollisionTest=false`) est confirmé actif et suffisant ; pas de
  cause supplémentaire trouvée. Si le souci persiste après retest, il faudra une repro précise
  (vidéo/screenshot) car je ne peux plus avancer par déduction seule ici.
- [x] **Trace d'attaque ancrée sur la main** (`BPC_Combat.DoAttackTrace`) : remplace l'ancienne
  approximation (position perso + vecteur avant × portée, qui ne suivait pas le vrai mouvement du
  bras) par `Mesh.GetSocketLocation("hand_r")` — suit maintenant la vraie position de la main
  pendant l'animation. `AttackRadius` remonté à 100 (la lame `SM_DKM_Sword` fait ~130 de long,
  donc un rayon de 100 depuis la main couvre l'essentiel de sa portée). **Piège** : ce squelette
  (`SK_DKM_Full`) n'a **aucun bone/socket dédié à la pointe de la lame** — testé tous les noms
  plausibles (`weapon_r`, `sword`, `blade`, `SwordSocket`...), seul `hand_r` existe. Un vrai trace
  directionnel (base→pointe de lame) demanderait d'ajouter un bone enfant sur `hand_r` avec un
  offset — pas fait, l'orientation locale de `hand_r` n'est pas connue avec certitude (risque de
  pointer le trace dans le mauvais sens sans repère visuel). Nettoyé les 5 nœuds de l'ancienne
  approximation, devenus orphelins (le graphe reste imparfait mais un peu moins pire).
- [~] **BPI (Blueprint Interface) pour les dégâts** : **bloqué par une limitation d'outillage
  réelle**, pas contourné. `unreal.BlueprintInterfaceFactory` permet de créer l'ASSET interface
  (`/Game/Combat/BPI_Damageable` créé), mais **il n'existe aucune méthode dans ce build pour
  ajouter une fonction à un Blueprint** (`create_function`/`add_function` n'existent nulle part
  dans `BlueprintService`, confirmé plusieurs fois cette session — seuls
  `add_function_parameter`/`add_function_local_variable` existent et exigent une fonction déjà
  créée). Impossible donc de définir la signature de la fonction d'interface par script.
  **Ce qui marche déjà et reste en place** : le pipeline de dégâts natif Unreal
  (`GameplayStatics.ApplyDamage` → `AActor::ReceiveAnyDamage`, implémenté sur `BP_DarkKnight_Alert`,
  `BP_Khaimera`, `BP_Morigesh`) — c'est fonctionnellement un système universel "n'importe quel
  acteur peut réagir aux dégâts", déjà testé et fiable. **Si l'utilisateur veut vraiment une vraie
  BPI Unreal** : ouvrir `/Game/Combat/BPI_Damageable` dans l'éditeur, clic droit dans MyBlueprint →
  New Function (ex: `ApplyHitDamage(float Damage, AActor* Instigator)`), me redonner la main —
  je peux ensuite câbler `add_interface()` sur les 3 BP et router `DoAttackTrace` dessus au lieu
  du pipeline natif.

## Fait (suite) — Notify de dégâts, hit-react, HUD
- [x] **`AN_AttackDamage` (notify, `/Game/Variant_Combat/Anims/`)** — c'est l'asset combat natif
  d'Epic déjà présent dans le projet (avec `BPI_Attacker`/`BPI_Damageable`). Sa fonction
  `Received_Notify` appelait à l'origine une interface (`Do Attack Trace` sur `BPI_Attacker`) —
  **impossible à implémenter** (même blocage que d'habitude : pas de `create_function` pour les
  fonctions d'interface paramétrées). Contournement : j'ai réécrit `Received_Notify` pour appeler
  directement `BPC_Combat.DoAttackTrace` (event déjà existant) via `GetComponentByClass` +
  `Cast` — bypasse l'interface entièrement, même résultat visible. Notify posé sur les 9 montages
  d'attaque (DK, Khaimera, Morigesh) à ~40-60% de la durée. **L'ancien déclenchement par
  `SetTimer(AttackTraceDelay)` dans `PlayStep` a été retiré** (le notify est plus précis, calé
  sur l'anim). Les interfaces `BPI_Attacker`/`BPI_Damageable` restent ajoutées aux 3 personnages
  (`add_interface` fonctionne) mais **aucune fonction n'est implémentée dessus** — décoratif pour
  l'instant, le vrai pipeline de dégâts reste `GameplayStatics.ApplyDamage`/`ReceiveAnyDamage`.
- [x] **Hit-react** (`BPC_Stat`) : à réception de dégâts (si pas mortel), gèle
  `MaxWalkSpeed`/`MaxAcceleration` (sauvegardés/restaurés comme pour l'attaque), joue
  `HitReactMontage`, puis restaure après `HitStunDuration` (0.4s) via `OnHitStunEnd`. Montages
  créés : `AM_DKM_HitReact` (Alert_Fwd), `AM_Khaimera_HitReact`, `AM_Morigesh_HitReact`
  (`HitReact_Front` des deux) — assignés sur les 3 `StatComponent`. **Validé en PIE** :
  `GameplayStatics.apply_damage()` → `MaxWalkSpeed` passe à `0.0` immédiatement.
  **Limite** : toujours la réaction "Front" seulement, pas de sélection Fwd/Bwd/Left/Right selon
  la direction du coup (les anims existent — `Anim_DKM_Hit_Alert_Bwd/Left/Right`,
  `HitReact_Back/Left/Right` — pas câblées, à faire si besoin).
- [x] **HUD** (`/Game/UI/WBP_HUD`) : `CanvasPanel` racine, 2 `ProgressBar` ancrées **haut-gauche**
  (`Anchors Min=Max=(0,0)`), `PB_Health2` rouge (0.85,0.05,0.05) à (30,30), `PB_Stamina2` jaune
  (0.95,0.85,0.05) à (30,60), taille 300×20. `Event Tick` lit `StatComponent` du pawn possédé
  (`GetOwningPlayerPawn`→`GetComponentByClass`→`Cast`) et met à jour `Percent` en direct
  (`CurrentHealth/MaxHealth`, `CurrentStamina/MaxStamina`). Ajouté à l'écran via
  `BP_DarkKnight_Alert.BeginPlay` (`Create Widget` + `AddToViewport`). **Validé par lecture live
  en PIE** (`spawn_widget_in_pie` + `get_live_property` : Percent/couleur corrects) — **PAS
  validé par capture d'écran** : l'outil `capture_preview` renvoyait un rendu visiblement en
  cache (image identique malgré des changements totalement différents), et `capture_image
  source=game` a échoué à répétition pendant ce test ("Slate screenshot failed"). Si le HUD
  n'apparaît pas à l'écran chez toi, c'est à vérifier en priorité — la donnée est prouvée
  correcte, l'affichage réel non confirmé visuellement de mon côté.
- [~] **Core Systems (asset `/Game/CoreSystems/`)** : repéré (`BPC_health`, `BPC_stamina`,
  `WBP_Hud`, `WBP_masterProgressBAr`, `BPI_vitalSystemsInterface`) mais **PAS utilisé** — j'ai
  gardé mon propre `BPC_Stat` + un HUD maison plutôt que de tout migrer vers ce système, faute de
  budget dans cette session pour un rework aussi large sans risquer de casser ce qui fonctionne
  déjà. Si tu veux vraiment migrer vers Core Systems, il faut me le redemander explicitement —
  gros chantier séparé.

## Fait (suite) — Refonte combo : une seule anim continue (fix "réactivité")
- [x] **Root cause du bug "ma course se coupe pour répéter l'animation"** : `Attack_01/02/03`
  sont incrémentales (01=coup1 seul 2.4s, 02=coup1+2 3.5s, 03=coup1+2+3 4.9s complet), mais
  `BPC_Combat` jouait encore 3 **montages séparés** en séquence — donc au 2e coup, `Attack_02`
  redémarrait de zéro et **rejouait le coup 1** avant d'enchaîner, d'où la coupure visible.
- [x] **Fix** : nouveau bool `bCumulativeCombo` sur `BPC_Combat` (false par défaut = ancien
  comportement 3-montages, toujours utilisé par Khaimera/Morigesh dont les anims Melee/Primary
  sont bien 3 clips distincts). **Activé uniquement sur `BP_DarkKnight_Alert`** : `Montage1`
  repointé vers `AM_DKM_Attack_03` (l'anim complète), jouée **une seule fois** au premier clic.
  Les clics suivants n'appellent plus jamais `PlayStep` (qui relançait le montage) — ils se
  contentent de `bComboQueued=true`, et à chaque fenêtre (`Window1Duration`=2.4s,
  `Window2Duration`=1.1s, `Window3Duration`=1.4s — calées sur les durées cumulatives
  d'Attack_01/02/03), `OnStepTimerElapsed` vérifie juste le buffer et programme la fenêtre
  suivante SANS toucher à l'animation (elle continue de jouer toute seule). Si pas de clic dans
  la fenêtre → `Montage_Stop` (blend 0.15s) coupe le combo là où il en est, proprement.
  **Validé en PIE** : `anim.get_current_active_montage()` confirme qu'`AM_DKM_Attack_03` tourne
  comme UNE seule anim (pas de montage différent par coup), et l'état revient proprement à
  `bIsAttacking=False` / `ComboIndex=0` après.
- [x] **3 notifies `AttackDamage`** posées sur `AM_DKM_Attack_03` (une par coup, aux ~impacts
  estimés : 0.5s / 2.8s / 4.0s — approximatif, pas de repère visuel exact) — avant il n'y en
  avait qu'une, donc les coups 2 et 3 n'infligeaient jamais de dégâts.
  **Non testé en PIE avec précision** (latence du canal de test trop grande pour observer un
  buffer de clic à la fenêtre près) — la logique est saine et compile clean, mais **à confirmer
  par toi en jeu réel** : enchaîne les clics pendant que tu avances (Z) et dis-moi si ça reste
  fluide maintenant.

## Fait (suite) — Diagnostic 3 bugs signalés (dodge direction / combo plein / HUD) — 29/08/2026
- [x] **HUD mal positionné — CAUSE RACINE TROUVÉE ET CORRIGÉE.** Le vrai problème n'était pas
  le contenu du string passé à `set_property(..., "Slot", "(LayoutData=(...))")` mais le fait
  que le pin `Slot` de `PB_Health2`/`PB_Stamina2` était carrément **`None`** (pas de
  `UCanvasPanelSlot` du tout) — confirmé via `WidgetService.get_widget_snapshot` :
  `slot_info.slot_type = "None"`. Écrire sur `"Slot"` comme si c'était un struct nativise en
  fait la string comme une **référence d'objet** (le pointeur `TObjectPtr<UPanelSlot>` lui-même)
  → si la string n'est pas un chemin d'objet valide, ça **remet le pointeur à None** au lieu
  d'éditer les champs (silencieux, `set_property` retourne quand même `True`). D'où le rendu
  "long et fin, 1/4 d'écran" : Slate applique un layout par défaut quand le Slot est invalide.
  **Fix en 2 temps** :
  1. `WidgetService.reparent_widget(bp_path, "PB_Health2", "RootCanvas")` (même parent qu'avant)
     — ça force UMG à créer un VRAI `UCanvasPanelSlot` (confirmé ensuite non-None dans
     `list_properties`).
  2. `WidgetService.set_property(bp_path, "PB_Health2", "Slot.LayoutData", "(Offsets=(Left=24,
     Top=24,Right=280,Bottom=22),Anchors=(Minimum=(X=0,Y=0),Maximum=(X=0,Y=0)),
     Alignment=(X=0,Y=0))")` — cibler **`Slot.LayoutData`** (le sous-struct interne, PAS `Slot`
     tout court) est ce qui permet d'éditer les champs du CanvasPanelSlot existant sans toucher
     au pointeur. Confirmé par `get_widget_snapshot` après coup : `slot_type: "Canvas"`, offsets
     exacts. **Vérifié visuellement en PIE (capture `game`)** : barre rouge (santé) + barre jaune
     (endurance) compactes, ancrées en haut à gauche, exactement comme demandé.
  - Nettoyé au passage les widgets orphelins `PB_Health`/`PB_Stamina`/`Bars` (reliquat d'une
    tentative `VerticalBox` abandonnée dans une session précédente, jamais supprimés) via
    `WidgetService.remove_component`.
  - **LEÇON GÉNÉRALE** : avant d'écrire sur une propriété `TObjectPtr<...>` (`Slot`, etc.) via
    `WidgetService.set_property`/`set_editor_property` avec une string de struct, vérifier
    d'abord qu'elle n'est pas `None` (`list_properties` ou `get_widget_snapshot`). Si `None`,
    la reparenter/recréer d'abord ; ensuite cibler le **sous-champ** (`Slot.LayoutData`, pas
    `Slot`) pour éditer sans écraser le pointeur.
- [x] **Combo "se réalise en entier" — testé rigoureusement, logique confirmée CORRECTE.**
  Méthode : `unreal.GameplayStatics.set_global_time_dilation(w, 0.15)` pour ralentir le temps
  jeu et pouvoir échantillonner `anim.get_current_active_montage()` /
  `comp.get_editor_property("bIsAttacking"/"ComboIndex"/"bComboQueued")` à des instants précis
  malgré la latence des allers-retours MCP (`unreal.GameplayStatics.get_time_seconds(w)` comme
  horloge, cohérente avec la dilation appliquée).
  - **1 seul `RequestAttack()`, aucun autre clic** : le montage s'arrête bien tout seul peu après
    2.4s (`Window1Duration`), `bIsAttacking` repasse à `False` — PAS de lecture jusqu'au bout
    (4.9s). Comportement correct.
  - **2 `RequestAttack()` (2e appel pendant la fenêtre 1, avant 2.4s)** : `bComboQueued` passe à
    `True` puis est consommé (`ComboIndex` 0→1) exactement au passage de la frontière 2.4s, et le
    montage continue jusqu'à ~3.5s (`Window1+Window2Duration`) puis s'arrête tout seul (pas de
    3e clic) — comportement correct, exactement le design voulu.
  - Vérifié aussi : pas de double-binding sur `IA_Attack` (une seule mapping souris + une seule
    manette dans `IMC_Default`, un seul node `EnhancedInputAction IA_Attack` dans
    `BP_DarkKnight_Alert`), le `Branch` qui gate `RequestAttack` ne dépend QUE du check stamina
    (`float>=float`), pas d'OR/bug qui forcerait un second appel implicite. Le `bCumulativeCombo`
    est bien à `True` uniquement sur l'instance `CombatComponent` de `BP_DarkKnight_Alert` (le
    class default de `BPC_Combat` reste `False`, correct pour Khaimera/Morigesh).
  - **Conclusion honnête** : je n'ai PAS réussi à reproduire le bug via les appels directs au
    composant. L'hypothèse la plus probable reste un double-déclenchement côté clic souris réel
    (double-clic involontaire perçu comme un seul clic) plutôt qu'un bug de logique — mais ça
    reste à confirmer par l'utilisateur en jouant avec attention au nombre de clics. Si le
    problème persiste malgré un seul clic bien isolé, il faudra probablement logger
    `RequestAttack`/`PlayStep` avec un compteur d'appels en conditions réelles (pas en Python) pour
    voir si `IA_Attack.Started` fire plus d'une fois par clic physique.
- [~] **Dodge direction ("ne marche qu'en avant")** : le rewiring de `CalculateDirection` pour
  lire `Pawn::GetLastMovementInputVector()` (au lieu de l'ancien `SelectVector` vélocité/forward)
  a été fait et compile clean, mais **pas re-vérifié visuellement** cette session (flakiness de
  `inject_key` pour simuler un maintien de touche en environnement d'automation — un seul essai
  antérieur avait donné un vecteur non-nul correct, les suivants sont retombés à zéro). À
  re-tester en priorité si l'utilisateur confirme que ça ne marche toujours qu'en avant.

## Fait (suite) — Session 29/08 (2e passe) : BP_Enemy collision, HUD refait, dodge réparé
### ⚠️ Correction d'une erreur d'interprétation de ma part
La demande HUD était **"centre-les en haut, long et fin, un quart de l'écran en horizontal"**.
J'avais lu "en haut à gauche" et livré ça — c'était faux. C'est maintenant **centré en haut**,
via des ancres `X 0.375 → 0.625` (= pile 25% de la largeur écran, quelle que soit la résolution).

- [x] **`/Game/AI/BP_Enemy` — collision mesh + capsule** (demande utilisateur). Parent = `Character`
  nu, donc `CharacterMesh0` et `CollisionCylinder` sont des composants **natifs hérités** →
  `BlueprintService.set_collision_settings` retourne **`False`** dessus (même famille de piège que
  `set_component_property` sur `Mesh`/`CameraBoom`). **Solution qui marche** : passer par le CDO —
  `cdo = unreal.get_default_object(bp.generated_class())`, puis
  `cdo.get_editor_property("mesh")` / `get_editor_property("capsule_component")`, puis
  `c.modify()` + `c.set_collision_profile_name("Custom")` + `c.set_collision_response_to_channel(...)`,
  puis `compile_blueprint` + `save_asset`. **Ordre important** : mettre le profil sur `"Custom"`
  AVANT de poser les réponses par canal (sinon le profil nommé réécrase tout).
  **Relever la baseline de TOUS les canaux avant de basculer sur Custom** et les reconduire
  explicitement — sinon on perd silencieusement les réponses du profil d'origine.
  Résultat vérifié après reload : mesh = Custom / QueryOnly / ObjectType Pawn / **Camera=Ignore**
  (WorldStatic+WorldDynamic+PhysicsBody+Destructible Block, Pawn+Visibility+Vehicle Ignore) ;
  capsule = Custom / QueryAndPhysics / ObjectType Pawn / **Camera=Ignore** (tout Block sauf
  Visibility Ignore). Enum Python = `unreal.CollisionResponseType.ECR_*` (PAS `CollisionResponse`).
- [x] **HUD entièrement refait** (`/Game/UI/WBP_HUD`). L'ancien avait été supprimé par
  l'utilisateur ; `HudWidgetClass` sur `BP_DarkKnight_Alert` était donc `None` (le HUD ne
  s'affichait plus du tout — ça explique le "on ne les voit pas"). Le nouveau **réutilise les
  barres du pack CoreSystems** (`WBP_masterProgressBAr`) au lieu de `ProgressBar` bruts, donc
  aspect pro (matériau + animation de dégât intégrée) : `RootCanvas` → `Health_Bar` / `Stamina_Bar`
  (deux `WBP_masterProgressBAr_C`). `WidgetService.add_component` accepte le **nom d'asset d'un WBP
  custom** comme `component_type`, pas seulement les types natifs.
  - Layout : ancres `Min=(0.375,0) Max=(0.625,0)` (25% écran, centré, collé en haut), offsets
    Health `Top=18 Bottom=14`, Stamina `Top=36 Bottom=9` → long et fin. Avec des ancres étirées en
    X, `Left`/`Right` sont des marges par rapport aux ancres ; `Top` = position Y, `Bottom` = hauteur.
  - Couleurs via `FillColour`/`BarColour`/`EmptyColour`/`UseColour` (variables publiques du pack).
  - **`Event Tick` NE SE DÉCLENCHE PAS sur ce Widget Blueprint** malgré `TickFrequency=AUTO`,
    widget `is_in_viewport=True`/`is_visible=True`, nœud `Event Tick` présent et son pin `then`
    bien connecté. Cause non élucidée. **Contournement retenu** : `Event Construct` →
    `KismetSystemLibrary::K2_SetTimer(Object=<K2Node_Self>, FunctionName="UpdateBars", Time=0.033,
    bLooping=true)` → Custom Event `UpdateBars` qui porte la chaîne de mise à jour. Plus fiable et
    plus adapté à un HUD de toute façon. (Rappel : le pin `Object` exige un vrai nœud `K2Node_Self`,
    la string `"self"` ne marche pas — piège déjà documenté plus haut.)
  - Chaîne : `UpdateBars → Cast To BPC_Stat(GetOwningPlayerPawn→GetComponentByClass(StatCompClass))
    → CurrentHealth/MaxHealth → float/float → Health_Bar.SetFillLevel(Progress)` puis idem stamina.
    `StatCompClass` = variable `TSubclassOf<ActorComponent>` mise à `BPC_Stat_C` via CDO (le pin
    `ComponentClass` n'accepte pas un chemin en string — piège habituel).
  - **Validé numériquement en PIE** : HP 75/100 → `Health_Bar.FillLevel = 0.750` ; stamina régénérée
    100/100 → `1.000`. Chaque barre suit exactement SA stat.
  - **PAS validé par capture d'écran** : `capture_image source="game"` échouait
    ("Slate screenshot failed") parce que l'éditeur affichait l'onglet **BT_Enemy** et non le
    viewport. `source="window"` marche toujours mais ne montre que l'onglet actif. → Pour une
    capture du jeu, il faut que l'onglet `Lvl_ThirdPerson` soit au premier plan.
  - Note : le remplissage visuel passe par un **matériau** (`PB_masterBar.Percent` reste à 1.0,
    c'est normal) — lire `FillLevel` sur le widget, pas `Percent` sur la ProgressBar interne.

### 🔴 Dodge — 3 VRAIS défauts trouvés (le "ça ne marche qu'en avant")
Le graphe `BPC_Combat` avait la **sélection de montage correcte** (|dir|<45→F, >135→B, signe→R/L,
seuils et 4 montages bien assignés — vérifié) mais **la propulsion était cassée** :
1. **`LaunchCharacter` du dodge avait son pin `execute` COMPLÈTEMENT DÉBRANCHÉ** → l'esquive ne
   déplaçait strictement rien, elle ne jouait que l'animation. Trouvé en traçant le flux exec
   depuis l'event `Dodge` : le nœud n'apparaissait nulle part dans la chaîne. **Rebranché** :
   `Cast To Character.then → LaunchCharacter.execute → Branch1.execute` (placé APRÈS le cast pour
   que le pin `self` soit valide, et AVANT la cascade pour lancer une seule fois).
2. **La direction de propulsion utilisait encore l'ancienne logique vélocité** :
   `SelectVector(A=Normalize(Velocity), B=ActorForward, bPickA=VSize(Velocity)>50)`. À vitesse
   faible (départ arrêté, tap directionnel) → prend `ActorForward` → **propulsion vers l'avant quoi
   qu'il arrive**. C'est LA cause du symptôme. **Corrigé** : nouveau nœud
   `KismetMathLibrary::Normal` alimenté par le MÊME `GetLastMovementInputVector` que la sélection
   de montage → `vector * DodgeDistance` → `LaunchCharacter`. Montage et déplacement partagent
   maintenant une source unique, donc ils ne peuvent plus diverger.
3. **`bXYOverride` était à `false`** sur le LaunchCharacter du dodge → mis à `true` (l'impulsion
   horizontale doit écraser la vélocité courante ; `bZOverride` reste false pour garder la gravité).
- **Nettoyage** : les 6 nœuds devenus orphelins de l'ancienne chaîne (`Select Vector`, `Normalize`
  vélocité, `Get Velocity`, `Get Actor Forward Vector`, `Vector Length`, `float > float`) ont été
  supprimés, avec une boucle qui ne supprime QUE les nœuds sans consommateur et hors flux exec.
- **NON validé en jeu** : impossible de simuler un appui directionnel maintenu depuis ce canal —
  `inject_key("D","down")` laisse `velocity` ET `GetLastMovementInputVector` à zéro (donc le gate
  `>0.1` bloque le dodge), et `add_movement_input` + timer ne marche pas non plus car
  `LastControlInputVector` est reconsommé/vidé entre deux appels MCP. **À tester manuellement.**

### Combo — mécanisme vérifié correct (mon test précédent était invalide)
Mon relevé précédent ne prouvait rien : les échantillons étaient trop espacés, le montage avait le
temps de finir naturellement (4.9s) entre deux mesures — j'avais conclu à tort.
**Nouveau test valide** (dilation 0.12, temps monde imprimé à CHAQUE relevé) : un seul
`RequestAttack`, aucun autre clic → à 2.225s le montage joue encore (pos 2.225), à 3.003s il est
**coupé** et `bIsAttacking=False`. Comme `AM_DKM_Attack_03` dure 4.9s, la coupure a bien eu lieu à
la fenêtre `Window1Duration`=2.4s. **Le combo ne se joue donc PAS en entier sur un clic.**
→ Si l'utilisateur trouve quand même que "ça part en entier", la piste restante n'est pas la
logique mais soit un double-déclenchement du clic physique, soit le fait qu'**un seul coup dure
déjà 2.4s** (longueur de l'anim source `Attack_01`) et paraît long. Levier dans ce cas :
augmenter `InPlayRate` des Play Montage ou raccourcir `Window1Duration`.
**LEÇON** : pour mesurer un événement temporel en PIE, imprimer le temps monde à chaque
échantillon et vérifier que l'intervalle encadre bien le seuil testé — sinon la mesure ne
distingue pas "coupé au seuil" de "terminé naturellement".

## 🔴🔴 ROOT CAUSE du "le perso avance puis revient à son point d'origine" (29/08, CORRIGÉ)
**Signalé 3 fois par l'utilisateur, jamais diagnostiqué correctement avant. Cause réelle trouvée :**
Les `Anim_DKM_Attack_01/02/03` ont une **grosse translation cuite dans le bone `root`** :
```
Anim_DKM_Attack_01  root: 0 -> 107.9   (len 2.40s)
Anim_DKM_Attack_02  root: 0 -> 149.2   (len 3.53s)
Anim_DKM_Attack_03  root: 0 -> 285.5   (len 4.90s)   # 0.753s->122.5 ; 1.840s->187.4
```
…mais `enable_root_motion = **False**` sur les 3. Conséquence : cette translation déplace le
**mesh visuellement** sans déplacer la capsule ; quand le montage se termine et que la pose
re-blende vers la locomotion, le mesh **claque en arrière** sur la capsule. D'où le symptôme
"il avance puis revient à sa position de départ".
- **Le `LaunchCharacter` + `LungeStrength` que j'avais ajouté était un pansement sur une jambe de
  bois** : il déplaçait bien la capsule (~112 u), mais ne corrigeait pas le décalage mesh/capsule,
  donc le claquement visuel restait.
- **FIX** : `enable_root_motion = True` sur `Anim_DKM_Attack_01/02/03` (+ `force_root_lock=False`).
  `ABP_DKM_Alert` était **déjà** en `ROOT_MOTION_FROM_MONTAGES_ONLY`, donc la capsule suit
  maintenant l'animation exactement.
- **Les 2 `LaunchCharacter` (attaque ET dodge) ont été SUPPRIMÉS** — le root motion fait le
  déplacement, les garder faisait double déplacement. Les nœuds nourriciers devenus orphelins
  (`vector * float`, `Normalize`, `Get Actor Forward Vector`, `Get DodgeDistance`,
  `Get LungeStrength`) ont été supprimés aussi. `BPC_Combat` : 162 → 154 nœuds.
- **Les anims de dodge du Mannequin ont DÉJÀ `enable_root_motion = True`** et une racine qui
  parcourt 400 unités (Dodge_F +400 Y, Dodge_B −400 Y, Dodge_L +400 X, Dodge_R −400 X). Donc le
  déplacement d'esquive était **déjà** géré par le root motion depuis le début — c'est bien la
  *sélection du montage* qui était en cause pour le "ça ne va qu'en avant", pas la propulsion.
- **VALIDÉ NUMÉRIQUEMENT EN PIE** : départ X=0 → 1 clic → s'arrête à X=**122.8** (racine de l'anim
  à 0.753s = 122.5 ✓). 2 clics → s'arrête à X=**187.4** (racine à 1.840s = **187.375** ✓). Position
  **stable** après la fin (relevée à +2.6s et +3.4s : aucun retour). `MaxWalkSpeed` restauré à 500,
  `GroundFriction` à 9. Capture d'écran à l'appui (perso épée levée, déplacé sur le sol).
- **LEÇON** : devant un symptôme "le mesh bouge mais pas le perso / il claque en arrière", vérifier
  **`enable_root_motion` de l'AnimSequence VS la translation réelle du bone `root`** avant toute
  autre hypothèse. Outil : `unreal.AnimationLibrary.get_bone_pose_for_time(seq,"root",t,False)`
  échantillonné à plusieurs instants (les propriétés `notifies`/`has_root_motion` sont `protected`
  et illisibles, mais `AnimationLibrary` passe outre).

## Combo recalé sur les VRAIS notifies de l'utilisateur (29/08)
**Je pilotais le combo avec mes propres timers (2.4s / 3.5s) en ignorant totalement son découpage.**
Lecture enfin réussie des notifies (via `unreal.AnimationLibrary`, pas via `AnimMontageService`
qui renvoie vide) : `AM_DKM_Attack_03` porte une track **"Combo"** avec **2 `PlayMontageNotify`
à t=0.753s et t=1.840s** (non nommés — `NotifyName='None'`).
→ `Window1Duration`=**0.753**, `Window2Duration`=**1.087** (0.753→1.840), `Window3Duration`=**3.060**
(1.840→4.90), réglés sur l'instance `CombatComponent` de `BP_DarkKnight_Alert`.
**VALIDÉ EN PIE** (dilation 0.10, temps monde à chaque relevé) : 1 clic → coupe à 0.753s ; clic 2
placé à 0.697s → `bComboQueued=True`, le montage **franchit** 0.753 sans couper, `ComboIndex`
passe à 1, puis **coupe à 1.840s** faute de 3e clic. Exactement son découpage.
**Lecture des notifies (recette qui marche)** :
```python
unreal.AnimationLibrary.get_animation_notify_track_names(m)   # ["Combo"]
evs = unreal.AnimationLibrary.get_animation_notify_events(m)
unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e) # temps exact
```

## Réactivité / latence du clic (29/08)
Cause principale : pendant tout le combo, `MaxWalkSpeed`/`MaxAcceleration` sont à 0. Avec
l'ancienne `Window1Duration`=2.4s, **un simple clic gelait le joueur 2.4 secondes** → sensation de
latence énorme, et un clic pendant ce gel ne faisait qu'armer `bComboQueued`. Avec 0.753s le gel
est 3× plus court. Vérifié : `RequestAttack` n'est PAS bloqué par `bIsDodging` (il ne teste que
`bIsAttacking`), et le `NOT(bIsAttacking OR bIsDodging)` de `BP_DarkKnight_Alert` ne sert qu'à
`Set bUseControllerRotationYaw`, pas de gate. Ré-attaque immédiate après fin de combo testée :
`bIsAttacking` repasse à True instantanément.
**Reste à surveiller** : le gate stamina (`CurrentStamina >= AttackStaminaCost`) est le seul point
qui peut avaler un clic silencieusement. Si "1 fois sur 2" persiste après enchaînement
dodge→attaque, c'est la stamina qu'il faut regarder (dodge 25 + attaque 20 sur 100 max).

## ⚠️ Notifies de dégâts retirées par l'utilisateur
L'utilisateur a supprimé les `AN_AttackDamage` que j'avais posées sur `AM_DKM_Attack_03` (il
soupçonnait qu'elles causaient le bug — ce n'était pas le cas, c'était le root motion).
**Conséquence : plus aucun dégât n'est déclenché par les attaques du Dark Knight.** Il reste
uniquement la track "Combo" avec ses 2 notifies. À re-poser quand il voudra (idéalement calées sur
les impacts réels, pas au jugé comme la première fois).

## Fait (suite) — Transition dodge trop lente + équilibrage stamina (29/08, 3e passe)
- [x] **"Le perso se stop avant de reprendre la course" après un dodge** : diagnostiqué en
  échantillonnant la translation du bone `root` de `Dodge_F` à 19 points dans le temps
  (`unreal.AnimationLibrary.get_bone_pose_for_time`). Le déplacement réel est **terminé à 0.54s**
  (vitesse retombée à ~0, position bloquée à Y=393) alors que l'anim dure **1.083s** — la seconde
  moitié est une pose de récupération en sur-place, jouée intégralement car `OnDodgeFinished` ne
  faisait que reset `bIsDodging`, jamais de `Montage_Stop`/blend anticipé.
  **Fix (sur les 4 montages `Dodge_F/B/L/R_Montage`)** : `blend_out_trigger_time` = `len - 0.52`
  (déclenche la sortie pile quand le déplacement racine s'arrête, au lieu d'attendre la fin des
  1.083s), `blend_in` 0.25→**0.10**, `blend_out` 0.25→**0.15**. C'est le mécanisme UE natif pour
  sortir un montage en avance sans toucher au graphe — pas de node en plus.
  Champs Python : `montage.get_editor_property("blend_out_trigger_time")` (float, PAS un struct),
  `blend_in`/`blend_out` sont des `FAlphaBlend` → `.get_editor_property("blend_time")`.
- [x] **Équilibrage stamina** demandé : jauge pleine doit permettre au moins 3 dodges + 1 combo de
  3 attaques. Avant : `DodgeStaminaCost`=25 (3×=75/100, aucune marge) et `AttackStaminaCost`=20
  (3×=60/100, marge faible) — les deux tenaient tout juste SÉPARÉMENT mais pas enchaînés
  (dodge→attaque comme demandé). **Nouveau** : `AttackStaminaCost` 20→**12**, `DodgeStaminaCost`
  25→**18** → 3 dodges (54) + combo de 3 (36) = **90/100**, marge de 10 + régén pendant l'action.
  `StaminaRegenDelay` 1.0→**0.6s** pour que la régén reparte plus vite entre deux actions.
  **Vérifié en PIE** (appels directs `ConsumeDodgeStamina`/`ConsumeAttackStamina`, hors gate
  d'input) : 100 → 3×Dodge → **46.0** (attendu 46) → 3×Attack → **10.0** (attendu 10). Calcul exact.
- **Limitation d'outillage découverte** : `AnimInstance.montage_play(...)` et
  `Character.play_anim_montage(...)` appelés **directement depuis Python** renvoient toujours
  `duration=0.0` et ne jouent RIEN — testé sur un montage dont je sais par ailleurs qu'il
  fonctionne (`AM_DKM_Attack_03`, confirmé juste après via le vrai chemin `RequestAttack`). C'est
  une limitation de l'appel Python sur cette fonction précise (signature/résolution d'overload
  côté binding), **pas un bug du jeu**. En conséquence, impossible de vérifier en isolation le
  nouveau timing de blend-out du dodge (le déclenchement normal via `Dodge()` est en plus bloqué
  par le gate directionnel faute d'input simulable — double limitation qui se cumule pour ce cas
  précis). Les réglages sont posés et persistés correctement (vérifié par relecture des assets
  après save), mais **le ressenti de la transition dodge→course doit être confirmé en jeu réel**.
  **Pour tester un montage isolément à l'avenir** : passer par un event Blueprint existant qui
  appelle `PlayAnimMontage` en interne (comme `RequestAttack`/`Dodge`), jamais par un appel Python
  direct sur `AnimInstance`/`Character`.

## Fait (suite) — Vitesse des attaques +35% (29/08, 4e passe)
- [x] `InPlayRate` mis à **1.35** (+35%, milieu de la fourchette demandée 30-40%) sur les 4 nœuds
  `Play Anim Montage` de `BPC_Combat` qui jouent `Montage1/2/3` (deux nœuds différents référencent
  `Montage1` — un pour la branche `bCumulativeCombo`, un pour l'ancien système 3-montages — les
  deux mis à jour pour rester cohérents quel que soit le personnage).
  **Piège évité** : `Window1/2/3Duration` (fenêtres du combo cumulatif du DK) sont des **délais en
  temps réel** (`K2_SetTimer`), pas liés au temps d'anim — si on accélère l'anim sans recalculer
  les fenêtres, elles se désynchronisent des notifies (la coupure arrive trop tard par rapport au
  geste visuel accéléré). **Recalculées en divisant par 1.35** : `Window1Duration` 0.753→**0.558**,
  `Window2Duration` 1.087→**0.805**, `Window3Duration` 3.060→**2.267**.
  **Vérifié en PIE** : ratio `montage_get_position / temps_réel_écoulé` mesuré à **1.352** (attendu
  1.35) — l'anim tourne bien à la vitesse réglée, et la coupure suit toujours les notifies au bon
  moment relatif.
  **Dodge non touché** (pas concerné par "animation de combat" au sens attaque, et déjà retravaillé
  la session précédente).

## Fait (suite) — 30/08 : IA ennemie qui ne chase pas, 3 bugs empilés (CORRIGÉ)
L'utilisateur avait configuré lui-même son propre système IA (`/Game/AI/BP_AI_Enemy`,
`/Game/AI/BT_Enemy`, `/Game/AI/BD_AI`, `/Game/AI/Tasks/Task_ChaseTarget` — distinct de mon
scaffolding précédent resté inachevé dans `/Game/Enemies/AI/`). Le décorateur Blackboard
(`seeingTarget?` Set/NotSet sur `Idle_Sequence`/`Chasing_Sequence`) était **structurellement
correct**. Trois bugs indépendants empêchaient quand même tout mouvement :

1. **`RunBehaviorTree.BTAsset` était vide** (`BP_AI_Enemy.EventGraph`, appelé depuis BeginPlay) →
   aucun arbre ne se chargeait, donc rien ne s'exécutait jamais, peu importe l'état du blackboard.
   **Piège** : écrire une string de chemin (`"/Game/AI/BT_Enemy"`, avec ou sans suffixe
   `BehaviorTree'...'`) sur un pin objet via `set_node_pin_value` retourne `True` mais **n'écrit
   rien** (même famille de piège que le pointeur `Slot` du HUD). **Fix qui marche** : ajouter une
   variable membre typée `BehaviorTree` (`add_member_variable`), la remplir via CDO
   (`unreal.get_default_object(...).set_editor_property(...)`), puis un `variable_get` de cette
   variable câblé sur le pin `BTAsset`.
2. **`AIBlueprintHelperLibrary::GetBlackboard` avait son pin `Target` vide** (x2, pour les 2 écritures
   `Set Value as Bool`/`Set Value as Object` dans le handler `On See Pawn` du PawnSensing). Cette
   fonction attend le **pawn contrôlé**, pas le controller — sans lui elle retourne `None` et les
   écritures blackboard échouent silencieusement. **Fix** : nœud `Controller::K2_GetPawn` (spawner
   "Get Controlled Pawn") câblé sur les deux pins `Target`.
3. **Aucun `NavMeshBoundsVolume` dans `Lvl_ThirdPerson`** → pas de NavMesh généré → `AI MoveTo`
   (dans `Task_ChaseTarget`) échoue instantanément à chaque tentative, même avec un `targetActor`
   et un `seeingTarget?=true` corrects. Symptôme trompeur : la task "s'exécute" (le BT tourne,
   rien ne plante) mais le pion reste figé. **Fix** : spawné un `NavMeshBoundsVolume`
   (`unreal.EditorActorSubsystem.spawn_actor_from_class`) centré sur (0,0,0), scale (80,80,20)
   (= 8000×8000×2000 unités, couvre toute la zone de jeu), `RebuildNavigation` en console, niveau
   sauvegardé.
- **`PawnSensing` déjà bien réglé** par l'utilisateur (SightRadius=2000, bOnlySensePlayers=True,
  PeripheralVisionAngle=85) — pas touché.
- **VALIDÉ EN PIE** : `seeingTarget?=True`, `targetActor`=le Dark Knight, `BehaviorTreeComponent
  .is_running()=True`, ET **position de l'ennemi passée de (340,-1290) à (12,-68)** — il a
  rejoint le joueur (à 0,0) et s'est arrêté à l'`AcceptanceRadius` (5u) par défaut de `AI MoveTo`.
- **Lecture directe des clés blackboard en PIE (recette qui marche)** :
  `ctrl.get_components_by_class(unreal.ActorComponent)` → filtrer `"Blackboard" in
  c.get_class().get_name()` → `bb.get_value_as_bool("seeingTarget?")` /
  `bb.get_value_as_object("targetActor")`. Pour le BT lui-même : filtrer
  `"BehaviorTreeComponent"` → `.is_running()`.
- **LEÇON** : "la task s'exécute mais rien ne bouge" avec perception/blackboard corrects → vérifier
  en premier la présence d'un `NavMeshBoundsVolume` couvrant la zone, PAS la logique du Behavior
  Tree elle-même.

## Fait (suite) — 30/08 : ABP ennemi, attaque, dégâts, hit-react, mort, barre de vie
- [x] **`ABP_Morigesh` + `BS_Morigesh_Locomotion` branchés sur `/Game/AI/BP_Enemy`** (ils
  existaient déjà d'une session précédente et étaient corrects : Blend Space 2D
  Direction -180..180 / Speed 0..500, mêmes réglages que `BS_StrafeMovement`, AnimGraph
  `BlendSpacePlayer → Slot('DefaultSlot') → Output Pose`, EventGraph Speed/Direction câblé —
  y compris la connexion `GetVelocity → VectorLength` qui avait causé le bug des jambes figées
  sur le DK). `MaxWalkSpeed` 350→500 pour coller au max du Blend Space, `bOrientRotationToMovement=false`
  + `bUseControllerRotationYaw=true` (strafe), `SetFocus` ajouté sur `BP_AI_Enemy.OnSeePawn`
  pour que le pion reste orienté vers la cible.
- [x] **🔴 PIÈGE MAJEUR — le mesh du skin Paragon a un squelette VIDE.** `BP_Enemy` utilisait
  `Morigesh_NorthernMysticAntlers` dont le squelette `..._Skeleton` a **`bone_count: 1`** (!),
  alors que le vrai rig `Morigesh_Skeleton` a **195 os**. Symptôme : `mesh.get_anim_instance()`
  retourne **`None`** en PIE — l'AnimBP ne s'instancie pas du tout, aucune animation. Ajouter la
  compatibilité de squelette (`add_compatible_skeleton`) NE SUFFIT PAS dans ce cas.
  **Fix** : repointer le mesh sur `/Game/ParagonMorigesh/.../Meshes/Morigesh` (rig complet).
  **Diagnostic** : `unreal.SkeletonService.get_skeleton_info(path)` → regarder `bone_count`.
- [x] **🔴 PIÈGE MAJEUR — les overrides d'instance de composant ne survivent pas aux éditions CDO.**
  `set_component_property(bp, "CombatComponent", "Montage1", ...)` retournait `True` et se
  relisait correctement **au niveau de l'asset**, mais l'instance en PIE gardait les montages du
  Dark Knight (les défauts de la classe `BPC_Combat_C`). Cause : toute édition ultérieure du CDO
  de `BP_Enemy` (ici `set_editor_property("skeletal_mesh_asset", ...)`) réinitialise les overrides
  d'instance posés avant. **Solution retenue (robuste)** : créer des **sous-classes dédiées**
  `/Game/Enemies/Morigesh/BPC_Combat_Morigesh` et `BPC_Stat_Morigesh` (via
  `unreal.BlueprintFactory` avec `parent_class` = la classe générée du parent), régler leurs
  **défauts de classe** via CDO (ça, ça persiste de façon fiable), puis
  `remove_component` + `add_component` sur `BP_Enemy` avec les nouveaux types.
  **Note** : `add_component` veut le nom de la **classe générée** (`"BPC_Combat_Morigesh_C"`),
  pas le chemin d'asset — le chemin retourne `False` silencieusement.
- [x] **🔴 Après un changement de type de composant, RAFRAÎCHIR les nœuds qui le référencent.**
  Le Blueprint ne compilait plus (`compile_blueprint → False`, et surtout **les composants
  disparaissaient à l'exécution** alors que `list_components` les montrait bien dans l'asset).
  Erreur réelle visible uniquement dans le log :
  `Saved/Logs/Francia_Souls_Like.log` → `LogBlueprint: Error: ... Stat Component of type
  BPC Stat Object Reference doesn't match the property StatComponent of type BPC Stat Morigesh
  Object Reference`. **Fix** : `BlueprintService.refresh_node(bp, graph, node_id, False)` sur
  chaque `Get StatComponent`/`Get CombatComponent`, puis recompile → `True`.
  **LEÇON** : quand `compile_blueprint` retourne `False` sans que l'audit des pins ne montre rien,
  `grep -iE "LogBlueprint: Error" Saved/Logs/*.log | tail` donne la vraie erreur.
- [x] **Attaque** : `BP_Enemy.Attack01` (implémentation de `BPI_Enemy`, appelée par
  `/Game/AI/Task_Attack`) avait un `PlayAnimMontage` avec **`self` ET `AnimMontage` non branchés**
  → ne jouait rien. Câblé (nœud `K2Node_Self` + variable `AttackMontage1`).
- [x] **Dégâts** : `ReceiveAnyDamage` overridé sur `BP_Enemy` → `Set PendingDamage` (sur
  `StatComponent`) → `ApplyDamage`. C'est le même pipeline que le joueur. Les notifies
  `AttackDamage` étaient déjà posées sur les 3 `AM_Morigesh_Attack_*` et appellent
  `BPC_Combat.DoAttackTrace` (socket `hand_r`, qui **existe bien** sur `Morigesh_Skeleton`).
- [x] **Barre de vie au-dessus de la tête** : `WidgetComponent` "HealthBarWidget" ajouté sur
  `BP_Enemy` (Space=World, DrawSize 120×16, Pivot (0.5,1), RelativeLocation Z=220), affichant
  `/Game/CoreSystems/VitalSystems/ExampleEnemy/WBP_enemyHealthBar` (asset du pack, qui était une
  **coquille vide** — aucun câblage). Complété : variables `OwnerActor` (Actor) + `StatCompClass`
  (`TSubclassOf<ActorComponent>` = `BPC_Stat_C`, mis via CDO), et `Event Tick` →
  `IsValid(OwnerActor)` → `GetComponentByClass(StatCompClass)` → `Cast BPC_Stat` →
  `CurrentHealth/MaxHealth` → `WBP_masterProgressBAr.SetFillLevel`.
  **`WidgetClass` sur le WidgetComponent ne tenait pas à l'exécution** (encore la même famille de
  piège) → contourné en créant le widget dans `BeginPlay` : `Create Widget` (classe depuis une
  variable `HealthBarWidgetClass` réglée par CDO) → `WidgetComponent.SetWidget` → `Cast
  WBP_enemyHealthBar` → `Set OwnerActor = self`.
- [x] **VALIDÉ EN PIE, bout en bout** : composants tous présents à l'exécution
  (`BPC_Combat_Morigesh_C`, `BPC_Stat_Morigesh_C`, `WidgetComponent`), montages tous corrects
  (Morigesh et non DK), `apply_damage(30)` → HP 100→70, `MaxWalkSpeed` → **0.0** (hit-stun) et
  montage **`AM_Morigesh_HitReact`** joué, barre **FillLevel = 0.7**, puis `apply_damage(200)` →
  HP **0.0**, `bIsDead=True`, montage **`AM_Morigesh_Death`**. Capture d'écran confirmant que
  l'ennemi chase bien le joueur jusqu'au contact.
- **Reste à faire / non vérifié** : la distance d'attaque (le BT a un `Task_Attack` mais je n'ai
  pas vérifié qu'un décorateur de distance déclenche bien la séquence d'attaque quand l'ennemi
  arrive à portée — `AI MoveTo` s'arrête à `AcceptanceRadius`=5 par défaut, ce qui est très près ;
  à ajuster). Les dégâts infligés PAR l'ennemi au joueur via le trace n'ont pas été observés en
  situation réelle (seulement le pipeline `ApplyDamage` testé directement).

## Fait (suite) — 30/08 : barre de vie corrigée + BOSS Khaimera (x2)
- [x] **Barre de vie ennemi — elle était ÉNORME et AUX PIEDS.** Diagnostic sur l'instance vivante :
  `DrawSize = 500x500` (défaut du WidgetComponent) et widget à Z=90 = à hauteur des pieds. Mes
  `set_component_property("DrawSize"/"RelativeLocation")` s'étaient bien écrits **au niveau de
  l'asset** mais ne survivaient pas à l'exécution (encore le piège des overrides d'instance
  écrasés par les éditions CDO). **Fix définitif — tout régler au RUNTIME dans `BeginPlay`** :
  `HealthBarWidget.SetDrawSize((110,12))` + `K2_SetRelativeLocation(0,0,210)` chaînés après le
  `Set OwnerActor`. **Vérifié en PIE** : `DrawSize = 110x12`, widget à **+210** au-dessus du pivot.
  **RÈGLE** : pour un WidgetComponent, ne pas compter sur les valeurs posées côté asset —
  `SetWidget` / `SetDrawSize` / `SetRelativeLocation` au BeginPlay, c'est le seul chemin fiable ici.
- [x] **`/Game/AI/BP_Boss` créé** (duplication de `BP_Enemy`, donc hérite gratuitement de tout le
  câblage déjà validé : `Attack01`, `ReceiveAnyDamage`→`ApplyDamage`, création + placement de la
  barre de vie au BeginPlay, `AIControllerClass = BP_AI_Enemy_C`, `AutoPossessAI`).
  - Mesh `/Game/ParagonKhaimera/.../Meshes/Khaimera` (**206 os**, rig complet — pas de piège de
    squelette vide comme sur le skin Morigesh), AnimClass `ABP_Khaimera_C`.
  - **Taille x2** : `capsule_half_height` 88→**176**, `capsule_radius` 34→**68**,
    `mesh.relative_scale3d` = **(2,2,2)**, `mesh.relative_location.z` = **-176** (pour que les
    pieds restent au bas de la capsule). Mesuré en PIE : tête Z=597, pieds Z=207 → **~390 unités
    de haut**, soit bien le double d'un personnage normal.
  - Sous-classes de composants dédiées (même méthode que Morigesh, la seule qui persiste) :
    `BPC_Combat_Khaimera` (montages `AM_Khaimera_Attack_01/02/03`, `AttackDamage`=40,
    `AttackRadius`=180 — doublé comme la taille) et `BPC_Stat_Khaimera` (`MaxHealth`=**600**,
    `AM_Khaimera_Death`, `AM_Khaimera_HitReact`).
  - Barre de vie remontée à **Z=420** et `DrawSize (150,14)` (boss 2x plus haut).
  - `MaxWalkSpeed` 420 (plus lourd), strafe activé comme les autres.
  - **VALIDÉ EN PIE** : `ABP_Khaimera_C` instanciée, scale (2,2,2), `BPC_Stat_Khaimera_C` avec
    600 PV, `AM_Khaimera_Attack_01`, contrôleur `BP_AI_Enemy_C` possédé, `seeingTarget?=True` et
    **le boss a chassé le joueur de 500 → 103 unités**. Capture d'écran confirmant l'échelle.
- [x] **⚠️ PIÈGE PYTHON — `unreal.Rotator(0,180,0)` en POSITIONNEL introduit un roll parasite.**
  Le boss apparaissait **à l'envers** (tête en bas) après mes rotations manuelles de test :
  `actor rot = pitch 0, yaw 180, roll 180`. Ce n'était PAS un bug du Blueprint mais mes propres
  appels `set_actor_rotation(unreal.Rotator(0,180,0), False)`. **Toujours construire un Rotator
  champ par champ** : `r = unreal.Rotator(); r.set_editor_property("pitch",0.0);
  r.set_editor_property("yaw",180.0); r.set_editor_property("roll",0.0)`. Après ça : roll=0,
  tête au-dessus des pieds, confirmé par mesure d'os ET capture d'écran.
  **Méthode de diagnostic d'orientation** : comparer `mesh.get_socket_location("head").z` vs
  `("foot_l").z` — objectif, contrairement à une lecture de capture qui peut tromper (une première
  capture m'avait fait conclure à tort au retournement, une seconde à conclure à tort l'inverse).
- **Reste à faire** : phases du boss (l'utilisateur les ajoutera), distance de déclenchement de
  l'attaque (`AI MoveTo` s'arrête à `AcceptanceRadius`=5 — beaucoup trop près, surtout pour un
  boss de cette taille ; à porter à ~150-250 côté `Task_ChaseTarget` et à coupler avec un
  décorateur de distance sur la séquence d'attaque du BT).

## Fait (suite) — 30/08 : strafe des ennemis (3 bugs empilés, corrigés)
Symptôme signalé : "y'a pas le strafemovement, je vois que idle". Le Blend Space et l'AnimBP
étaient corrects — trois bugs indépendants empêchaient les anims latérales de sortir :

1. **`Speed` incluait la vitesse verticale.** Les 3 AnimBP (`ABP_Morigesh`, `ABP_Khaimera`,
   **et `ABP_DKM_Alert` du joueur**) faisaient `GetVelocity → Vector Length (VSize)` → `Set Speed`.
   `VSize` prend les **3 axes**, donc en chute libre `Speed` montait à 1845 (mesuré) alors que la
   vitesse horizontale était de 4.7 — le Blend Space recevait n'importe quoi.
   **Fix** : remplacé par `KismetMathLibrary::VSizeXY` (horizontale seule) sur les 3.
   **Vérifié** : `velocity XY = 500.0` → `Speed = 500.0` exactement, `Z = 0`.
2. **`Task_ChaseTarget` échouait TOUJOURS.** Ses **deux** nœuds `FinishExecute` (celui branché sur
   `OnSuccess` ET celui sur `OnFail`) avaient `bSuccess = false`. Donc la tâche retournait
   systématiquement un échec → la `Chasing_Sequence` s'avortait immédiatement après et
   **n'atteignait jamais le nœud suivant**. C'est LA raison pour laquelle aucun comportement autre
   que "courir droit devant" ne pouvait s'exécuter. **Fix** : `bSuccess = true` sur la branche
   `OnSuccess`.
   **LEÇON** : sur un `BTTask_BlueprintBase`, toujours vérifier le `bSuccess` de CHAQUE
   `FinishExecute` — un `false` sur la branche succès casse silencieusement toute la séquence en
   aval, sans erreur de compilation ni warning.
3. **`AcceptanceRadius` du `AI MoveTo` était à 5** → l'ennemi rentrait littéralement dans le joueur
   avant de s'arrêter. Porté à **220** (distance de combat).

- [x] **`/Game/AI/Tasks/Task_Strafe` créé** (`BTTask_BlueprintBase`) et ajouté dans
  `Root/Selector[0]/Chasing_Sequence[0]` après `Task_ChaseTarget`. Logique : `targetActor` (clé BB
  liée via `BehaviorTreeService.set_node_blackboard_key`) → position cible − position pion →
  `Normal` → `RotateAngleAxis(90°, axe Z)` = vecteur latéral → `× (300,300,0)` → `+ position pion`
  → **`AI MoveTo`** (nœud latent `K2Node_AIMoveTo`, `AcceptanceRadius` 60) → `FinishExecute(true)`.
  **Piège** : `AIBlueprintHelperLibrary::SimpleMoveToLocation` ne marche PAS dans un BTTask (la
  tâche se termine instantanément, le déplacement est annulé au redémarrage de la séquence) — il
  faut le nœud latent `AI MoveTo` (spawner `SPAWN K2Node_AIMoveTo|AI MoveTo`), comme dans
  `Task_ChaseTarget`.
- **VALIDÉ EN PIE** : l'ennemi part de (500,0), atteint la distance de combat, puis **contourne**
  le joueur — positions successives relevées (203,−227) puis (−126,−179), avec `vXY = 297.6` en
  plein déplacement latéral. `actor yaw == control yaw` confirmé (le pion reste **face au joueur**
  grâce à `SetFocus` + `bUseControllerRotationYaw=true` + `bOrientRotationToMovement=false`), donc
  `Direction` part vers ±90 et déclenche `Jog_Left`/`Jog_Right` du Blend Space. Capture d'écran
  montrant Morigesh ayant contourné sur le flanc droit du joueur, face à lui.
### Lissage du strafe (fait) — passage d'un "pas de côté" à une vraie ORBITE
La v1 calculait `destination = position_pion + latéral × 300` : le pion **dérivait** au lieu de
tourner autour de la cible, et s'arrêtait à chaque pas. Refait en géométrie d'orbite :
`(position_pion − position_cible)` → `Normal` → `RotateAngleAxis(angle, Z)` → `× (250,250,0)`
→ **`+ position_cible`**. Le point visé est donc toujours **sur un cercle de rayon 250 autour du
joueur** → il tourne autour au lieu de s'éloigner. (Changements clés : les entrées A/B du
`vector - vector` ont été **inversées**, et le `vector + vector` prend maintenant la position de
la **cible** et non celle du pion.)
- **Angle de pas = `StrafeSign × 65°`** (nœud `float * float` alimenté par la variable `StrafeSign`).
  **Contre-intuitif mais essentiel** : un petit pas d'angle rend le mouvement PLUS saccadé, pas
  moins — chaque `AI MoveTo` devient très court, donc le pion s'arrête sans arrêt. Un arc long
  (65° ≈ 280 unités de trajet à rayon 250) donne un déplacement **continu**. Testé à 22° : quasi
  immobile, angle qui n'avançait que de 2° entre deux relevés. À 65° : `vXY = 439` capté en plein
  mouvement.
- **`AcceptanceRadius` du MoveTo de strafe = 25** (serré, pour ne pas couper l'arc trop tôt).
- **Changement de sens** : `RandomBoolWithWeight(0.2)` en tête de tâche → si vrai,
  `StrafeSign = StrafeSign × -1`. Donne de longs arcs dans un sens avec inversion occasionnelle
  (~1 fois sur 5), au lieu d'une oscillation gauche-droite permanente. Vérifié en jeu : l'angle
  d'orbite est passé de 56° à 54° après une inversion.
- **VALIDÉ EN PIE** : orbite mesurée à angle **10° → 89° → 142°** avec distance au joueur stable
  (~235-243, cohérent avec le rayon 250), et en plein déplacement `Speed = 439.0`,
  **`Direction = -151.7`** — le Blend Space reçoit enfin une direction non nulle, donc les
  échantillons `Jog_Bwd`/`Jog_Left`/`Jog_Right` se déclenchent réellement. Capture d'écran du boss
  avec flou de mouvement pendant qu'il contourne le joueur.
- **Reste non fait** : la barre de vie ennemie garde les couleurs par défaut du pack (orange/vert),
  pas recolorée. Le strafe peut se figer près d'un bord de plateforme (point d'orbite hors
  NavMesh) — pas gênant au centre de l'arène, à surveiller sur une map réelle.

## Nouvelle demande utilisateur (29/08/2026, pas commencée) — Target Lock via Input Action dédiée
Une `Input Action` de lock a déjà été créée côté utilisateur, mappée sur un bouton. Contrairement
à l'approche "caméra toujours verrouillée derrière le perso" actuelle, l'objectif du tuto suivi
est un **vrai lock-on de cible souls-like** : appui sur le bouton → cherche un ennemi verrouillable
à portée → la caméra s'oriente vers/reste sur cette cible (pas juste dans le dos du joueur) tant
que le lock est actif, perso peut strafer autour d'elle. C'est la même feature que le point 7 de
la todo list ("Target Lock") plus bas, maintenant avec une contrainte précise côté input déjà en
place. **Pas commencé** — prochaine étape demandée par l'utilisateur.

## Pas encore fait
- **Barre de vie/endurance à l'écran (HUD UMG)** : pas construite (pas d'asset fourni par
  l'utilisateur). Le système est 100% fonctionnel côté code (`CurrentHealth`/`MaxHealth`/
  `CurrentStamina`/`MaxStamina` sur `BPC_Stat`, lisibles par n'importe quel widget). Prochaine
  étape si demandé : un `WBP_HUD` simple avec deux ProgressBar liées par binding.

## À faire (dans l'ordre demandé par l'utilisateur)
1. ~~Blend Space Alert~~ ✅
2. ~~AnimBP~~ ✅
3. ~~Character Blueprint + caméra~~ ✅
4. ~~Attack Combo~~ ✅
5. ~~BPC Stat (santé)~~ ✅
6. ~~Dodge (scaffold fonctionnel, anim à assigner)~~ ✅
7. **Target Lock** (souls-like) : recherche de cible verrouillable à portée, caméra qui
   s'oriente/reste dans le dos du perso pendant qu'il strafe autour de la cible. **Pas commencé,
   prochaine étape.**

## Connexion MCP — piège récurrent
Le serveur HTTP `unreal-mcp` (port 8000, côté plugin VibeUE dans l'éditeur) peut répondre à un
`curl` alors que **cette session Claude Code ne l'a pas chargé** — les serveurs `.mcp.json` se
connectent au démarrage du process `claude`, pas à l'ouverture de l'éditeur Unreal. Rouvrir
l'éditeur ne suffit PAS. Si `ToolSearch` ne trouve pas `mcp__unreal-mcp__*` alors que le curl
répond : il faut fermer et rouvrir le terminal Claude Code lui-même (pas juste l'éditeur).

<!-- END PROJECT STATE -->
