# Francia Souls-Like — prototype de combat

Francia Souls-Like est mon premier prototype de combat de boss réalisé sous Unreal Engine 5. Il propose une boucle courte : choisir une difficulté, affronter un gardien, puis combattre Khaimera à travers trois phases jusqu'à la victoire ou la mort.

Le prototype met l'accent sur le ressenti et la lisibilité du combat : caméra à l'épaule, verrouillage de cible, combo à trois coups, endurance, esquive avec invulnérabilité, réactions aux impacts, étourdissement, IA de poursuite et boss alternant attaques physiques et magie de feu.

## Ce que ce projet m'a appris

Ce projet m'a surtout permis de progresser en Blueprint et en Technical Game Design :

- séparer les responsabilités entre le personnage, le combat, les statistiques, l'IA et l'interface ;
- utiliser les Actor Components pour rendre la santé, l'endurance et le combat réutilisables ;
- construire un combo avec buffer d'input, coûts d'endurance et fenêtres d'action ;
- synchroniser dégâts et effets avec les animations et les Anim Notifies ;
- créer un verrouillage de cible et une assistance d'orientation ;
- piloter une IA avec Blackboard, Behavior Tree et tâches dédiées ;
- concevoir trois phases de boss dans une seule IA à partir de seuils de vie ;
- coordonner les états attaque, esquive, hit-react, incantation et mort sans softlock ;
- relier les données de gameplay au HUD, au menu de difficulté et aux écrans de fin ;
- tester une boucle complète en jeu et corriger les problèmes qui n'apparaissent pas à la compilation.

Le développement a été réalisé avec l'aide d'agents IA pour accélérer l'intégration, l'organisation des graphes et les tests répétitifs. J'ai défini la direction du gameplay, évalué chaque itération en jeu et demandé les corrections selon le ressenti recherché. Le résultat est un prototype portfolio, volontairement limité à sa boucle de combat.

## Commandes

- ZQSD / stick gauche : déplacement
- Souris / stick droit : caméra
- Clic gauche / X ou Carré : attaque
- Espace / A ou Croix : esquive
- Clic molette / R3 : verrouillage

Durée indicative : quelques minutes par partie.

