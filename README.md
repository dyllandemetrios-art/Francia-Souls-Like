# Francia Souls-Like — prototype de combat

Premier prototype jouable centré sur le **game feel d'un combat de boss à la troisième personne**. Le projet ne cherche pas encore à former un jeu complet : il teste une boucle courte, lisible et rejouable, du menu jusqu'à la victoire ou la mort.

## Boucle jouable

1. Choisir une difficulté dans le menu **The Last Knight**.
2. Approcher et vaincre le gardien Morigesh.
3. Affronter Khaimera sur trois phases.
4. Gagner, ou revenir au menu après un Game Over pour recommencer.

Khaimera passe d'un combat physique à une phase magique, puis à un mode berserk rouge. Sa phase magique alterne une révélation de feu autour de lui quand le joueur reste au corps-à-corps et des projectiles lorsqu'il garde ses distances.

## Systèmes réalisés

- locomotion en strafe et caméra à l'épaule ;
- verrouillage de cible et assistance d'orientation pendant les combos ;
- combo à trois coups, endurance, esquive directionnelle et invulnérabilité brève ;
- dégâts, réaction aux impacts, étourdissement du finisher et mort ;
- IA de poursuite et d'attaque pour le gardien et le boss ;
- boss en trois phases avec changements de rythme, d'animations et de VFX ;
- HUD joueur et boss, annonces de phase, victoire et Game Over ;
- trois réglages de difficulté ;
- prise en charge clavier/souris et manette.

## Commandes

| Action | Clavier / souris | Manette |
|---|---|---|
| Déplacement | ZQSD ou flèches | Stick gauche |
| Caméra | Souris | Stick droit |
| Attaque | Clic gauche | X / Carré |
| Esquive | Espace | A / Croix |
| Verrouillage | Clic molette | Stick droit pressé |
| Interaction | E ou clic droit | Y / Triangle |
| Retour au menu après la mort | Entrée | Start |

## Développement assisté par IA

Le prototype sert aussi d'expérimentation de production avec des agents IA. Une partie des Blueprints, de l'intégration des animations et des tests Play-In-Editor a été pilotée dans Unreal via MCP, d'abord avec Claude Code puis avec ChatGPT/Codex. Les décisions de game design, les retours de jeu et la validation finale restent humains.

Cette méthode a surtout accéléré les itérations et les tâches répétitives. Elle a aussi confirmé qu'un Blueprint qui compile n'est pas nécessairement correct : les systèmes ont donc été contrôlés en jeu, avec des parcours complets et des mesures d'état. Le journal technique détaillé se trouve dans [CLAUDE.md](CLAUDE.md).

## Lancer le projet

- Version utilisée : **Unreal Engine 5.8**.
- Ouvrir `Francia_Souls_Like.uproject`.
- Lancer la carte `/Game/ThirdPerson/Lvl_ThirdPerson`.

Les packs Marketplace et Paragon sont exclus du dépôt Git à cause de leur taille et doivent être présents localement pour ouvrir le projet complet. Une version Windows autonome est prévue pour la page itch.io.

## État de la V1

La V1 s'arrête volontairement à ce prototype de combat. Une éventuelle suite pourra explorer une parade inspirée de l'AMHE, des animations capturées avec le club et une arène dédiée. Ces pistes seront traitées comme de nouvelles itérations pour préserver cette version jouable.

## Crédits et licences

Le projet utilise Unreal Engine ainsi que des assets Epic Games, Paragon et Marketplace. Chaque asset reste soumis à la licence de son éditeur. Le code, les Blueprints propres au prototype et la documentation de production sont présentés comme travail de portfolio.
