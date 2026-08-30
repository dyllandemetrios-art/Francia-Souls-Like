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
`curl` alors que **cette session Codex ne l'a pas chargé** — les serveurs `.mcp.json` se
connectent au démarrage du process `Codex`, pas à l'ouverture de l'éditeur Unreal. Rouvrir
l'éditeur ne suffit PAS. Si `ToolSearch` ne trouve pas `mcp__unreal-mcp__*` alors que le curl
répond : il faut fermer et rouvrir le terminal Codex lui-même (pas juste l'éditeur).

<!-- END PROJECT STATE -->
